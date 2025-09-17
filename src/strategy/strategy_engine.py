"""
策略引擎 - 协调单个股票的策略流水线
处理：市场分析 → 模式识别 → 信号生成 → 风险管理 → 执行
"""

import pandas as pd
from typing import Optional, Dict, Any
from collections import deque
import threading

from models.market_data import BarData
from models.strategy_data import TradingSignal, MarketContext
from utils.log import setup_logging
from config.config import TradingConfig
from utils.events import event_bus, EventTypes, publish_event
from utils.data_transforms import bars_to_dataframe, get_latest_bars_slice
from .price_action_analyzer import PriceActionAnalyzer, PriceActionContext, BarQuality, MarketStructure

log = setup_logging(module_prefix='STRATEGY')


class StrategyEngine:
    """
    策略引擎 - 协调单个股票的完整策略流水线
    """

    def __init__(self, symbol: str, config: Optional[TradingConfig] = None, preloaded_historical_data: Optional[list] = None):
        self.symbol = symbol
        self.config = config or TradingConfig.create()
        self.historical_data: Optional[pd.DataFrame] = None
        self.current_context: Optional[MarketContext] = None

        # 策略状态
        self.last_signal: Optional[TradingSignal] = None
        self.position_size: float = 0.0  # 当前持仓

        # 实时数据缓存
        self.buffer_size = getattr(config, 'buffer_size', 1000) if config else 1000
        self.bar_buffer: deque = deque(maxlen=self.buffer_size)
        self.latest_bar: Optional[BarData] = None
        self.lock = threading.Lock()

        # 注意：现在使用纯函数版本的价格行为分析器，无需实例化

        # 加载预加载的历史数据
        self._load_preloaded_data(preloaded_historical_data or [])

    def _load_preloaded_data(self, historical_data: list):
        """使用预加载的历史数据"""
        if historical_data:
            # 将预加载的BarData对象直接添加到buffer
            for bar_data in historical_data:
                self.bar_buffer.append(bar_data)

            log.info(f"{self.symbol}: 使用预加载的{len(historical_data)}根历史K线")

            # 保留DataFrame格式的历史数据作为备份（可选）
            self.historical_data = bars_to_dataframe(historical_data)
        else:
            log.warning(f"{self.symbol}: 预加载历史数据为空")
            self.historical_data = pd.DataFrame()


    def process_new_bar(self, bar_data: BarData) -> Optional[TradingSignal]:
        """
        处理新的K线数据，执行完整的策略流水线（使用纯函数版本）
        """
        try:
            # 先添加新K线到缓存
            self.add_bar(bar_data)

            # 获取最近的K线数据用于分析
            recent_bars = self.get_recent_bars(50)
            if len(recent_bars) < 20:  # 数据不够，跳过
                return None

            # 1. 市场分析（纯函数）
            market_context = PriceActionAnalyzer.market_analysis(recent_bars, bar_data)
            self.current_context = market_context

            # 发布市场分析结果事件
            self._emit_market_analysis_update(market_context)

            # 2. 模式识别（纯函数）
            patterns = PriceActionAnalyzer.pattern_recognition(recent_bars, market_context)

            # 4. 信号生成（纯函数）
            signal = PriceActionAnalyzer.signal_generation(patterns, market_context, bar_data)

            # 5. 风险管理（纯函数）
            final_signal = PriceActionAnalyzer.risk_management(signal, market_context, self.last_signal)

            # 6. 执行决策
            if final_signal:
                self.last_signal = final_signal
                log.info(f"{self.symbol}: 生成{final_signal.signal_type}信号 "
                        f"@{final_signal.price:.2f} 置信度:{final_signal.confidence:.2f}")

                # 直接处理交易信号
                self.handle_trading_signal(final_signal)

            return final_signal

        except Exception as e:
            log.error(f"{self.symbol} 策略处理错误: {e}")
            return None









    @publish_event(EventTypes.MARKET_ANALYSIS_UPDATED, source='StrategyEngine')
    def _emit_market_analysis_update(self, market_context: MarketContext) -> Dict[str, Any]:
        """发布市场分析更新事件（使用装饰器）"""
        return {
            'symbol': self.symbol,
            'trend': market_context.trend,
            'volatility': market_context.volatility,
            'volume_profile': market_context.volume_profile,
            'position_size': self.position_size,
            'current_price': market_context.current_price
        }

    @publish_event(EventTypes.SIGNAL_GENERATED, source='StrategyEngine')
    def _emit_signal_event(self, signal: TradingSignal) -> Dict[str, Any]:
        """发布信号生成事件（使用装饰器）"""
        return {
            'symbol': signal.symbol,
            'signal_type': signal.signal_type,
            'price': signal.price,
            'confidence': signal.confidence,
            'reason': signal.reason,
            'timestamp': signal.timestamp,
            'executed': False
        }

    def get_current_context(self) -> Optional[MarketContext]:
        """获取当前市场背景"""
        return self.current_context

    def get_last_signal(self) -> Optional[TradingSignal]:
        """获取最后的交易信号"""
        return self.last_signal

    def handle_trading_signal(self, signal: TradingSignal):
        """处理生成的交易信号"""
        log.info(f"{self.symbol}: {signal.signal_type}信号 "
                f"@{signal.price:.2f} 置信度:{signal.confidence:.2f} 原因:{signal.reason}")

        # 使用装饰器发布信号事件
        self._emit_signal_event(signal)

        # TODO: 在这里实现具体的交易执行逻辑
        # 例如：下单、仓位管理、风险控制等
        # 每个策略引擎可以有不同的执行逻辑


    def add_bar(self, bar: BarData):
        """添加新的K线数据到缓存"""
        with self.lock:
            self.bar_buffer.append(bar)
            self.latest_bar = bar

    def get_recent_bars(self, count: int = 50) -> pd.DataFrame:
        """获取最近的K线数据"""
        with self.lock:
            if len(self.bar_buffer) == 0:
                return pd.DataFrame()

            # 获取最近的K线并转换为DataFrame
            all_bars = list(self.bar_buffer)
            recent_bars = get_latest_bars_slice(all_bars, count)
            return bars_to_dataframe(recent_bars)

    def get_current_price(self) -> Optional[float]:
        """获取当前价格"""
        with self.lock:
            # 使用最新K线收盘价
            if self.latest_bar is not None:
                return self.latest_bar.close

            return None