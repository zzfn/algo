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
from .execution_engine import ExecutionEngine

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

        # 注意：现在使用纯函数版本的价格行为分析器和执行引擎，无需实例化

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

            # 集成的信号生成（包含市场分析、模式识别和信号生成）
            signal, market_context = PriceActionAnalyzer.signal_generation(
                recent_bars,
                bar_data,
                last_signal=self.last_signal
            )
            self.current_context = market_context

            # 发布市场分析结果事件
            self._emit_market_analysis_update(market_context)

            # 5. 执行决策（包含风险管理）
            final_signal = ExecutionEngine.process_signal(signal, market_context)

            if final_signal:
                self.last_signal = final_signal

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


    def get_current_context(self) -> Optional[MarketContext]:
        """获取当前市场背景"""
        return self.current_context

    def get_last_signal(self) -> Optional[TradingSignal]:
        """获取最后的交易信号"""
        return self.last_signal



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
