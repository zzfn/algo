"""
市场数据相关类型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum


@dataclass(frozen=True)
class MarketData:
    """市场数据基类"""
    symbol: str
    timestamp: datetime


@dataclass(frozen=True)
class BarData(MarketData):
    """K线数据"""
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    trade_count: Optional[int] = None


class DataEventType(Enum):
    TRADE = "trade"
    BAR = "bar"
    ERROR = "error"


@dataclass(frozen=True)
class DataEvent:
    """数据事件"""
    event_type: DataEventType
    symbol: str
    data: Any  # TRADE 为 float 价格，BAR 为 BarData
    timestamp: datetime = field(default_factory=datetime.now)