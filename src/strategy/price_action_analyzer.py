"""
纯函数版本的价格行为分析器
基于 Al Brooks 价格行为学的无状态分析函数
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from models.market_data import BarData
from models.strategy_data import TradingSignal, MarketContext


class BarQuality(Enum):
    """K线质量"""
    STRONG_BULL = "strong_bull"      # 强势看涨K线
    WEAK_BULL = "weak_bull"          # 弱势看涨K线
    STRONG_BEAR = "strong_bear"      # 强势看跌K线
    WEAK_BEAR = "weak_bear"          # 弱势看跌K线
    DOJI = "doji"                    # 十字星
    REVERSAL = "reversal"            # 反转K线


class MarketStructure(Enum):
    """市场结构"""
    STRONG_TREND_UP = "strong_trend_up"      # 强势上升趋势
    WEAK_TREND_UP = "weak_trend_up"          # 弱势上升趋势
    STRONG_TREND_DOWN = "strong_trend_down"  # 强势下降趋势
    WEAK_TREND_DOWN = "weak_trend_down"      # 弱势下降趋势
    TRADING_RANGE = "trading_range"          # 交易区间
    BREAKOUT_ATTEMPT = "breakout_attempt"    # 突破尝试


@dataclass
class PriceActionContext:
    """价格行为市场背景"""
    symbol: str
    current_price: float
    bar_quality: BarQuality
    market_structure: MarketStructure
    trend_strength: float           # 趋势强度 0-1
    at_key_level: bool             # 是否在关键位置
    key_level_type: Optional[str]  # 关键位置类型
    consecutive_pattern: Optional[str]  # 连续K线模式


@dataclass
class AnalysisState:
    """分析状态数据结构"""
    last_signal: Optional[TradingSignal]
    position_size: float
    current_context: Optional[MarketContext]


class PriceActionAnalyzer:
    """价格行为分析器"""

    @staticmethod
    def analyze_market_context(bars: pd.DataFrame, current_bar: BarData) -> PriceActionContext:
        """纯函数：分析当前市场的价格行为背景"""
        if bars.empty or len(bars) < 5:
            return PriceActionContext(
                symbol=current_bar.symbol,
                current_price=current_bar.close,
                bar_quality=BarQuality.DOJI,
                market_structure=MarketStructure.TRADING_RANGE,
                trend_strength=0.0,
                at_key_level=False,
                key_level_type=None,
                consecutive_pattern=None
            )

        # 分析市场结构和趋势强度
        if len(bars) < 10:
            market_structure, trend_strength = PriceActionAnalyzer._simple_trend_analysis(bars, current_bar)
        else:
            market_structure, trend_strength = PriceActionAnalyzer._analyze_market_structure(bars, current_bar)

        # 分析当前K线质量
        bar_quality = PriceActionAnalyzer._analyze_bar_quality(current_bar, bars)

        # 检查是否在关键位置
        at_key_level, key_level_type = PriceActionAnalyzer._check_key_levels(bars, current_bar)

        # 分析连续K线模式
        consecutive_pattern = PriceActionAnalyzer._analyze_consecutive_pattern(bars)

        return PriceActionContext(
            symbol=current_bar.symbol,
            current_price=current_bar.close,
            bar_quality=bar_quality,
            market_structure=market_structure,
            trend_strength=trend_strength,
            at_key_level=at_key_level,
            key_level_type=key_level_type,
            consecutive_pattern=consecutive_pattern
        )

    @staticmethod
    def market_analysis(bars: pd.DataFrame, current_bar: BarData) -> MarketContext:
        """纯函数：基于Al Brooks价格行为学的市场分析"""
        if bars.empty or len(bars) < 20:
            return MarketContext(
                symbol=current_bar.symbol,
                current_price=current_bar.close,
                trend="UNKNOWN",
                volatility=0.0,
                volume_profile="UNKNOWN"
            )

        # 使用价格行为分析获取市场背景
        price_action_context = PriceActionAnalyzer.analyze_market_context(bars, current_bar)

        # 将价格行为分析结果转换为传统的MarketContext格式
        trend = PriceActionAnalyzer._convert_market_structure_to_trend(price_action_context.market_structure)

        # 基于趋势强度和K线质量计算波动率指标
        volatility = PriceActionAnalyzer._calculate_price_action_volatility(price_action_context)

        # 成交量分析
        volume_profile = PriceActionAnalyzer._analyze_volume_profile(bars, current_bar)

        return MarketContext(
            symbol=current_bar.symbol,
            current_price=current_bar.close,
            trend=trend,
            volatility=volatility,
            volume_profile=volume_profile
        )

    @staticmethod
    def pattern_recognition(bars: pd.DataFrame, context: MarketContext) -> Dict[str, Any]:
        """纯函数：模式识别 - Al Brooks价格行为模式"""
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

        # 检测反转模式（更严格的条件）
        if len(recent_bars) >= 5:
            last_5_closes = recent_bars['close'].tail(5)
            # 需要更强的信号确认反转
            strong_ascending = all(last_5_closes.iloc[i] < last_5_closes.iloc[i+1] for i in range(4))
            strong_descending = all(last_5_closes.iloc[i] > last_5_closes.iloc[i+1] for i in range(4))

            # 只有在强趋势中才考虑反转，弱趋势中的回调不算反转
            is_strong_uptrend = context.trend == "UPTREND" and context.volatility > 2.0
            is_strong_downtrend = context.trend == "DOWNTREND" and context.volatility > 2.0

            patterns['reversal'] = {
                'bullish_reversal': strong_ascending and is_strong_downtrend,
                'bearish_reversal': strong_descending and is_strong_uptrend
            }

        return patterns

    @staticmethod
    def signal_generation(patterns: Dict[str, Any], context: MarketContext, bar: BarData) -> Optional[TradingSignal]:
        """纯函数：信号生成"""
        # 基于模式和市场背景生成信号
        if 'breakout' in patterns:
            breakout = patterns['breakout']

            # 上涨突破信号
            if (breakout['high_break'] and
                context.trend in ["UPTREND", "SIDEWAYS"] and
                context.volume_profile in ["HIGH", "NORMAL"] and
                context.volatility > 1.0):

                confidence = 0.8 if context.trend == "UPTREND" else 0.6
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="BUY",
                    confidence=confidence,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="向上突破 + 上升趋势"
                )

            # 下跌突破信号
            if (breakout['low_break'] and
                context.trend in ["DOWNTREND", "SIDEWAYS"] and
                context.volume_profile in ["HIGH", "NORMAL"] and
                context.volatility > 1.0):

                confidence = 0.8 if context.trend == "DOWNTREND" else 0.6
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="SELL",
                    confidence=confidence,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="向下突破 + 下降趋势"
                )

        # 反转信号（只在强趋势中考虑）
        if 'reversal' in patterns:
            reversal = patterns['reversal']

            if reversal.get('bullish_reversal', False):
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="BUY",
                    confidence=0.7,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="强势看涨反转模式"
                )

            if reversal.get('bearish_reversal', False):
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="SELL",
                    confidence=0.7,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="强势看跌反转模式"
                )

        return None

    @staticmethod
    def risk_management(signal: Optional[TradingSignal],
                       context: MarketContext,
                       last_signal: Optional[TradingSignal]) -> Optional[TradingSignal]:
        """纯函数：风险管理 - 过滤和调整信号"""
        if not signal:
            return None

        # 波动率过滤
        if context.volatility > 5.0:
            return None

        # 成交量过滤
        if context.volume_profile == "LOW":
            # 创建新的信号对象，降低置信度
            return TradingSignal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence * 0.7,
                price=signal.price,
                timestamp=signal.timestamp,
                reason=signal.reason + " (成交量偏低)"
            )

        # 信号频率控制
        if (last_signal and
            signal.signal_type == last_signal.signal_type and
            (signal.timestamp - last_signal.timestamp).total_seconds() < 300):
            return None

        return signal

    # 私有辅助方法
    @staticmethod
    def _analyze_bar_quality(current_bar: BarData, bars: pd.DataFrame) -> BarQuality:
        """分析K线质量"""
        body = abs(current_bar.close - current_bar.open)
        total_range = current_bar.high - current_bar.low

        if total_range == 0:
            return BarQuality.DOJI

        body_ratio = body / total_range

        # 计算上下影线
        if current_bar.close > current_bar.open:  # 阳线
            upper_shadow = current_bar.high - current_bar.close
            lower_shadow = current_bar.open - current_bar.low
        else:  # 阴线
            upper_shadow = current_bar.high - current_bar.open
            lower_shadow = current_bar.close - current_bar.low

        upper_shadow_ratio = upper_shadow / total_range if total_range > 0 else 0
        lower_shadow_ratio = lower_shadow / total_range if total_range > 0 else 0

        # 十字星判断
        if body_ratio < 0.1:
            return BarQuality.DOJI

        # 反转K线判断
        if PriceActionAnalyzer._is_reversal_bar(current_bar, bars):
            return BarQuality.REVERSAL

        # 强弱K线判断
        if current_bar.close > current_bar.open:  # 阳线
            if body_ratio > 0.7 and upper_shadow_ratio < 0.2:
                return BarQuality.STRONG_BULL
            else:
                return BarQuality.WEAK_BULL
        else:  # 阴线
            if body_ratio > 0.7 and lower_shadow_ratio < 0.2:
                return BarQuality.STRONG_BEAR
            else:
                return BarQuality.WEAK_BEAR

    @staticmethod
    def _is_reversal_bar(current_bar: BarData, bars: pd.DataFrame) -> bool:
        """判断是否为反转K线"""
        if len(bars) < 3:
            return False

        recent_bars = bars.tail(3)

        # 锤头线（下影线长，实体小，在下降趋势中）
        body = abs(current_bar.close - current_bar.open)
        total_range = current_bar.high - current_bar.low
        lower_shadow = min(current_bar.open, current_bar.close) - current_bar.low

        if total_range > 0 and lower_shadow > body * 2 and body / total_range < 0.3:
            # 检查是否在下降趋势中
            if PriceActionAnalyzer._is_in_downtrend(recent_bars):
                return True

        # 上吊线（上影线长，实体小，在上升趋势中）
        upper_shadow = current_bar.high - max(current_bar.open, current_bar.close)
        if total_range > 0 and upper_shadow > body * 2 and body / total_range < 0.3:
            # 检查是否在上升趋势中
            if PriceActionAnalyzer._is_in_uptrend(recent_bars):
                return True

        return False

    @staticmethod
    def _is_in_uptrend(bars: pd.DataFrame) -> bool:
        """判断是否处于上升趋势"""
        if len(bars) < 3:
            return False
        closes = bars['close'].values
        return closes[-1] > closes[-2] > closes[-3]

    @staticmethod
    def _is_in_downtrend(bars: pd.DataFrame) -> bool:
        """判断是否处于下降趋势"""
        if len(bars) < 3:
            return False
        closes = bars['close'].values
        return closes[-1] < closes[-2] < closes[-3]

    @staticmethod
    def _analyze_market_structure(bars: pd.DataFrame, current_bar: BarData) -> Tuple[MarketStructure, float]:
        """分析市场结构和趋势强度"""
        if len(bars) < 10:
            return MarketStructure.TRADING_RANGE, 0.0

        # 分析高点低点序列
        highs = bars['high'].values
        lows = bars['low'].values
        closes = bars['close'].values

        # 获取最近的高低点
        recent_highs = PriceActionAnalyzer._find_local_peaks(highs[-20:], window=2)
        recent_lows = PriceActionAnalyzer._find_local_valleys(lows[-20:], window=2)

        # 判断趋势方向和强度
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            # 高点序列分析
            higher_highs = recent_highs[-1] > recent_highs[-2] if len(recent_highs) >= 2 else False
            higher_lows = recent_lows[-1] > recent_lows[-2] if len(recent_lows) >= 2 else False

            lower_highs = recent_highs[-1] < recent_highs[-2] if len(recent_highs) >= 2 else False
            lower_lows = recent_lows[-1] < recent_lows[-2] if len(recent_lows) >= 2 else False

            # 计算趋势强度
            price_range = max(highs[-20:]) - min(lows[-20:])
            if price_range == 0:
                trend_strength = 0.0
            else:
                recent_move = abs(closes[-1] - closes[-10])
                trend_strength = min(recent_move / price_range, 1.0)

            # 判断市场结构
            if higher_highs and higher_lows:
                if trend_strength > 0.6:
                    return MarketStructure.STRONG_TREND_UP, trend_strength
                else:
                    return MarketStructure.WEAK_TREND_UP, trend_strength
            elif lower_highs and lower_lows:
                if trend_strength > 0.6:
                    return MarketStructure.STRONG_TREND_DOWN, trend_strength
                else:
                    return MarketStructure.WEAK_TREND_DOWN, trend_strength
            else:
                return PriceActionAnalyzer._analyze_ema_trend(bars, current_bar)
        else:
            return PriceActionAnalyzer._analyze_ema_trend(bars, current_bar)

    @staticmethod
    def _find_local_peaks(data: List[float], window: int = 2) -> List[float]:
        """寻找局部高点"""
        peaks = []
        if len(data) < window * 2 + 1:
            return peaks

        for i in range(window, len(data) - window):
            is_peak = True
            for j in range(1, window + 1):
                if data[i] < data[i-j] or data[i] < data[i+j]:
                    is_peak = False
                    break
            if is_peak:
                peaks.append(data[i])
        return peaks

    @staticmethod
    def _find_local_valleys(data: List[float], window: int = 2) -> List[float]:
        """寻找局部低点"""
        valleys = []
        if len(data) < window * 2 + 1:
            return valleys

        for i in range(window, len(data) - window):
            is_valley = True
            for j in range(1, window + 1):
                if data[i] > data[i-j] or data[i] > data[i+j]:
                    is_valley = False
                    break
            if is_valley:
                valleys.append(data[i])
        return valleys

    @staticmethod
    def _check_key_levels(bars: pd.DataFrame, current_bar: BarData) -> Tuple[bool, Optional[str]]:
        """检查是否在关键支撑阻力位"""
        if len(bars) < 20:
            return False, None

        current_price = current_bar.close

        # 寻找重要的支撑阻力位
        highs = bars['high'].values
        lows = bars['low'].values

        # 寻找最近20根K线的重要高低点
        recent_highs = PriceActionAnalyzer._find_local_peaks(highs[-20:])
        recent_lows = PriceActionAnalyzer._find_local_valleys(lows[-20:])

        # 检查当前价格是否接近这些关键位置
        tolerance = (max(highs[-20:]) - min(lows[-20:])) * 0.005  # 0.5%容差

        for high in recent_highs:
            if abs(current_price - high) <= tolerance:
                return True, "resistance"

        for low in recent_lows:
            if abs(current_price - low) <= tolerance:
                return True, "support"

        return False, None

    @staticmethod
    def _analyze_consecutive_pattern(bars: pd.DataFrame) -> Optional[str]:
        """分析连续K线模式"""
        if len(bars) < 5:
            return None

        recent_closes = bars['close'].tail(5).values

        # 连续上涨
        if all(recent_closes[i] < recent_closes[i+1] for i in range(4)):
            return "consecutive_bull"

        # 连续下跌
        if all(recent_closes[i] > recent_closes[i+1] for i in range(4)):
            return "consecutive_bear"

        # 三连阳/阴
        if len(recent_closes) >= 3:
            if all(recent_closes[i] < recent_closes[i+1] for i in range(-3, -1)):
                return "three_bull"
            if all(recent_closes[i] > recent_closes[i+1] for i in range(-3, -1)):
                return "three_bear"

        return None

    @staticmethod
    def _analyze_ema_trend(bars: pd.DataFrame, current_bar: BarData) -> Tuple[MarketStructure, float]:
        """基于EMA20简单趋势判断"""
        if len(bars) < 20:
            return MarketStructure.TRADING_RANGE, 0.0

        # 计算EMA20
        closes = bars['close']
        ema20 = closes.ewm(span=20).mean()
        current_price = current_bar.close
        current_ema = ema20.iloc[-1]

        # 检查最近几根K线是否反复穿越EMA20
        recent_crosses = PriceActionAnalyzer._count_ema_crosses(bars.tail(10), ema20.tail(10))

        # 计算价格偏离EMA的程度作为趋势强度
        price_deviation = abs(current_price - current_ema) / current_ema if current_ema > 0 else 0.0
        trend_strength = min(price_deviation * 10, 1.0)

        # 判断逻辑
        if recent_crosses >= 3:
            return MarketStructure.TRADING_RANGE, trend_strength
        elif current_price > current_ema * 1.001:
            if trend_strength > 0.5:
                return MarketStructure.STRONG_TREND_UP, trend_strength
            else:
                return MarketStructure.WEAK_TREND_UP, trend_strength
        elif current_price < current_ema * 0.999:
            if trend_strength > 0.5:
                return MarketStructure.STRONG_TREND_DOWN, trend_strength
            else:
                return MarketStructure.WEAK_TREND_DOWN, trend_strength
        else:
            return MarketStructure.TRADING_RANGE, trend_strength

    @staticmethod
    def _count_ema_crosses(bars: pd.DataFrame, ema_values: pd.Series) -> int:
        """计算价格穿越EMA的次数"""
        if len(bars) < 2 or len(ema_values) < 2:
            return 0

        crosses = 0
        closes = bars['close'].values
        ema_vals = ema_values.values

        for i in range(1, len(closes)):
            prev_above = closes[i-1] > ema_vals[i-1]
            curr_above = closes[i] > ema_vals[i]

            if prev_above != curr_above:
                crosses += 1

        return crosses

    @staticmethod
    def _simple_trend_analysis(bars: pd.DataFrame, current_bar: BarData) -> Tuple[MarketStructure, float]:
        """简单的价格趋势分析（当数据不足20根时使用）"""
        if len(bars) < 5:
            return MarketStructure.TRADING_RANGE, 0.0

        closes = bars['close']
        current_price = current_bar.close

        if len(bars) >= 10:
            ema = closes.ewm(span=10).mean()
            current_ema = ema.iloc[-1]
        else:
            current_ema = closes.mean()

        # 计算趋势强度
        price_deviation = abs(current_price - current_ema) / current_ema if current_ema > 0 else 0.0
        trend_strength = min(price_deviation * 10, 1.0)

        # 判断趋势
        if current_price > current_ema * 1.002:
            return MarketStructure.WEAK_TREND_UP, trend_strength
        elif current_price < current_ema * 0.998:
            return MarketStructure.WEAK_TREND_DOWN, trend_strength
        else:
            return MarketStructure.TRADING_RANGE, trend_strength

    @staticmethod
    def _convert_market_structure_to_trend(market_structure: MarketStructure) -> str:
        """将市场结构转换为趋势字符串"""
        if market_structure in [MarketStructure.STRONG_TREND_UP, MarketStructure.WEAK_TREND_UP]:
            return "UPTREND"
        elif market_structure in [MarketStructure.STRONG_TREND_DOWN, MarketStructure.WEAK_TREND_DOWN]:
            return "DOWNTREND"
        elif market_structure == MarketStructure.TRADING_RANGE:
            return "SIDEWAYS"
        elif market_structure == MarketStructure.BREAKOUT_ATTEMPT:
            return "BREAKOUT"
        else:
            return "UNKNOWN"

    @staticmethod
    def _calculate_price_action_volatility(context: PriceActionContext) -> float:
        """基于价格行为背景计算波动率指标"""
        # 基础波动率基于趋势强度
        base_volatility = context.trend_strength * 3.0

        # 根据K线质量调整
        if context.bar_quality in [BarQuality.STRONG_BULL, BarQuality.STRONG_BEAR]:
            base_volatility *= 1.2
        elif context.bar_quality == BarQuality.DOJI:
            base_volatility *= 0.7
        elif context.bar_quality == BarQuality.REVERSAL:
            base_volatility *= 1.5

        # 在关键位置增加波动率
        if context.at_key_level:
            base_volatility *= 1.3

        return min(base_volatility, 10.0)

    @staticmethod
    def _analyze_volume_profile(bars: pd.DataFrame, current_bar: BarData) -> str:
        """分析成交量概况"""
        if len(bars) < 10:
            return "UNKNOWN"

        avg_volume = bars['volume'].rolling(window=10).mean().iloc[-1]
        current_volume = current_bar.volume

        if current_volume > avg_volume * 1.5:
            return "HIGH"
        elif current_volume < avg_volume * 0.5:
            return "LOW"
        else:
            return "NORMAL"