"""
策略相关数据模型
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TradingSignal:
    """交易信号"""
    symbol: str
    signal_type: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0 to 1.0
    price: float
    timestamp: datetime
    reason: str  # 信号产生的原因


@dataclass(frozen=True)
class MarketContext:
    """市场背景信息"""
    symbol: str
    current_price: float
    trend: str  # "UPTREND", "DOWNTREND", "SIDEWAYS"
    volatility: float
    volume_profile: str  # "HIGH", "NORMAL", "LOW"