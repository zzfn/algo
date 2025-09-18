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
    TWO_LEG_PULLBACK = "two_leg_pullback"    # 二腿修正
    WEDGE_PATTERN = "wedge_pattern"          # 楔形模式
    TEST_PATTERN = "test_pattern"            # 测试模式


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
    two_leg_pullback: Optional[Dict[str, Any]]  # 二腿修正信息
    wedge_pattern: Optional[Dict[str, Any]]     # 楔形模式信息
    test_pattern: Optional[Dict[str, Any]]      # 测试模式信息
    trendline_break: Optional[Dict[str, Any]]   # 趋势线突破信息
    failed_breakout: Optional[Dict[str, Any]]   # 假突破信息


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

        # 分析Al Brooks高级模式
        two_leg_pullback = PriceActionAnalyzer._analyze_two_leg_pullback(bars, current_bar)
        wedge_pattern = PriceActionAnalyzer._analyze_wedge_pattern(bars, current_bar)
        test_pattern = PriceActionAnalyzer._analyze_test_pattern(bars, current_bar)
        trendline_break = PriceActionAnalyzer._analyze_trendline_break(bars, current_bar)
        failed_breakout = PriceActionAnalyzer._analyze_failed_breakout(bars, current_bar)

        return PriceActionContext(
            symbol=current_bar.symbol,
            current_price=current_bar.close,
            bar_quality=bar_quality,
            market_structure=market_structure,
            trend_strength=trend_strength,
            at_key_level=at_key_level,
            key_level_type=key_level_type,
            consecutive_pattern=consecutive_pattern,
            two_leg_pullback=two_leg_pullback,
            wedge_pattern=wedge_pattern,
            test_pattern=test_pattern,
            trendline_break=trendline_break,
            failed_breakout=failed_breakout
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
    def pattern_recognition(bars: pd.DataFrame, context: MarketContext, current_bar: BarData) -> Dict[str, Any]:
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

        # Al Brooks反转模式：基于K线质量和价格行为背景
        price_action_context = PriceActionAnalyzer.analyze_market_context(bars, current_bar)

        # 基本反转信号：基于K线质量
        if price_action_context.bar_quality == BarQuality.REVERSAL:
            patterns['reversal'] = {
                'bullish_reversal': (price_action_context.market_structure in
                                   [MarketStructure.STRONG_TREND_DOWN, MarketStructure.WEAK_TREND_DOWN]),
                'bearish_reversal': (price_action_context.market_structure in
                                   [MarketStructure.STRONG_TREND_UP, MarketStructure.WEAK_TREND_UP])
            }

        # Al Brooks高级模式
        # 二腿修正模式
        if price_action_context.two_leg_pullback:
            patterns['two_leg_pullback'] = price_action_context.two_leg_pullback

        # 楔形模式
        if price_action_context.wedge_pattern:
            patterns['wedge'] = price_action_context.wedge_pattern

        # 测试模式
        if price_action_context.test_pattern:
            patterns['test'] = price_action_context.test_pattern

        # 趋势线突破
        if price_action_context.trendline_break:
            patterns['trendline_break'] = price_action_context.trendline_break

        # 假突破模式
        if price_action_context.failed_breakout:
            patterns['failed_breakout'] = price_action_context.failed_breakout

        return patterns

    @staticmethod
    def signal_generation(bars: pd.DataFrame, bar: BarData) -> Tuple[Optional[TradingSignal], MarketContext]:
        """纯函数：集成市场分析、模式识别和信号生成，返回信号和市场分析结果"""
        # 1. 市场分析
        context = PriceActionAnalyzer.market_analysis(bars, bar)

        # 2. 模式识别
        patterns = PriceActionAnalyzer.pattern_recognition(bars, context, bar)

        # 3. 基于模式和市场背景生成信号
        if 'breakout' in patterns:
            breakout = patterns['breakout']

            # 上涨突破信号 - Al Brooks: 专注价格行为，不依赖成交量
            if (breakout['high_break'] and
                context.trend in ["UPTREND", "SIDEWAYS"]):

                confidence = 0.8 if context.trend == "UPTREND" else 0.6
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="BUY",
                    confidence=confidence,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="向上突破 + 上升趋势"
                ), context

            # 下跌突破信号 - Al Brooks: 专注价格行为，不依赖成交量
            if (breakout['low_break'] and
                context.trend in ["DOWNTREND", "SIDEWAYS"]):

                confidence = 0.8 if context.trend == "DOWNTREND" else 0.6
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="SELL",
                    confidence=confidence,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="向下突破 + 下降趋势"
                ), context

        # Al Brooks高级模式信号
        # 二腿修正信号
        if 'two_leg_pullback' in patterns:
            pullback = patterns['two_leg_pullback']
            if pullback['type'] == 'bullish_two_leg' and pullback['strength'] > 0.3:
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="BUY",
                    confidence=0.75,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="二腿修正后看涨信号"
                ), context
            elif pullback['type'] == 'bearish_two_leg' and pullback['strength'] > 0.3:
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="SELL",
                    confidence=0.75,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="二腿修正后看跌信号"
                ), context

        # 楔形突破信号
        if 'wedge' in patterns:
            wedge = patterns['wedge']
            if wedge['type'] == 'converging_wedge':
                # 收敛楔形突破通常延续原趋势
                if context.trend == "UPTREND":
                    return TradingSignal(
                        symbol=bar.symbol,
                        signal_type="BUY",
                        confidence=0.7,
                        price=bar.close,
                        timestamp=bar.timestamp,
                        reason="收敛楔形向上突破"
                    ), context
                elif context.trend == "DOWNTREND":
                    return TradingSignal(
                        symbol=bar.symbol,
                        signal_type="SELL",
                        confidence=0.7,
                        price=bar.close,
                        timestamp=bar.timestamp,
                        reason="收敛楔形向下突破"
                    ), context

        # 趋势线突破信号
        if 'trendline_break' in patterns:
            trendline = patterns['trendline_break']
            if trendline['signal'] == 'bullish' and trendline['break_strength'] > 0.01:
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="BUY",
                    confidence=0.65,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="向上突破下降趋势线"
                ), context
            elif trendline['signal'] == 'bearish' and trendline['break_strength'] > 0.01:
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="SELL",
                    confidence=0.65,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="向下突破上升趋势线"
                ), context

        # 假突破反转信号
        if 'failed_breakout' in patterns:
            failed = patterns['failed_breakout']
            if failed['signal'] == 'bullish_reversal':
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="BUY",
                    confidence=0.8,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="假突破后看涨反转"
                ), context
            elif failed['signal'] == 'bearish_reversal':
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="SELL",
                    confidence=0.8,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="假突破后看跌反转"
                ), context

        # 测试模式信号（支撑阻力位测试）
        if 'test' in patterns:
            test = patterns['test']
            if test['type'] == 'support_test' and test['test_quality'] == 'strong':
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="BUY",
                    confidence=0.6,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="强支撑位测试反弹"
                ), context
            elif test['type'] == 'resistance_test' and test['test_quality'] == 'strong':
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="SELL",
                    confidence=0.6,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="强阻力位测试回落"
                ), context

        # 基本反转信号（只在强趋势中考虑）
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
                ), context

            if reversal.get('bearish_reversal', False):
                return TradingSignal(
                    symbol=bar.symbol,
                    signal_type="SELL",
                    confidence=0.7,
                    price=bar.close,
                    timestamp=bar.timestamp,
                    reason="强势看跌反转模式"
                ), context

        return None, context

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

    # Al Brooks高级模式识别方法
    @staticmethod
    def _analyze_two_leg_pullback(bars: pd.DataFrame, current_bar: BarData) -> Optional[Dict[str, Any]]:
        """分析二腿修正模式 - Al Brooks核心概念"""
        if len(bars) < 10:
            return None

        highs = bars['high'].values
        lows = bars['low'].values
        closes = bars['close'].values

        # 寻找最近的重要高低点
        recent_highs = PriceActionAnalyzer._find_local_peaks(highs[-15:], window=2)
        recent_lows = PriceActionAnalyzer._find_local_valleys(lows[-15:], window=2)

        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        current_price = current_bar.close

        # 检测上升趋势中的二腿回调
        if len(recent_lows) >= 2:
            # 两个连续的低点，第二个低点高于第一个低点（高低点）
            if recent_lows[-1] > recent_lows[-2]:
                # 检查当前价格是否从第二个低点开始反弹
                if current_price > recent_lows[-1] * 1.005:  # 0.5%的反弹确认
                    return {
                        'type': 'bullish_two_leg',
                        'first_low': recent_lows[-2],
                        'second_low': recent_lows[-1],
                        'current_price': current_price,
                        'strength': min((current_price - recent_lows[-1]) / recent_lows[-1] * 100, 1.0)
                    }

        # 检测下降趋势中的二腿回调
        if len(recent_highs) >= 2:
            # 两个连续的高点，第二个高点低于第一个高点（低高点）
            if recent_highs[-1] < recent_highs[-2]:
                # 检查当前价格是否从第二个高点开始下跌
                if current_price < recent_highs[-1] * 0.995:  # 0.5%的下跌确认
                    return {
                        'type': 'bearish_two_leg',
                        'first_high': recent_highs[-2],
                        'second_high': recent_highs[-1],
                        'current_price': current_price,
                        'strength': min((recent_highs[-1] - current_price) / recent_highs[-1] * 100, 1.0)
                    }

        return None

    @staticmethod
    def _analyze_wedge_pattern(bars: pd.DataFrame, current_bar: BarData) -> Optional[Dict[str, Any]]:
        """分析楔形模式 - 收敛楔形和发散楔形"""
        if len(bars) < 15:
            return None

        highs = bars['high'].values[-15:]
        lows = bars['low'].values[-15:]

        # 寻找高点和低点序列
        high_peaks = PriceActionAnalyzer._find_local_peaks(highs, window=2)
        low_valleys = PriceActionAnalyzer._find_local_valleys(lows, window=2)

        if len(high_peaks) < 3 or len(low_valleys) < 3:
            return None

        # 计算高点趋势线斜率
        high_slope = (high_peaks[-1] - high_peaks[-3]) / 2 if len(high_peaks) >= 3 else 0
        # 计算低点趋势线斜率
        low_slope = (low_valleys[-1] - low_valleys[-3]) / 2 if len(low_valleys) >= 3 else 0

        # 收敛楔形：高点下降，低点上升
        if high_slope < 0 and low_slope > 0:
            convergence_ratio = abs(high_slope) + abs(low_slope)
            if convergence_ratio > (highs.max() - lows.min()) * 0.01:  # 1%的收敛率
                return {
                    'type': 'converging_wedge',
                    'high_slope': high_slope,
                    'low_slope': low_slope,
                    'convergence_strength': convergence_ratio,
                    'breakout_direction': 'pending'
                }

        # 发散楔形：高点上升加速，低点下降加速
        if high_slope > 0 and low_slope < 0:
            divergence_ratio = abs(high_slope) + abs(low_slope)
            if divergence_ratio > (highs.max() - lows.min()) * 0.015:  # 1.5%的发散率
                return {
                    'type': 'diverging_wedge',
                    'high_slope': high_slope,
                    'low_slope': low_slope,
                    'divergence_strength': divergence_ratio,
                    'reversal_potential': 'high'
                }

        return None

    @staticmethod
    def _analyze_test_pattern(bars: pd.DataFrame, current_bar: BarData) -> Optional[Dict[str, Any]]:
        """分析测试模式 - 测试前期高点或低点"""
        if len(bars) < 10:
            return None

        current_price = current_bar.close
        highs = bars['high'].values
        lows = bars['low'].values

        # 寻找重要的支撑阻力位
        recent_highs = PriceActionAnalyzer._find_local_peaks(highs[-20:], window=3)
        recent_lows = PriceActionAnalyzer._find_local_valleys(lows[-20:], window=3)

        test_tolerance = (highs.max() - lows.min()) * 0.003  # 0.3%的测试容差

        # 测试前期高点（阻力位）
        for i, high in enumerate(recent_highs):
            if abs(current_price - high) <= test_tolerance:
                # 检查是否是第二次或多次测试
                test_count = sum(1 for h in recent_highs if abs(h - high) <= test_tolerance)
                if test_count >= 2:
                    return {
                        'type': 'resistance_test',
                        'test_level': high,
                        'current_price': current_price,
                        'test_count': test_count,
                        'test_quality': 'strong' if test_count >= 3 else 'moderate'
                    }

        # 测试前期低点（支撑位）
        for i, low in enumerate(recent_lows):
            if abs(current_price - low) <= test_tolerance:
                # 检查是否是第二次或多次测试
                test_count = sum(1 for l in recent_lows if abs(l - low) <= test_tolerance)
                if test_count >= 2:
                    return {
                        'type': 'support_test',
                        'test_level': low,
                        'current_price': current_price,
                        'test_count': test_count,
                        'test_quality': 'strong' if test_count >= 3 else 'moderate'
                    }

        return None

    @staticmethod
    def _analyze_trendline_break(bars: pd.DataFrame, current_bar: BarData) -> Optional[Dict[str, Any]]:
        """分析微趋势线突破"""
        if len(bars) < 10:
            return None

        highs = bars['high'].values[-10:]
        lows = bars['low'].values[-10:]
        current_price = current_bar.close

        # 分析上升趋势线（连接低点）
        low_points = PriceActionAnalyzer._find_local_valleys(lows, window=1)
        if len(low_points) >= 2:
            # 计算趋势线
            trendline_slope = (low_points[-1] - low_points[-2]) / (len(low_points) - 1)
            projected_trendline = low_points[-1] + trendline_slope

            # 检查是否跌破上升趋势线
            if current_price < projected_trendline * 0.995:  # 0.5%的突破确认
                return {
                    'type': 'uptrend_break',
                    'trendline_value': projected_trendline,
                    'current_price': current_price,
                    'break_strength': (projected_trendline - current_price) / projected_trendline,
                    'signal': 'bearish'
                }

        # 分析下降趋势线（连接高点）
        high_points = PriceActionAnalyzer._find_local_peaks(highs, window=1)
        if len(high_points) >= 2:
            # 计算趋势线
            trendline_slope = (high_points[-1] - high_points[-2]) / (len(high_points) - 1)
            projected_trendline = high_points[-1] + trendline_slope

            # 检查是否突破下降趋势线
            if current_price > projected_trendline * 1.005:  # 0.5%的突破确认
                return {
                    'type': 'downtrend_break',
                    'trendline_value': projected_trendline,
                    'current_price': current_price,
                    'break_strength': (current_price - projected_trendline) / projected_trendline,
                    'signal': 'bullish'
                }

        return None

    @staticmethod
    def _analyze_failed_breakout(bars: pd.DataFrame, current_bar: BarData) -> Optional[Dict[str, Any]]:
        """分析假突破模式 - Al Brooks重要概念"""
        if len(bars) < 15:
            return None

        current_price = current_bar.close
        highs = bars['high'].values
        lows = bars['low'].values

        # 寻找最近的重要支撑阻力位
        recent_highs = PriceActionAnalyzer._find_local_peaks(highs[-15:], window=2)
        recent_lows = PriceActionAnalyzer._find_local_valleys(lows[-15:], window=2)

        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        # 检测向上假突破
        for high in recent_highs:
            # 检查是否有突破后快速回落的情况
            bars_since_high = 0
            max_penetration = 0
            for i in range(len(bars) - 5, len(bars)):
                if i >= 0 and i < len(bars):
                    bar_high = highs[i] if i < len(highs) else current_bar.high
                    if bar_high > high:
                        penetration = (bar_high - high) / high
                        max_penetration = max(max_penetration, penetration)
                        bars_since_high = len(bars) - i

            # 假突破条件：突破幅度小于2%，且在3根K线内回落到突破位以下
            if (max_penetration > 0.001 and max_penetration < 0.02 and
                bars_since_high <= 3 and current_price < high * 0.998):
                return {
                    'type': 'failed_upward_breakout',
                    'resistance_level': high,
                    'max_penetration': max_penetration,
                    'current_price': current_price,
                    'bars_since_break': bars_since_high,
                    'signal': 'bearish_reversal'
                }

        # 检测向下假突破
        for low in recent_lows:
            # 检查是否有跌破后快速反弹的情况
            bars_since_low = 0
            max_penetration = 0
            for i in range(len(bars) - 5, len(bars)):
                if i >= 0 and i < len(bars):
                    bar_low = lows[i] if i < len(lows) else current_bar.low
                    if bar_low < low:
                        penetration = (low - bar_low) / low
                        max_penetration = max(max_penetration, penetration)
                        bars_since_low = len(bars) - i

            # 假突破条件：跌破幅度小于2%，且在3根K线内反弹到突破位以上
            if (max_penetration > 0.001 and max_penetration < 0.02 and
                bars_since_low <= 3 and current_price > low * 1.002):
                return {
                    'type': 'failed_downward_breakout',
                    'support_level': low,
                    'max_penetration': max_penetration,
                    'current_price': current_price,
                    'bars_since_break': bars_since_low,
                    'signal': 'bullish_reversal'
                }

        return None

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
        elif market_structure == MarketStructure.TWO_LEG_PULLBACK:
            return "PULLBACK"
        elif market_structure == MarketStructure.WEDGE_PATTERN:
            return "WEDGE"
        elif market_structure == MarketStructure.TEST_PATTERN:
            return "TEST"
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