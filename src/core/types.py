from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass(frozen=True)
class TakeProfitTarget:
    """定义单个分批止盈目标"""
    price: float
    portion: float # 仓位退出的比例, e.g., 0.5 for 50%

@dataclass(frozen=True)
class Signal:
    """定义交易信号的数据结构"""
    symbol: str
    timestamp: datetime
    action: str  # "BUY" or "SELL"
    signal_type: str
    entry_price: float
    stop_loss: float
    take_profit_targets: List[TakeProfitTarget] = field(default_factory=list)
    reason: Optional[str] = None

@dataclass(frozen=True)
class Order:
    """定义订单指令的数据结构"""
    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: float
    order_type: str  # "LIMIT", "MARKET", "STOP"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None # For STOP or STOP_LIMIT orders
    stop_loss_price: Optional[float] = None # For bracket orders

@dataclass(frozen=True)
class Confirmation:
    """定义订单确认的数据结构"""
    order_id: str
    symbol: str
    status: str
    filled_quantity: Optional[float] = None
    filled_avg_price: Optional[float] = None
    timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
