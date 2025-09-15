"""
策略引擎 - 协调单个股票的策略流水线
处理：市场分析 → 模式识别 → 信号生成 → 风险管理 → 执行
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from collections import deque
import threading

from src.models.market_data import BarData
from src.models.strategy_data import TradingSignal, MarketContext
from src.utils.log import setup_logging
from src.config.config import TradingConfig
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from src.utils.data_transforms import alpaca_bars_to_dataframe, bars_to_dataframe, get_latest_bars_slice

log = setup_logging()


class StrategyEngine:
    """
    策略引擎 - 协调单个股票的完整策略流水线
    """

    def __init__(self, symbol: str, config: Optional[TradingConfig] = None):
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

        # 自动加载历史数据
        self._load_historical_data()

    def _load_historical_data(self, days: int = 30):
        """自动加载历史数据"""
        try:
            client = StockHistoricalDataClient(
                api_key=self.config.api_key,
                secret_key=self.config.secret_key
            )

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            request = StockBarsRequest(
                symbol_or_symbols=[self.symbol],
                timeframe=TimeFrame.Minute,
                start=start_date,
                end=end_date,
                feed=self.config.data_feed
            )

            bars = client.get_stock_bars(request)
            symbol_bars = bars.data.get(self.symbol, [])

            if symbol_bars:
                self.historical_data = alpaca_bars_to_dataframe(symbol_bars)
                log.info(f"[STRATEGY] {self.symbol}: 自动加载了{len(self.historical_data)}根历史K线")
            else:
                log.warning(f"[STRATEGY] {self.symbol}: 未获取到历史数据")
                self.historical_data = pd.DataFrame()

        except Exception as e:
            log.error(f"[STRATEGY] {self.symbol}: 加载历史数据失败: {e}")
            self.historical_data = pd.DataFrame()


    def process_new_bar(self, bar_data: BarData) -> Optional[TradingSignal]:
        """
        处理新的K线数据，执行完整的策略流水线
        """
        try:
            # 先添加新K线到缓存
            self.add_bar(bar_data)

            # 获取最近的K线数据用于分析
            recent_bars = self.get_recent_bars(50)
            if len(recent_bars) < 20:  # 数据不够，跳过
                return None

            # 1. 市场分析
            market_context = self._market_analysis(recent_bars, bar_data)
            self.current_context = market_context

            # 2. 模式识别
            patterns = self._pattern_recognition(recent_bars, market_context)

            # 4. 信号生成
            signal = self._signal_generation(patterns, market_context, bar_data)

            # 5. 风险管理
            final_signal = self._risk_management(signal, market_context)

            # 6. 执行决策
            if final_signal:
                self.last_signal = final_signal
                log.info(f"[STRATEGY] {self.symbol}: 生成{final_signal.signal_type}信号 "
                        f"@{final_signal.price:.2f} 置信度:{final_signal.confidence:.2f}")

                # 直接处理交易信号
                self.handle_trading_signal(final_signal)

            return final_signal

        except Exception as e:
            log.error(f"[STRATEGY] {self.symbol} 策略处理错误: {e}")
            return None


    def _market_analysis(self, bars: pd.DataFrame, current_bar: BarData) -> MarketContext:
        """2. 市场分析 - 分析当前市场状态"""
        if bars.empty or len(bars) < 20:
            return MarketContext(
                symbol=self.symbol,
                current_price=current_bar.close,
                trend="UNKNOWN",
                volatility=0.0,
                volume_profile="UNKNOWN"
            )

        # 趋势分析（简化版）
        ma20 = bars['close'].rolling(window=20).mean().iloc[-1]
        current_price = current_bar.close

        if current_price > ma20 * 1.02:
            trend = "UPTREND"
        elif current_price < ma20 * 0.98:
            trend = "DOWNTREND"
        else:
            trend = "SIDEWAYS"

        # 波动率分析
        returns = bars['close'].pct_change().dropna()
        volatility = returns.std() * 100 if len(returns) > 0 else 0.0

        # 成交量分析
        avg_volume = bars['volume'].rolling(window=10).mean().iloc[-1]
        current_volume = current_bar.volume

        if current_volume > avg_volume * 1.5:
            volume_profile = "HIGH"
        elif current_volume < avg_volume * 0.5:
            volume_profile = "LOW"
        else:
            volume_profile = "NORMAL"

        return MarketContext(
            symbol=self.symbol,
            current_price=current_price,
            trend=trend,
            volatility=volatility,
            volume_profile=volume_profile
        )

    def _pattern_recognition(self, bars: pd.DataFrame, context: MarketContext) -> Dict[str, Any]:
        """3. 模式识别 - Al Brooks价格行为模式"""
        patterns = {}

        if bars.empty or len(bars) < 10:
            return patterns

        # 简单的价格行为模式识别
        recent_bars = bars.tail(5)

        # 检测突破模式
        high_break = context.current_price > recent_bars['high'].max()
        low_break = context.current_price < recent_bars['low'].min()

        patterns['breakout'] = {
            'high_break': high_break,
            'low_break': low_break,
            'strength': context.volatility
        }

        # 检测反转模式（简化）
        if len(recent_bars) >= 3:
            last_3_closes = recent_bars['close'].tail(3)
            ascending = all(last_3_closes.iloc[i] < last_3_closes.iloc[i+1] for i in range(2))
            descending = all(last_3_closes.iloc[i] > last_3_closes.iloc[i+1] for i in range(2))

            patterns['reversal'] = {
                'bullish_reversal': ascending and context.trend == "DOWNTREND",
                'bearish_reversal': descending and context.trend == "UPTREND"
            }

        return patterns

    def _signal_generation(self, patterns: Dict[str, Any], context: MarketContext, bar: BarData) -> Optional[TradingSignal]:
        """4. 信号生成"""

        # 基于模式和市场背景生成信号
        if 'breakout' in patterns:
            breakout = patterns['breakout']

            # 上涨突破信号
            if (breakout['high_break'] and
                context.trend in ["UPTREND", "SIDEWAYS"] and
                context.volume_profile in ["HIGH", "NORMAL"]):

                return TradingSignal(
                    symbol=self.symbol,
                    signal_type="BUY",
                    confidence=0.7,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="向上突破 + 上升趋势"
                )

            # 下跌突破信号
            if (breakout['low_break'] and
                context.trend in ["DOWNTREND", "SIDEWAYS"] and
                context.volume_profile in ["HIGH", "NORMAL"]):

                return TradingSignal(
                    symbol=self.symbol,
                    signal_type="SELL",
                    confidence=0.7,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="向下突破 + 下降趋势"
                )

        # 反转信号
        if 'reversal' in patterns:
            reversal = patterns['reversal']

            if reversal.get('bullish_reversal', False):
                return TradingSignal(
                    symbol=self.symbol,
                    signal_type="BUY",
                    confidence=0.6,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="看涨反转模式"
                )

            if reversal.get('bearish_reversal', False):
                return TradingSignal(
                    symbol=self.symbol,
                    signal_type="SELL",
                    confidence=0.6,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="看跌反转模式"
                )

        return None

    def _risk_management(self, signal: Optional[TradingSignal], context: MarketContext) -> Optional[TradingSignal]:
        """5. 风险管理 - 过滤和调整信号"""
        if not signal:
            return None

        # 波动率过滤
        if context.volatility > 5.0:  # 5%以上波动率认为风险过高
            log.info(f"[RISK] {self.symbol}: 波动率过高({context.volatility:.2f}%)，过滤信号")
            return None

        # 成交量过滤
        if context.volume_profile == "LOW":
            log.info(f"[RISK] {self.symbol}: 成交量过低，降低信号置信度")
            # 创建新的信号对象，降低置信度
            return TradingSignal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence * 0.7,  # 降低置信度
                price=signal.price,
                timestamp=signal.timestamp,
                reason=signal.reason + " (成交量偏低)"
            )

        # 信号频率控制
        if (self.last_signal and
            signal.signal_type == self.last_signal.signal_type and
            (signal.timestamp - self.last_signal.timestamp).seconds < 300):  # 5分钟内不重复同类信号

            log.info(f"[RISK] {self.symbol}: 信号过于频繁，过滤重复信号")
            return None

        return signal

    def get_current_context(self) -> Optional[MarketContext]:
        """获取当前市场背景"""
        return self.current_context

    def get_last_signal(self) -> Optional[TradingSignal]:
        """获取最后的交易信号"""
        return self.last_signal

    def handle_trading_signal(self, signal: TradingSignal):
        """处理生成的交易信号"""
        log.info(f"[SIGNAL] {self.symbol}: {signal.signal_type}信号 "
                f"@{signal.price:.2f} 置信度:{signal.confidence:.2f} 原因:{signal.reason}")

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