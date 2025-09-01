import os
from datetime import datetime
from typing import List

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# 简单的映射，将字符串转换为Alpaca的TimeFrame对象
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

    Args:
        symbols: 交易品种的列表, e.g., ["SPY", "QQQ"].
        start_date: 数据开始时间 (timezone-aware).
        end_date: 数据结束时间 (timezone-aware).
        timeframe_str: K线周期字符串, e.g., "1Day", "1Hour".

    Returns:
        一个字典，键是交易品种，值是对应的、符合我们标准的DataFrame。
        如果某个品种没有数据，则不会出现在字典中。
    """
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        raise ValueError("API keys not found. Please set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables.")

    client = StockHistoricalDataClient(api_key, secret_key)

    if timeframe_str not in TIMEFRAME_MAP:
        raise ValueError(f"Timeframe '{timeframe_str}' is not supported. Supported values are: {list(TIMEFRAME_MAP.keys())}")

    request_params = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TIMEFRAME_MAP[timeframe_str],
        start=start_date,
        end=end_date,
    )

    bars = client.get_stock_bars(request_params)

    # Alpaca-py v2返回一个按品种分组的字典
    dataframes = bars.df.reset_index()
    dataframes['timestamp'] = pd.to_datetime(dataframes['timestamp'])
    
    # 按我们的标准格式化DataFrame
    formatted_dfs = {}
    for symbol in symbols:
        symbol_df = dataframes[dataframes['symbol'] == symbol].copy()
        if not symbol_df.empty:
            symbol_df.set_index('timestamp', inplace=True)
            # 确保列名符合标准
            symbol_df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True)
            # 只保留标准列
            formatted_dfs[symbol] = symbol_df[['open', 'high', 'low', 'close', 'volume']]

    return formatted_dfs


if __name__ == '__main__':
    # 这是一个使用示例，需要您在.env文件中设置好API密钥
    # 运行 `pip install python-dotenv` 来加载.env文件
    from dotenv import load_dotenv
    from pytz import timezone

    load_dotenv()

    # --- 参数设置 ---
    symbols_to_load = ["SPY", "AAPL"]
    tz = timezone("America/New_York")
    start = tz.localize(datetime(2024, 1, 1))
    end = tz.localize(datetime(2024, 1, 31))
    timeframe = "1Day"
    # ----------------

    print(f"Loading {timeframe} data for {symbols_to_load} from {start.date()} to {end.date()}...")
    
    try:
        all_data = load_historical_data(symbols_to_load, start, end, timeframe)

        for symbol, df in all_data.items():
            print(f"\n--- Data for {symbol} ---")
            if df.empty:
                print("No data returned.")
            else:
                print("Data loaded successfully.")
                print("Shape:", df.shape)
                print("Head:")
                print(df.head(3))
                print("\nTail:")
                print(df.tail(3))

    except (ValueError, Exception) as e:
        print(f"An error occurred: {e}")
