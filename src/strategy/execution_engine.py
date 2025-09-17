"""
执行引擎 - 处理风险管理和交易执行决策
从策略信号到实际交易执行的桥梁
"""

from typing import Optional, Dict, Any
from datetime import datetime

from models.strategy_data import TradingSignal, MarketContext
from utils.log import setup_logging
from utils.events import publish_event, EventTypes

log = setup_logging(module_prefix='EXECUTION')


class ExecutionEngine:
    """
    执行引擎 - 负责风险管理和交易执行决策
    使用静态方法，不需要实例化
    """

    # 类级别状态，跨调用保持
    _last_signals: Dict[str, TradingSignal] = {}

    @staticmethod
    def process_signal(signal: Optional[TradingSignal],
                      market_context: MarketContext) -> Optional[TradingSignal]:
        """
        处理交易信号：风险管理 + 执行决策

        Args:
            signal: 原始交易信号
            market_context: 市场环境

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
            ExecutionEngine._handle_signal_execution(final_signal)

        return final_signal

    @staticmethod
    def _risk_management(signal: TradingSignal,
                        context: MarketContext) -> Optional[TradingSignal]:
        """风险管理 - 过滤和调整信号"""
        # 波动率过滤
        if context.volatility > 5.0:
            log.warning(f"{signal.symbol}: 波动率过高({context.volatility:.2f})，拒绝信号")
            return None

        # 成交量过滤
        if context.volume_profile == "LOW":
            log.info(f"{signal.symbol}: 成交量偏低，降低信号置信度")
            return TradingSignal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence * 0.7,
                price=signal.price,
                timestamp=signal.timestamp,
                reason=signal.reason + " (成交量偏低)"
            )

        # 信号频率控制
        last_signal = ExecutionEngine._last_signals.get(signal.symbol)
        if (last_signal and
            signal.signal_type == last_signal.signal_type and
            (signal.timestamp - last_signal.timestamp).total_seconds() < 300):
            log.info(f"{signal.symbol}: 信号频率过高，跳过重复信号")
            return None

        return signal

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
    def _handle_signal_execution(signal: TradingSignal):
        """处理信号执行"""
        log.info(f"{signal.symbol}: 执行{signal.signal_type}信号 "
                f"@{signal.price:.2f} 置信度:{signal.confidence:.2f} "
                f"原因:{signal.reason}")

        # 发布信号执行事件
        ExecutionEngine._emit_signal_event(signal)

        # TODO: 在这里实现具体的交易执行逻辑
        # 例如：下单、仓位管理、风险控制等

    @staticmethod
    @publish_event(EventTypes.SIGNAL_GENERATED, source='ExecutionEngine')
    def _emit_signal_event(signal: TradingSignal) -> Dict[str, Any]:
        """发布信号执行事件（使用装饰器）"""
        return {
            'symbol': signal.symbol,
            'signal_type': signal.signal_type,
            'price': signal.price,
            'confidence': signal.confidence,
            'reason': signal.reason,
            'timestamp': signal.timestamp,
            'executed': True
        }

    @staticmethod
    def get_last_signal(symbol: str) -> Optional[TradingSignal]:
        """获取指定股票的最后执行信号"""
        return ExecutionEngine._last_signals.get(symbol)