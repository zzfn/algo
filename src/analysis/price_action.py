import pandas as pd
import talib
from loguru import logger

def analyze_price_action(df: pd.DataFrame) -> pd.DataFrame:
    """
    价格行为分析主函数。
    为输入的DataFrame添加分析列。

    Args:
        df: 原始的OHLCV DataFrame，列名需为小写的 open, high, low, close。

    Returns:
        一个添加了 'ema_20', 'market_state', 'signal' 列的DataFrame。
    """
    logger.info("Starting price action analysis using TA-Lib...")
    
    analysis_df = df.copy()

    # 1. 计算EMA (使用小写 'close')
    logger.debug("Calculating EMA(20)...")
    analysis_df['ema_20'] = talib.EMA(analysis_df['close'], timeperiod=20)

    # 2. 判断市场状态 (使用小写 'close')
    logger.debug("Determining market state...")
    n_bars_for_trend = 10
    above_ema = (analysis_df['close'] > analysis_df['ema_20']).astype(int).rolling(window=n_bars_for_trend).sum() == n_bars_for_trend
    below_ema = (analysis_df['close'] < analysis_df['ema_20']).astype(int).rolling(window=n_bars_for_trend).sum() == n_bars_for_trend
    
    analysis_df['market_state'] = 'range'
    analysis_df.loc[above_ema, 'market_state'] = 'uptrend'
    analysis_df.loc[below_ema, 'market_state'] = 'downtrend'

    # 3. 寻找交易信号 (使用小写 'low', 'close', 'open')
    logger.debug("Finding pullback signals...")
    analysis_df['signal'] = None

    buy_conditions = (
        (analysis_df['market_state'] == 'uptrend') &
        (analysis_df['low'] <= analysis_df['ema_20']) &
        (analysis_df['close'] > analysis_df['open'])
    )
    analysis_df.loc[buy_conditions, 'signal'] = 'buy_pullback'
    
    logger.success("Price action analysis complete.")
    return analysis_df
