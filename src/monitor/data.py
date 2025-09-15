"""
监控数据模型 - 定义监控面板需要的数据结构
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum

class SystemStatus(Enum):
    RUNNING = "运行中"
    STOPPED = "已停止"
    ERROR = "错误"
    STARTING = "启动中"

@dataclass
class MonitorSnapshot:
    """监控快照 - 系统当前状态的完整视图"""
    timestamp: datetime
    system_status: SystemStatus

    # 市场数据
    symbols: Dict[str, 'SymbolStatus']

    # 系统性能
    total_signals: int
    active_positions: int
    daily_pnl: float

    # 连接状态
    data_feed_connected: bool
    trading_api_connected: bool

    # 系统资源
    cpu_usage: float
    memory_usage: float
    uptime_seconds: int

@dataclass
class SymbolStatus:
    """单个股票的状态"""
    symbol: str
    current_price: Optional[float]
    price_change: Optional[float]
    price_change_pct: Optional[float]

    # 市场背景
    trend: str
    volatility: float
    volume_profile: str

    # 最新信号
    last_signal_type: Optional[str]
    last_signal_time: Optional[datetime]
    last_signal_price: Optional[float]
    last_signal_confidence: Optional[float]

    # 交易状态
    position_size: float
    unrealized_pnl: float

    # 数据质量
    bars_received_today: int
    last_bar_time: Optional[datetime]

@dataclass
class SignalHistory:
    """信号历史记录"""
    timestamp: datetime
    symbol: str
    signal_type: str
    price: float
    confidence: float
    reason: str
    executed: bool

@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    sharpe_ratio: float
    max_drawdown: float
    daily_returns: List[float]

@dataclass
class SystemHealth:
    """系统健康状况"""
    data_stream_healthy: bool
    last_data_time: Optional[datetime]
    connection_errors: int
    memory_usage_mb: float
    cpu_usage_pct: float
    disk_usage_pct: float
    error_count_today: int
    warning_count_today: int