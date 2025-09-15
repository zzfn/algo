"""
轻量级事件系统 - 用于解耦组件间的通信
支持同步/异步事件发布，线程安全
"""

import threading
import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from utils.log import setup_logging

log = setup_logging()


@dataclass
class Event:
    """事件数据结构"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime
    source: Optional[str] = None


class EventBus:
    """线程安全的事件总线"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, callback: Callable[[Event], None]):
        """订阅事件类型

        Args:
            event_type: 事件类型名称
            callback: 回调函数，接收 Event 对象
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
            log.debug(f"[EVENT] 订阅事件: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]):
        """取消订阅"""
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    log.debug(f"[EVENT] 取消订阅: {event_type}")
                except ValueError:
                    pass

    def publish(self, event_type: str, data: Dict[str, Any], source: str = None):
        """发布事件（同步）

        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源标识
        """
        event = Event(
            type=event_type,
            data=data,
            timestamp=datetime.now(),
            source=source
        )

        with self._lock:
            subscribers = self._subscribers.get(event_type, []).copy()

        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                log.error(f"[EVENT] 事件处理异常 {event_type}: {e}")

    def publish_async(self, event_type: str, data: Dict[str, Any], source: str = None):
        """发布事件（异步执行回调）"""
        def _async_publish():
            self.publish(event_type, data, source)

        threading.Thread(target=_async_publish, daemon=True).start()

    def get_subscriber_count(self, event_type: str = None) -> int:
        """获取订阅者数量"""
        with self._lock:
            if event_type:
                return len(self._subscribers.get(event_type, []))
            return sum(len(subs) for subs in self._subscribers.values())

    def clear_subscribers(self, event_type: str = None):
        """清除订阅者"""
        with self._lock:
            if event_type:
                self._subscribers.pop(event_type, None)
            else:
                self._subscribers.clear()


# 全局事件总线实例
event_bus = EventBus()


# 便捷装饰器
def on_event(event_type: str, bus: EventBus = None):
    """事件订阅装饰器

    使用示例:
    @on_event('market_update')
    def handle_market_update(event: Event):
        print(f"收到市场更新: {event.data}")
    """
    if bus is None:
        bus = event_bus

    def decorator(func):
        bus.subscribe(event_type, func)
        return func
    return decorator


def publish_event(event_type: str, source: str = None, bus: EventBus = None, async_mode: bool = False):
    """事件发布装饰器

    使用示例:
    @publish_event(EventTypes.MARKET_ANALYSIS_UPDATED, source='StrategyEngine')
    def update_market_analysis(symbol: str, trend: str, volatility: float):
        # 业务逻辑
        return {
            'symbol': symbol,
            'trend': trend,
            'volatility': volatility
        }

    # 调用时会自动发布事件，返回值作为事件数据
    update_market_analysis('AAPL', 'UPTREND', 2.5)
    """
    if bus is None:
        bus = event_bus

    def decorator(func):
        def wrapper(*args, **kwargs):
            # 执行原函数
            result = func(*args, **kwargs)

            # 如果有返回值，作为事件数据发布
            if result is not None:
                if async_mode:
                    bus.publish_async(event_type, result, source)
                else:
                    bus.publish(event_type, result, source)

            return result
        return wrapper
    return decorator


def emit_event(event_type: str, source: str = None, bus: EventBus = None, async_mode: bool = False):
    """更简洁的事件发布装饰器，可以传入额外数据

    使用示例:
    @emit_event(EventTypes.SIGNAL_GENERATED, source='StrategyEngine')
    def generate_signal(self, signal_data):
        # 业务逻辑
        log.info(f"生成信号: {signal_data}")
        # 返回要发布的事件数据
        return signal_data
    """
    return publish_event(event_type, source, bus, async_mode)


# 事件类型常量
class EventTypes:
    """标准事件类型定义"""

    # 市场数据事件
    MARKET_DATA_RECEIVED = "market_data_received"
    MARKET_ANALYSIS_UPDATED = "market_analysis_updated"
    PRICE_UPDATED = "price_updated"

    # 策略事件
    SIGNAL_GENERATED = "signal_generated"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"

    # 系统事件
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    ERROR_OCCURRED = "error_occurred"

    # 监控事件
    MONITOR_UPDATE = "monitor_update"
    HEALTH_CHECK = "health_check"