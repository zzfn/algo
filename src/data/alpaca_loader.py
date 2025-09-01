import os
from datetime import datetime
from typing import List

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from loguru import logger

TIMEFRAME_MAP = {
    "1Min": TimeFrame(1, TimeFrameUnit.Minute),
    "5Min": TimeFrame(5, TimeFrameUnit.Minute),
    "15Min": TimeFrame(15, TimeFrameUnit.Minute),
    "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
    "1Day": TimeFrame(1, TimeFrameUnit.Day),
}

def load_historical_data(
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    timeframe_str: str = "1Day",
) -> dict[str, pd.DataFrame]:
    """
    从Alpaca加载一个或多个交易品种的历史K线数据。
    """
    logger.info(f"Attempting to load data for symbols: {symbols}")
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        logger.error("API keys not found. Please set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables.")
        raise ValueError("API keys not found in environment variables.")

    client = StockHistoricalDataClient(api_key, secret_key)

    if timeframe_str not in TIMEFRAME_MAP:
        logger.error(f"Timeframe '{timeframe_str}' is not supported.")
        raise ValueError(f"Timeframe '{timeframe_str}' is not supported.")

    request_params = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TIMEFRAME_MAP[timeframe_str],
        start=start_date,
        end=end_date,
        feed="iex",
    )

    logger.debug(f"Requesting bars from Alpaca with params: {request_params}")
    bars = client.get_stock_bars(request_params)

    # Alpaca apy-py returns a multi-index DataFrame with timezone-aware index
    all_data = bars.df

    formatted_dfs = {}
    for symbol in symbols:
        # Select data for the specific symbol
        symbol_df = all_data.loc[symbol].copy()
        if not symbol_df.empty:
            # The index is already a timezone-aware DatetimeIndex.
            # We just need to ensure the column names are what we expect.
            symbol_df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True)
            formatted_dfs[symbol] = symbol_df[['open', 'high', 'low', 'close', 'volume']]

    logger.success(f"Successfully formatted data for symbols: {list(formatted_dfs.keys())}")
    return formatted_dfs