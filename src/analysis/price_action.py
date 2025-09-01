import pandas as pd
import talib
from loguru import logger
from scipy.signal import find_peaks

def _add_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """辅助函数，用于添加K线形态列。"""
    logger.debug("Identifying candlestick patterns...")
    
    df['pattern'] = None

    inside_bar = (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1))
    df.loc[inside_bar, 'pattern'] = 'inside_bar'
    
    bullish_engulfing = (
        (df['close'] > df['open']) &
        (df['close'].shift(1) < df['open'].shift(1)) &
        (df['close'] > df['open'].shift(1)) &
        (df['open'] < df['close'].shift(1))
    )
    df.loc[bullish_engulfing, 'pattern'] = 'bullish_engulfing'
    
    bearish_engulfing = (
        (df['close'] < df['open']) &
        (df['close'].shift(1) > df['open'].shift(1)) &
        (df['close'] < df['open'].shift(1)) &
        (df['open'] > df['close'].shift(1))
    )
    df.loc[bearish_engulfing, 'pattern'] = 'bearish_engulfing'
    
    return df

def _add_swing_points(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """使用 scipy.signal.find_peaks 寻找波段高低点。"""
    logger.debug(f"Identifying swing points with lookback={lookback}...")
    
    high_peaks_indices, _ = find_peaks(df['high'], distance=lookback)
    low_peaks_indices, _ = find_peaks(-df['low'], distance=lookback)
    
    df['is_swing_high'] = False
    df.iloc[high_peaks_indices, df.columns.get_loc('is_swing_high')] = True
    
    df['is_swing_low'] = False
    df.iloc[low_peaks_indices, df.columns.get_loc('is_swing_low')] = True
    
    return df

def analyze_price_action(df: pd.DataFrame) -> pd.DataFrame:
    """
    价格行为分析主函数。
    """
    logger.info("Starting price action analysis...")
    analysis_df = df.copy()

    # 1. 计算EMA
    analysis_df['ema_20'] = talib.EMA(analysis_df['close'], timeperiod=20)

    # 2. 添加K线形态
    analysis_df = _add_patterns(analysis_df)
    
    # 3. 添加波段高低点
    analysis_df = _add_swing_points(analysis_df)

    # 4. 判断市场状态
    logger.debug("Determining market state...")
    n_bars_for_trend = 10
    above_ema = (analysis_df['close'] > analysis_df['ema_20']).astype(int).rolling(window=n_bars_for_trend).sum() == n_bars_for_trend
    below_ema = (analysis_df['close'] < analysis_df['ema_20']).astype(int).rolling(window=n_bars_for_trend).sum() == n_bars_for_trend
    
    analysis_df['market_state'] = 'range'
    analysis_df.loc[above_ema, 'market_state'] = 'uptrend'
    analysis_df.loc[below_ema, 'market_state'] = 'downtrend'

    # 5. 寻找交易信号
    logger.debug("Finding trading signals...")
    analysis_df['signal'] = None

    buy_conditions = (
        (analysis_df['market_state'] == 'uptrend') &
        (analysis_df['low'] <= analysis_df['ema_20']) &
        (analysis_df['pattern'] == 'bullish_engulfing')
    )
    analysis_df.loc[buy_conditions, 'signal'] = 'buy_bullish_engulfing_pullback'
    
    logger.success("Price action analysis complete.")
    return analysis_df
