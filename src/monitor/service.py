"""
监控服务 - 收集和提供系统监控数据
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

from .data import (
    MonitorSnapshot, SymbolStatus, SignalHistory,
    PerformanceMetrics, SystemHealth, SystemStatus
)
from utils.log import setup_logging
from utils.events import event_bus, EventTypes, Event

log = setup_logging()

class MonitorService:
    """监控服务 - 单例模式收集系统数据"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.start_time = datetime.now()
        self.system_status = SystemStatus.STARTING

        # 数据存储
        self.symbol_status: Dict[str, SymbolStatus] = {}
        self.signal_history: deque = deque(maxlen=1000)  # 最近1000个信号
        self.daily_signals = 0
        self.active_positions = 0
        self.daily_pnl = 0.0

        # 连接状态
        self.data_feed_connected = False
        self.trading_api_connected = False

        # 错误计数
        self.error_count_today = 0
        self.warning_count_today = 0

        # 性能指标
        self.performance_metrics = PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            daily_returns=[]
        )

        # 订阅事件
        self._setup_event_subscriptions()

        log.info("[MONITOR] 监控服务已初始化")

    def _setup_event_subscriptions(self):
        """设置事件订阅"""
        # 订阅市场分析更新事件
        event_bus.subscribe(EventTypes.MARKET_ANALYSIS_UPDATED, self._handle_market_analysis_event)

        # 订阅信号生成事件
        event_bus.subscribe(EventTypes.SIGNAL_GENERATED, self._handle_signal_event)

        log.debug("[MONITOR] 事件订阅已设置")

    def _handle_market_analysis_event(self, event: Event):
        """处理市场分析更新事件"""
        try:
            data = event.data
            self.update_symbol_status(
                symbol=data['symbol'],
                current_price=data.get('current_price'),
                trend=data.get('trend'),
                volatility=data.get('volatility'),
                volume_profile=data.get('volume_profile'),
                position_size=data.get('position_size')
            )
            log.debug(f"[MONITOR] 处理市场分析事件: {data['symbol']}")
        except Exception as e:
            log.error(f"[MONITOR] 处理市场分析事件失败: {e}")

    def _handle_signal_event(self, event: Event):
        """处理信号生成事件"""
        try:
            data = event.data
            self.add_signal(
                symbol=data['symbol'],
                signal_type=data['signal_type'],
                price=data['price'],
                confidence=data['confidence'],
                reason=data['reason'],
                executed=data.get('executed', False)
            )
            log.debug(f"[MONITOR] 处理信号事件: {data['symbol']} {data['signal_type']}")
        except Exception as e:
            log.error(f"[MONITOR] 处理信号事件失败: {e}")

    def set_system_status(self, status: SystemStatus):
        """设置系统状态"""
        self.system_status = status
        log.info(f"[MONITOR] 系统状态更新: {status.value}")

    def update_symbol_status(self, symbol: str,
                           current_price: Optional[float] = None,
                           price_change: Optional[float] = None,
                           price_change_pct: Optional[float] = None,
                           trend: Optional[str] = None,
                           volatility: Optional[float] = None,
                           volume_profile: Optional[str] = None,
                           position_size: Optional[float] = None,
                           unrealized_pnl: Optional[float] = None):
        """更新股票状态"""
        if symbol not in self.symbol_status:
            self.symbol_status[symbol] = SymbolStatus(
                symbol=symbol,
                current_price=None,
                price_change=None,
                price_change_pct=None,
                trend="UNKNOWN",
                volatility=0.0,
                volume_profile="UNKNOWN",
                last_signal_type=None,
                last_signal_time=None,
                last_signal_price=None,
                last_signal_confidence=None,
                position_size=0.0,
                unrealized_pnl=0.0,
                bars_received_today=0,
                last_bar_time=None
            )

        status = self.symbol_status[symbol]
        if current_price is not None:
            status.current_price = current_price
        if price_change is not None:
            status.price_change = price_change
        if price_change_pct is not None:
            status.price_change_pct = price_change_pct
        if trend is not None:
            status.trend = trend
        if volatility is not None:
            status.volatility = volatility
        if volume_profile is not None:
            status.volume_profile = volume_profile
        if position_size is not None:
            status.position_size = position_size
        if unrealized_pnl is not None:
            status.unrealized_pnl = unrealized_pnl

    def add_signal(self, symbol: str, signal_type: str, price: float,
                  confidence: float, reason: str, executed: bool = False):
        """添加交易信号"""
        signal = SignalHistory(
            timestamp=datetime.now(),
            symbol=symbol,
            signal_type=signal_type,
            price=price,
            confidence=confidence,
            reason=reason,
            executed=executed
        )

        self.signal_history.append(signal)
        self.daily_signals += 1

        # 更新股票的最新信号
        if symbol in self.symbol_status:
            status = self.symbol_status[symbol]
            status.last_signal_type = signal_type
            status.last_signal_time = signal.timestamp
            status.last_signal_price = price
            status.last_signal_confidence = confidence

        log.info(f"[MONITOR] 记录信号: {symbol} {signal_type} @{price}")

    def update_bar_received(self, symbol: str):
        """更新K线接收计数"""
        if symbol in self.symbol_status:
            self.symbol_status[symbol].bars_received_today += 1
            self.symbol_status[symbol].last_bar_time = datetime.now()

    def set_connection_status(self, data_feed: bool = None, trading_api: bool = None):
        """设置连接状态"""
        if data_feed is not None:
            self.data_feed_connected = data_feed
        if trading_api is not None:
            self.trading_api_connected = trading_api

    def increment_error_count(self):
        """增加错误计数"""
        self.error_count_today += 1

    def increment_warning_count(self):
        """增加警告计数"""
        self.warning_count_today += 1

    def get_snapshot(self) -> MonitorSnapshot:
        """获取当前监控快照"""
        # 计算系统运行时间
        uptime = int((datetime.now() - self.start_time).total_seconds())

        # 获取系统资源使用情况
        cpu_usage = psutil.cpu_percent(interval=None)
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent

        # 计算活跃持仓数
        active_positions = sum(1 for status in self.symbol_status.values()
                             if status.position_size != 0)

        # 计算今日PnL
        daily_pnl = sum(status.unrealized_pnl for status in self.symbol_status.values())

        return MonitorSnapshot(
            timestamp=datetime.now(),
            system_status=self.system_status,
            symbols=self.symbol_status.copy(),
            total_signals=self.daily_signals,
            active_positions=active_positions,
            daily_pnl=daily_pnl,
            data_feed_connected=self.data_feed_connected,
            trading_api_connected=self.trading_api_connected,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            uptime_seconds=uptime
        )

    def get_recent_signals(self, limit: int = 50) -> List[SignalHistory]:
        """获取最近的信号历史"""
        return list(self.signal_history)[-limit:]

    def get_system_health(self) -> SystemHealth:
        """获取系统健康状况"""
        # 检查最后数据时间
        last_data_time = None
        if self.symbol_status:
            last_times = [s.last_bar_time for s in self.symbol_status.values()
                         if s.last_bar_time is not None]
            if last_times:
                last_data_time = max(last_times)

        # 判断数据流是否健康（5分钟内有数据）
        data_stream_healthy = False
        if last_data_time:
            data_stream_healthy = (datetime.now() - last_data_time) < timedelta(minutes=5)

        # 获取系统资源
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')

        return SystemHealth(
            data_stream_healthy=data_stream_healthy,
            last_data_time=last_data_time,
            connection_errors=0,  # TODO: 实现连接错误计数
            memory_usage_mb=memory_info.used / 1024 / 1024,
            cpu_usage_pct=psutil.cpu_percent(interval=None),
            disk_usage_pct=disk_info.percent,
            error_count_today=self.error_count_today,
            warning_count_today=self.warning_count_today
        )

    def reset_daily_counters(self):
        """重置每日计数器（可在每日开始时调用）"""
        self.daily_signals = 0
        self.error_count_today = 0
        self.warning_count_today = 0
        for status in self.symbol_status.values():
            status.bars_received_today = 0

        log.info("[MONITOR] 每日计数器已重置")

# 全局监控实例
monitor = MonitorService()