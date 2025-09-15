"""
Al Brooks 价格行为分析器
基于原生价格行为而非技术指标来分析市场
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from models.market_data import BarData


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


class PriceActionAnalyzer:
    """Al Brooks 价格行为分析器"""

    def __init__(self):
        pass

    def analyze_market_context(self, bars: pd.DataFrame, current_bar: BarData) -> PriceActionContext:
        """分析当前市场的价格行为背景"""
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

        # 如果数据不足但大于等于5根，尝试简单的价格趋势分析
        if len(bars) < 10:
            market_structure, trend_strength = self._simple_trend_analysis(bars, current_bar)
        else:
            # 使用正常的市场结构分析
            market_structure, trend_strength = self._analyze_market_structure(bars, current_bar)

        # 1. 分析当前K线质量
        bar_quality = self._analyze_bar_quality(current_bar, bars)

        # 3. 检查是否在关键位置
        at_key_level, key_level_type = self._check_key_levels(bars, current_bar)

        # 4. 分析连续K线模式
        consecutive_pattern = self._analyze_consecutive_pattern(bars)

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

    def _analyze_bar_quality(self, current_bar: BarData, bars: pd.DataFrame) -> BarQuality:
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
        if self._is_reversal_bar(current_bar, bars):
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

    def _is_reversal_bar(self, current_bar: BarData, bars: pd.DataFrame) -> bool:
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
            if self._is_in_downtrend(recent_bars):
                return True

        # 上吊线（上影线长，实体小，在上升趋势中）
        upper_shadow = current_bar.high - max(current_bar.open, current_bar.close)
        if total_range > 0 and upper_shadow > body * 2 and body / total_range < 0.3:
            # 检查是否在上升趋势中
            if self._is_in_uptrend(recent_bars):
                return True

        return False

    def _is_in_uptrend(self, bars: pd.DataFrame) -> bool:
        """判断是否处于上升趋势"""
        if len(bars) < 3:
            return False
        closes = bars['close'].values
        return closes[-1] > closes[-2] > closes[-3]

    def _is_in_downtrend(self, bars: pd.DataFrame) -> bool:
        """判断是否处于下降趋势"""
        if len(bars) < 3:
            return False
        closes = bars['close'].values
        return closes[-1] < closes[-2] < closes[-3]

    def _analyze_market_structure(self, bars: pd.DataFrame, current_bar: BarData) -> Tuple[MarketStructure, float]:
        """分析市场结构和趋势强度"""
        if len(bars) < 10:
            return MarketStructure.TRADING_RANGE, 0.0

        # 分析高点低点序列
        highs = bars['high'].values
        lows = bars['low'].values
        closes = bars['close'].values

        # 获取最近的高低点（降低窗口要求）
        recent_highs = self._find_local_peaks(highs[-20:], window=2)
        recent_lows = self._find_local_valleys(lows[-20:], window=2)

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
                # 当高低点模式不明确时，使用EMA20判断
                return self._analyze_ema_trend(bars, current_bar)
        else:
            # 当无法识别足够的高低点时，使用EMA20判断
            return self._analyze_ema_trend(bars, current_bar)

    def _find_local_peaks(self, data: List[float], window: int = 2) -> List[float]:
        """寻找局部高点（优化版本）"""
        peaks = []
        if len(data) < window * 2 + 1:
            return peaks

        for i in range(window, len(data) - window):
            # 放宽条件：只需要比相邻点高即可
            is_peak = True
            for j in range(1, window + 1):
                if data[i] < data[i-j] or data[i] < data[i+j]:
                    is_peak = False
                    break
            if is_peak:
                peaks.append(data[i])
        return peaks

    def _find_local_valleys(self, data: List[float], window: int = 2) -> List[float]:
        """寻找局部低点（优化版本）"""
        valleys = []
        if len(data) < window * 2 + 1:
            return valleys

        for i in range(window, len(data) - window):
            # 放宽条件：只需要比相邻点低即可
            is_valley = True
            for j in range(1, window + 1):
                if data[i] > data[i-j] or data[i] > data[i+j]:
                    is_valley = False
                    break
            if is_valley:
                valleys.append(data[i])
        return valleys

    def _check_key_levels(self, bars: pd.DataFrame, current_bar: BarData) -> Tuple[bool, Optional[str]]:
        """检查是否在关键支撑阻力位"""
        if len(bars) < 20:
            return False, None

        current_price = current_bar.close

        # 寻找重要的支撑阻力位
        highs = bars['high'].values
        lows = bars['low'].values

        # 寻找最近20根K线的重要高低点
        recent_highs = self._find_local_peaks(highs[-20:])
        recent_lows = self._find_local_valleys(lows[-20:])

        # 检查当前价格是否接近这些关键位置
        tolerance = (max(highs[-20:]) - min(lows[-20:])) * 0.005  # 0.5%容差

        for high in recent_highs:
            if abs(current_price - high) <= tolerance:
                return True, "resistance"

        for low in recent_lows:
            if abs(current_price - low) <= tolerance:
                return True, "support"

        return False, None

    def _analyze_consecutive_pattern(self, bars: pd.DataFrame) -> Optional[str]:
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

    def _analyze_ema_trend(self, bars: pd.DataFrame, current_bar: BarData) -> Tuple[MarketStructure, float]:
        """基于EMA20简单趋势判断：上方=涨，下方=跌，反复穿越=震荡"""
        if len(bars) < 20:
            return MarketStructure.TRADING_RANGE, 0.0

        # 计算EMA20
        closes = bars['close']
        ema20 = closes.ewm(span=20).mean()
        current_price = current_bar.close
        current_ema = ema20.iloc[-1]

        # 检查最近几根K线是否反复穿越EMA20（震荡判断）
        recent_crosses = self._count_ema_crosses(bars.tail(10), ema20.tail(10))

        # 计算价格偏离EMA的程度作为趋势强度
        price_deviation = abs(current_price - current_ema) / current_ema if current_ema > 0 else 0.0
        trend_strength = min(price_deviation * 10, 1.0)  # 放大偏离度

        # 简单判断逻辑
        if recent_crosses >= 3:  # 最近10根K线内穿越3次以上 = 震荡
            return MarketStructure.TRADING_RANGE, trend_strength
        elif current_price > current_ema * 1.001:  # 价格明显高于EMA（0.1%以上）
            if trend_strength > 0.5:
                return MarketStructure.STRONG_TREND_UP, trend_strength
            else:
                return MarketStructure.WEAK_TREND_UP, trend_strength
        elif current_price < current_ema * 0.999:  # 价格明显低于EMA（0.1%以下）
            if trend_strength > 0.5:
                return MarketStructure.STRONG_TREND_DOWN, trend_strength
            else:
                return MarketStructure.WEAK_TREND_DOWN, trend_strength
        else:
            return MarketStructure.TRADING_RANGE, trend_strength

    def _count_ema_crosses(self, bars: pd.DataFrame, ema_values: pd.Series) -> int:
        """计算价格穿越EMA的次数"""
        if len(bars) < 2 or len(ema_values) < 2:
            return 0

        crosses = 0
        closes = bars['close'].values
        ema_vals = ema_values.values

        for i in range(1, len(closes)):
            # 检查是否发生穿越：前一根在EMA下方，当前在上方（或反之）
            prev_above = closes[i-1] > ema_vals[i-1]
            curr_above = closes[i] > ema_vals[i]

            if prev_above != curr_above:  # 发生穿越
                crosses += 1

        return crosses

    def _simple_trend_analysis(self, bars: pd.DataFrame, current_bar: BarData) -> Tuple[MarketStructure, float]:
        """简单的价格趋势分析（当数据不足20根时使用）"""
        if len(bars) < 5:
            return MarketStructure.TRADING_RANGE, 0.0

        # 如果有足够数据，尝试计算EMA10作为简化版本
        closes = bars['close']
        current_price = current_bar.close

        if len(bars) >= 10:
            # 使用EMA10
            ema = closes.ewm(span=10).mean()
            current_ema = ema.iloc[-1]
        else:
            # 使用简单移动平均
            current_ema = closes.mean()

        # 计算趋势强度
        price_deviation = abs(current_price - current_ema) / current_ema if current_ema > 0 else 0.0
        trend_strength = min(price_deviation * 10, 1.0)

        # 简单判断：价格相对于均线的位置
        if current_price > current_ema * 1.002:  # 0.2%以上
            return MarketStructure.WEAK_TREND_UP, trend_strength
        elif current_price < current_ema * 0.998:  # 0.2%以下
            return MarketStructure.WEAK_TREND_DOWN, trend_strength
        else:
            return MarketStructure.TRADING_RANGE, trend_strength