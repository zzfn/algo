import pandas as pd
import talib
from loguru import logger

def _add_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """辅助函数，用于添加K线形态列。"""
    logger.debug("Identifying candlestick patterns...")
    
    df['pattern'] = None # 默认为无特定形态

    # 内包K线 (Inside Bar)
    inside_bar = (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1))
    df.loc[inside_bar, 'pattern'] = 'inside_bar'
    
    # 看涨吞没 (Bullish Engulfing)
    bullish_engulfing = (
        (df['close'] > df['open']) &
        (df['close'].shift(1) < df['open'].shift(1)) & # 前一根是阴线
        (df['close'] > df['open'].shift(1)) &
        (df['open'] < df['close'].shift(1))
    )
    df.loc[bullish_engulfing, 'pattern'] = 'bullish_engulfing'
    
    # 看跌吞没 (Bearish Engulfing)
    bearish_engulfing = (
        (df['close'] < df['open']) &
        (df['close'].shift(1) > df['open'].shift(1)) & # 前一根是阳线
        (df['close'] < df['open'].shift(1)) &
        (df['open'] > df['close'].shift(1))
    )
    df.loc[bearish_engulfing, 'pattern'] = 'bearish_engulfing'
    
    return df

def analyze_price_action(df: pd.DataFrame) -> pd.DataFrame:
    """
    价格行为分析主函数。
    为输入的DataFrame添加分析列。
    """
    logger.info("Starting price action analysis...")
    analysis_df = df.copy()

    # 1. 计算EMA
    logger.debug("Calculating EMA(20)...")
    analysis_df['ema_20'] = talib.EMA(analysis_df['close'], timeperiod=20)

    # 2. 添加K线形态
    analysis_df = _add_patterns(analysis_df)

    # 3. 判断市场状态
    logger.debug("Determining market state...")
    n_bars_for_trend = 10
    above_ema = (analysis_df['close'] > analysis_df['ema_20']).astype(int).rolling(window=n_bars_for_trend).sum() == n_bars_for_trend
    below_ema = (analysis_df['close'] < analysis_df['ema_20']).astype(int).rolling(window=n_bars_for_trend).sum() == n_bars_for_trend
    
    analysis_df['market_state'] = 'range'
    analysis_df.loc[above_ema, 'market_state'] = 'uptrend'
    analysis_df.loc[below_ema, 'market_state'] = 'downtrend'

    # 4. 寻找交易信号
    logger.debug("Finding trading signals...")
    analysis_df['signal'] = None

    # 新的买入信号: 在上升趋势中，回调至EMA并形成看涨吞没形态
    buy_conditions = (
        (analysis_df['market_state'] == 'uptrend') &
        (analysis_df['low'] <= analysis_df['ema_20']) &
        (analysis_df['pattern'] == 'bullish_engulfing')
    )
    analysis_df.loc[buy_conditions, 'signal'] = 'buy_bullish_engulfing_pullback'
    
    logger.success("Price action analysis complete.")
    return analysis_df