"""
数据转换纯函数
所有的数据格式转换逻辑都应该是纯函数
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
import arrow

from src.models.market_data import BarData


def alpaca_bar_to_bar_data(bar: Any) -> BarData:
    """将 Alpaca Bar 对象转换为 BarData"""
    return BarData(
        symbol=bar.symbol,
        timestamp=bar.timestamp,
        open=float(bar.open),
        high=float(bar.high),
        low=float(bar.low),
        close=float(bar.close),
        volume=int(bar.volume),
        vwap=float(bar.vwap) if bar.vwap else None,
        trade_count=int(bar.trade_count) if bar.trade_count else None
    )


def bars_to_dataframe(bars: List[BarData]) -> pd.DataFrame:
    """将 BarData 列表转换为 pandas DataFrame"""
    if not bars:
        return pd.DataFrame()

    df_data = []
    for bar in bars:
        df_data.append({
            'timestamp': bar.timestamp,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume,
            'vwap': bar.vwap
        })

    df = pd.DataFrame(df_data)
    df.set_index('timestamp', inplace=True)
    return df


def alpaca_bars_to_dataframe(symbol_bars: List[Any]) -> pd.DataFrame:
    """将 Alpaca Bar 对象列表转换为 DataFrame"""
    if not symbol_bars:
        return pd.DataFrame()

    df_data = []
    for bar in symbol_bars:
        df_data.append({
            'timestamp': bar.timestamp,
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': int(bar.volume),
            'vwap': float(bar.vwap) if bar.vwap else None
        })

    df = pd.DataFrame(df_data)
    df.set_index('timestamp', inplace=True)
    return df


def format_timestamp_to_et(timestamp: datetime) -> str:
    """将时间戳格式化为美东时间字符串"""
    return arrow.get(timestamp).to('US/Eastern').format('YYYY-MM-DD HH:mm:ss.SSSSSS')


def get_latest_bars_slice(bars: List[BarData], count: int) -> List[BarData]:
    """获取最近的 N 根 K线"""
    return bars[-count:] if bars else []