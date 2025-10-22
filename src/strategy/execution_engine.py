"""
执行引擎 - 处理风险管理和交易执行决策
从策略信号到实际交易执行的桥梁
"""

from typing import Optional, Dict, Any
import threading

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from config.config import TradingConfig
from models.strategy_data import TradingSignal, MarketContext
from utils.log import setup_logging
from utils.events import publish_event, EventTypes
from risk.risk_manager import RiskManager

log = setup_logging(module_prefix='EXECUTION')


class ExecutionEngine:
    """
    执行引擎 - 负责风险管理和交易执行决策
    使用静态方法，不需要实例化
    """

    # 类级别状态，跨调用保持
    _last_signals: Dict[str, TradingSignal] = {}
    _trading_client: Optional[TradingClient] = None
    _client_lock = threading.Lock()

    @staticmethod
    def process_signal(signal: Optional[TradingSignal],
                      market_context: MarketContext,
                      config: TradingConfig) -> Optional[TradingSignal]:
        """
        处理交易信号：风险管理 + 执行决策 + Alpaca下单

        Args:
            signal: 原始交易信号
            market_context: 市场环境
            config: 交易配置（含Alpaca密钥、下单参数等）

        Returns:
            处理后的最终信号，或None（拒绝执行）
        """
        if not signal:
            return None

        # 1. 风险管理过滤
        filtered_signal = ExecutionEngine._risk_management(signal, market_context)
        if not filtered_signal:
            return None

        # 2. 执行决策
        final_signal = ExecutionEngine._execution_decision(filtered_signal, market_context)

        if final_signal:
            ExecutionEngine._last_signals[signal.symbol] = final_signal
            ExecutionEngine._handle_signal_execution(final_signal, config)

        return final_signal

    @staticmethod
    def _risk_management(signal: TradingSignal,
                        context: MarketContext) -> Optional[TradingSignal]:
        """风险管理 - 过滤和调整信号"""
        last_signal = ExecutionEngine._last_signals.get(signal.symbol)
        decision = RiskManager.apply_risk_filters(signal, context, last_signal=last_signal)

        if decision.signal is None:
            if decision.reason == "volatility_high":
                log.warning(f"{signal.symbol}: 波动率过高({context.volatility:.2f})，拒绝信号")
            elif decision.reason == "duplicate_signal":
                log.info(f"{signal.symbol}: 信号频率过高，跳过重复信号")
            else:
                log.info(f"{signal.symbol}: 风险管理拒绝信号")
            return None

        if decision.adjusted:
            log.info(f"{signal.symbol}: 成交量偏低，调整置信度至{decision.signal.confidence:.2f}")

        return decision.signal

    @staticmethod
    def _execution_decision(signal: TradingSignal,
                           context: MarketContext) -> Optional[TradingSignal]:
        """执行决策 - 决定是否执行信号"""
        # 这里可以添加更复杂的执行逻辑
        # 例如：仓位管理、市场时机判断等

        # 基本的置信度阈值检查
        if signal.confidence < 0.6:
            log.info(f"{signal.symbol}: 信号置信度过低({signal.confidence:.2f})，不执行")
            return None

        log.info(f"{signal.symbol}: 信号通过执行决策，准备执行")
        return signal

    @staticmethod
    def _handle_signal_execution(signal: TradingSignal, config: TradingConfig):
        """处理信号执行并触发下单"""
        log.info(f"{signal.symbol}: 执行{signal.signal_type}信号 "
                f"@{signal.price:.2f} 置信度:{signal.confidence:.2f} "
                f"原因:{signal.reason}")

        order_payload = ExecutionEngine._submit_order(signal, config)

        # 发布信号执行事件
        ExecutionEngine._emit_signal_event(signal, order_payload)

    @staticmethod
    def _submit_order(signal: TradingSignal, config: TradingConfig) -> Dict[str, Any]:
        """
        调用Alpaca交易API提交订单。
        返回订单信息或错误原因，供事件总线/监控使用。
        """
        if not config.api_key or not config.secret_key:
            message = "缺少Alpaca API密钥，已跳过下单"
            log.error(f"{signal.symbol}: {message}")
            return {'executed': False, 'reason': message}

        client = ExecutionEngine._ensure_trading_client(config)
        if client is None:
            message = "Alpaca交易客户端初始化失败"
            log.error(f"{signal.symbol}: {message}")
            return {'executed': False, 'reason': message}

        qty = max(config.default_order_qty, 1)
        side = ExecutionEngine._map_side(signal.signal_type)
        if side is None:
            message = f"未知的信号类型: {signal.signal_type}"
            log.error(f"{signal.symbol}: {message}")
            return {'executed': False, 'reason': message}

        tif = ExecutionEngine._resolve_time_in_force(config.time_in_force)

        order_request = MarketOrderRequest(
            symbol=signal.symbol,
            qty=qty,
            side=side,
            time_in_force=tif
        )

        try:
            order = client.submit_order(order_request)
            log.info(
                f"{signal.symbol}: Alpaca下单成功 "
                f"订单ID:{order.id} 方向:{side.value.upper()} 数量:{qty} TIF:{tif.value}"
            )
            return {
                'executed': True,
                'order_id': order.id,
                'side': side.value,
                'qty': qty,
                'status': getattr(order, "status", None)
            }
        except Exception as exc:
            log.error(f"{signal.symbol}: Alpaca下单失败: {exc}")
            return {'executed': False, 'reason': str(exc)}

    @staticmethod
    def _ensure_trading_client(config: TradingConfig) -> Optional[TradingClient]:
        """保持单例TradingClient，避免重复建立连接"""
        with ExecutionEngine._client_lock:
            if ExecutionEngine._trading_client is None:
                try:
                    ExecutionEngine._trading_client = TradingClient(
                        api_key=config.api_key,
                        secret_key=config.secret_key,
                        paper=config.is_test
                    )
                except Exception as exc:
                    log.error(f"初始化Alpaca TradingClient失败: {exc}")
                    ExecutionEngine._trading_client = None
            return ExecutionEngine._trading_client

    @staticmethod
    def _map_side(signal_type: str) -> Optional[OrderSide]:
        """将内部信号类型映射为Alpaca下单方向"""
        signal_type = signal_type.upper()
        if signal_type == "BUY":
            return OrderSide.BUY
        if signal_type == "SELL":
            return OrderSide.SELL
        return None

    @staticmethod
    def _resolve_time_in_force(_: str) -> TimeInForce:
        """固定使用IOC（立即成交或取消）"""
        return TimeInForce.IOC

    @staticmethod
    @publish_event(EventTypes.SIGNAL_GENERATED, source='ExecutionEngine')
    def _emit_signal_event(signal: TradingSignal,
                           order_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """发布信号执行事件（使用装饰器）"""
        executed = order_payload.get('executed', True) if order_payload else True
        event = {
            'symbol': signal.symbol,
            'signal_type': signal.signal_type,
            'price': signal.price,
            'confidence': signal.confidence,
            'reason': signal.reason,
            'timestamp': signal.timestamp,
            'executed': executed
        }
        if order_payload:
            event.update({'order': order_payload})
        return event

    @staticmethod
    def get_last_signal(symbol: str) -> Optional[TradingSignal]:
        """获取指定股票的最后执行信号"""
        return ExecutionEngine._last_signals.get(symbol)
