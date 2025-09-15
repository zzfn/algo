"""
监控服务 - 收集和提供系统监控数据
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

from .data import (
    MonitorSnapshot, SymbolStatus, SignalHistory,
    PerformanceMetrics, SystemHealth, SystemStatus,
    ActiveStock, MostActives
)
from utils.log import setup_logging
from utils.events import event_bus, EventTypes, Event
from config.config import TradingConfig
from alpaca.data.historical.screener import ScreenerClient
from alpaca.data.requests import MostActivesRequest

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

        # 活跃股票数据
        self.most_actives: Optional[MostActives] = None
        self.last_actives_update: Optional[datetime] = None

        # 连接状态
        self.data_feed_connected = False
        self.trading_api_connected = False

        # 错误计数
        self.error_count_today = 0
        self.warning_count_today = 0

        # 初始化 Screener 客户端
        try:
            config = TradingConfig.create()
            self.screener_client = ScreenerClient(
                api_key=config.api_key,
                secret_key=config.secret_key
            )
            log.info("[MONITOR] ScreenerClient 已初始化")
        except Exception as e:
            log.error(f"[MONITOR] ScreenerClient 初始化失败: {e}")
            self.screener_client = None

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

    def fetch_most_actives(self, force_update: bool = False) -> Optional[MostActives]:
        """获取最活跃股票（带缓存）"""
        # 检查是否需要更新（每10分钟更新一次，除非强制更新）
        if (not force_update and
            self.last_actives_update and
            (datetime.now() - self.last_actives_update).total_seconds() < 600):
            return self.most_actives

        if not self.screener_client:
            log.warning("[MONITOR] ScreenerClient 未初始化，无法获取活跃股票")
            return None

        try:
            # 创建请求参数：按交易次数排序，获取前10名
            request_params = MostActivesRequest(
                by='trades',
                top=10
            )

            # 调用API获取活跃股票
            alpaca_response = self.screener_client.get_most_actives(request_params)

            # 转换为我们的数据模型
            active_stocks = []
            for stock in alpaca_response.most_actives:
                active_stock = ActiveStock(
                    symbol=stock.symbol,
                    volume=stock.volume,
                    trade_count=stock.trade_count
                )
                active_stocks.append(active_stock)

            self.most_actives = MostActives(
                last_updated=alpaca_response.last_updated,
                stocks=active_stocks
            )
            self.last_actives_update = datetime.now()

            log.info(f"[MONITOR] 已更新活跃股票列表，获取到 {len(active_stocks)} 只股票")
            return self.most_actives

        except Exception as e:
            log.error(f"[MONITOR] 获取活跃股票失败: {e}")
            return None

    def get_snapshot(self) -> MonitorSnapshot:
        """获取当前监控快照"""
        # 计算活跃持仓数
        active_positions = sum(1 for status in self.symbol_status.values()
                             if status.position_size != 0)

        # 计算今日PnL
        daily_pnl = sum(status.unrealized_pnl for status in self.symbol_status.values())

        # 获取活跃股票（如果缓存还有效就使用缓存）
        most_actives = self.fetch_most_actives()

        return MonitorSnapshot(
            timestamp=datetime.now(),
            system_status=self.system_status,
            symbols=self.symbol_status.copy(),
            most_actives=most_actives,
            total_signals=self.daily_signals,
            active_positions=active_positions,
            daily_pnl=daily_pnl,
            data_feed_connected=self.data_feed_connected,
            trading_api_connected=self.trading_api_connected,
            cpu_usage=0.0,  # 不再使用，保留为兼容性
            memory_usage=0.0,  # 不再使用，保留为兼容性
            uptime_seconds=0  # 不再使用，保留为兼容性
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

        return SystemHealth(
            data_stream_healthy=data_stream_healthy,
            last_data_time=last_data_time,
            connection_errors=0,  # TODO: 实现连接错误计数
            memory_usage_mb=0.0,  # 不再监控，保留为兼容性
            cpu_usage_pct=0.0,  # 不再监控，保留为兼容性
            disk_usage_pct=0.0,  # 不再监控，保留为兼容性
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