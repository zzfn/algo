"""
Al Brooks价格行为量化策略 - 基于alpaca-py的数据层架构
使用alpaca-py官方包进行实时数据获取和交易执行
"""

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed
from alpaca.common.exceptions import APIError

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading
import asyncio
import time
import os
from dotenv import load_dotenv
from logbook import Logger, StreamHandler
import sys

# 加载环境变量
load_dotenv()

# 初始化日志 - 配置输出到控制台
StreamHandler(sys.stdout, level='INFO').push_application()
log = Logger('AlgoTrading')

# ========================================
# 1. 配置管理 (Configuration)
# ========================================

@dataclass
class AlpacaConfig:
    """Alpaca配置"""
    # API密钥
    api_key: str = ""
    secret_key: str = ""

    # 环境设置
    is_test: bool = False  # True为测试模式

    # 数据设置
    data_feed: DataFeed = DataFeed.IEX  # iex, sip
    buffer_size: int = 1000  # 数据缓存大小


# ========================================
# 2. 数据结构定义 (Data Structures)
# ========================================

@dataclass
class MarketData:
    """市场数据基类"""
    symbol: str
    timestamp: datetime



@dataclass
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

@dataclass
class DataEvent:
    """数据事件"""
    event_type: DataEventType
    symbol: str
    data: Any  # TRADE 为 float 价格，BAR 为 BarData
    timestamp: datetime = field(default_factory=datetime.now)

# ========================================
# 3. 实时数据流管理 (Real-time Data Stream)
# ========================================

class AlpacaDataStream:
    """
    Alpaca实时数据流管理
    使用alpaca-py的StockDataStream
    """

    def __init__(self, config: AlpacaConfig):
        self.config = config
        self.stream = None
        self.subscribed_symbols = set()

        # 事件处理器
        self.event_handlers: Dict[DataEventType, List[Callable]] = {
            DataEventType.TRADE: [],
            DataEventType.BAR: []
        }

        # 初始化数据流
        self._init_stream()

    def _init_stream(self):
        """初始化数据流"""
        if self.config.is_test:
            self.stream = StockDataStream(
                api_key=self.config.api_key,
                secret_key=self.config.secret_key,
                feed=self.config.data_feed,
                url_override="wss://stream.data.alpaca.markets/v2/test"
            )
        else:
            self.stream = StockDataStream(
                api_key=self.config.api_key,
                secret_key=self.config.secret_key,
                feed=self.config.data_feed
            )

        # 数据处理器在订阅时设置

    async def _on_trade_data(self, trade):
        log.info(f"[TRADE] 收到交易数据: {trade}")
        """处理交易数据 - 仅传递价格"""
        # 直接创建简单的价格事件
        event = DataEvent(
            event_type=DataEventType.TRADE,
            symbol=trade.symbol,
            data=float(trade.price)  # 只传递价格
        )

        await self._dispatch_event(event)


    async def _on_bar_data(self, bar):
        """处理K线数据"""
        bar_data = BarData(
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
        log.info(f"[BAR] 收到K线数据: {bar_data}")
        event = DataEvent(
            event_type=DataEventType.BAR,
            symbol=bar.symbol,
            data=bar_data
        )

        await self._dispatch_event(event)

    async def _dispatch_event(self, event: DataEvent):
        """分发数据事件"""
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                log.error(f"[ERROR] 事件处理器错误: {e}")

    def register_handler(self, event_type: DataEventType, handler: Callable):
        """注册事件处理器"""
        self.event_handlers[event_type].append(handler)

    def subscribe_symbols(self, symbols: List[str]):
        """订阅股票数据"""
        self.subscribed_symbols.update(symbols)
        
        # 为每个股票单独订阅数据流 - 始终启用 trades 和 bars
        for symbol in symbols:
            self.stream.subscribe_trades(self._on_trade_data, symbol)
            self.stream.subscribe_bars(self._on_bar_data, symbol)

    def run(self):
        """启动数据流"""
        log.info(f"[STREAM] 启动Alpaca数据流，数据源: {self.config.data_feed}")
        try:
            self.stream.run()
        except Exception as e:
            log.error(f"[ERROR] 数据流运行错误: {e}")

    def stop(self):
        """停止数据流"""
        if self.stream:
            self.stream.stop()

# ========================================
# 4. 历史数据管理 (Historical Data)
# ========================================

class AlpacaHistoricalData:
    """
    Alpaca历史数据管理
    使用alpaca-py的StockHistoricalDataClient
    """

    def __init__(self, config: AlpacaConfig):
        self.config = config
        self.client = StockHistoricalDataClient(
            api_key=config.api_key,
            secret_key=config.secret_key
        )

    def get_bars(self,
                 symbols: List[str],
                 timeframe: TimeFrame,
                 start: datetime,
                 end: Optional[datetime] = None,
                 limit: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """获取历史K线数据"""

        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=timeframe,
            start=start,
            end=end or datetime.now(),
            limit=limit,
            feed=self.config.data_feed
        )

        try:
            bars = self.client.get_stock_bars(request)

            # 转换为DataFrame格式
            result = {}
            for symbol in symbols:
                symbol_bars = bars.data.get(symbol, [])
                if symbol_bars:
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
                    result[symbol] = df
                else:
                    result[symbol] = pd.DataFrame()

            return result

        except APIError as e:
            log.error(f"[ERROR] 获取历史数据错误: {e}")
            return {symbol: pd.DataFrame() for symbol in symbols}


# ========================================
# 5. 实时数据缓存 (Real-time Data Buffer)
# ========================================

class RealTimeDataBuffer:
    """实时数据缓存管理"""

    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size

        # 数据缓存 - 仅存储 K线历史数据
        self.bar_buffers: Dict[str, deque] = {}

        # 最新数据
        self.latest_trade_prices: Dict[str, float] = {}  # 只存储价格
        self.latest_bars: Dict[str, BarData] = {}

        # 线程锁
        self.lock = threading.Lock()

    def update_latest_trade_price(self, symbol: str, price: float):
        """更新最新交易价格 - 只存储价格"""
        with self.lock:
            self.latest_trade_prices[symbol] = price


    def add_bar(self, bar: BarData):
        """添加K线数据"""
        with self.lock:
            symbol = bar.symbol

            if symbol not in self.bar_buffers:
                self.bar_buffers[symbol] = deque(maxlen=self.buffer_size)

            self.bar_buffers[symbol].append(bar)
            self.latest_bars[symbol] = bar

    def get_recent_bars(self, symbol: str, count: int = 50) -> pd.DataFrame:
        """获取最近的K线数据"""
        with self.lock:
            if symbol not in self.bar_buffers:
                return pd.DataFrame()

            bars = list(self.bar_buffers[symbol])[-count:]

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

            if df_data:
                df = pd.DataFrame(df_data)
                df.set_index('timestamp', inplace=True)
                return df
            else:
                return pd.DataFrame()

    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        with self.lock:
            # 优先使用最新交易价格
            if symbol in self.latest_trade_prices:
                return self.latest_trade_prices[symbol]

            # 其次使用最新K线收盘价
            if symbol in self.latest_bars:
                return self.latest_bars[symbol].close

            return None

# ========================================
# 6. 主数据管理器 (Main Data Manager)
# ========================================

class AlpacaDataManager:
    """
    Alpaca数据管理器主类
    整合实时流、历史数据、缓存管理
    """

    def __init__(self, config: AlpacaConfig, symbols: List[str]):
        self.config = config
        # 测试模式下使用 FAKEPACA 符号
        self.symbols = ["FAKEPACA"] if config.is_test else symbols

        # 初始化组件
        self.historical = AlpacaHistoricalData(config)
        self.stream = AlpacaDataStream(config)
        self.buffer = RealTimeDataBuffer(config.buffer_size)

        # 注册实时数据处理器
        self.stream.register_handler(DataEventType.TRADE, self._on_trade)
        self.stream.register_handler(DataEventType.BAR, self._on_bar)

        # 策略回调
        self.strategy_callbacks: List[Callable] = []

        # 启动标志
        self.running = False
        self.stream_thread = None

    def _on_trade(self, event: DataEvent):
        """处理交易事件 - 仅更新最新价格"""
        if event.symbol in self.symbols:
            self.buffer.update_latest_trade_price(event.symbol, event.data)


    def _on_bar(self, event: DataEvent):
        """处理K线事件"""
        if event.symbol in self.symbols:
            self.buffer.add_bar(event.data)
            self._trigger_strategy_callbacks(event.symbol, 'bar')

    def _trigger_strategy_callbacks(self, symbol: str, data_type: str):
        """触发策略回调"""
        for callback in self.strategy_callbacks:
            try:
                callback(symbol, data_type)
            except Exception as e:
                log.error(f"[ERROR] 策略回调错误: {e}")

    def register_strategy_callback(self, callback: Callable):
        """注册策略回调"""
        self.strategy_callbacks.append(callback)

    def load_historical_data(self, days: int = 30) -> Dict[str, pd.DataFrame]:
        """加载历史数据"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        return self.historical.get_bars(
            symbols=self.symbols,
            timeframe=TimeFrame.Minute,
            start=start_date,
            end=end_date
        )

    def start_stream(self):
        """启动实时数据流"""
        if self.running:
            return

        self.running = True

        # 在单独线程中运行数据流
        def run_stream():
            # 先订阅股票，再启动流
            self.stream.subscribe_symbols(self.symbols)
            self.stream.run()

        self.stream_thread = threading.Thread(target=run_stream, daemon=True)
        self.stream_thread.start()

        log.info(f"[STREAM] 已启动实时数据流，监听股票: {self.symbols}")

    def stop_stream(self):
        """停止实时数据流"""
        if not self.running:
            return

        self.running = False
        self.stream.stop()

        if self.stream_thread:
            self.stream_thread.join(timeout=5)

        log.info("[STREAM] 已停止实时数据流")

    # 数据访问接口
    def get_realtime_bars(self, symbol: str, count: int = 50) -> pd.DataFrame:
        """获取实时K线数据"""
        return self.buffer.get_recent_bars(symbol, count)

    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        return self.buffer.get_current_price(symbol)


# ========================================
# 7. 使用示例
# ========================================

class StrategyInterface:
    """策略接口示例"""

    def __init__(self, symbols: List[str]):
        # 配置Alpaca
        config = AlpacaConfig(
            api_key=os.getenv("ALPACA_API_KEY", ""),
            secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
            is_test=True,  # 启用测试模式
            data_feed=DataFeed.IEX
        )

        self.symbols = symbols
        self.data_manager = AlpacaDataManager(config, symbols)

        # 注册策略回调
        self.data_manager.register_strategy_callback(self.on_market_data_update)

        # 预加载历史数据
        self.historical_data = {}

    def on_market_data_update(self, symbol: str, data_type: str):
        """市场数据更新回调"""
        if data_type == 'bar':
            # K线更新时触发策略分析
            current_price = self.data_manager.get_current_price(symbol)
            bars_df = self.data_manager.get_realtime_bars(symbol, 50)

            if len(bars_df) >= 20:  # 有足够数据时分析
                log.info(f"[STRATEGY] {symbol}: 新K线 @ {current_price}, 共{len(bars_df)}根K线")

                # 这里调用Al Brooks策略分析
                self.analyze_price_action(symbol, bars_df, current_price)

    def analyze_price_action(self, symbol: str, bars: pd.DataFrame, current_price: float):
        """价格行为分析"""
        # TODO: 实现Al Brooks价格行为分析逻辑
        pass

    def start(self):
        """启动策略"""
        log.info("[STRATEGY] 加载历史数据...")
        self.historical_data = self.data_manager.load_historical_data(30)

        log.info("[STRATEGY] 启动实时数据流...")
        self.data_manager.start_stream()

    def stop(self):
        """停止策略"""
        self.data_manager.stop_stream()

if __name__ == "__main__":
    # 使用示例 - 减少股票数量避免超限
    symbols = ["AAPL","TSLA"]

    strategy = StrategyInterface(symbols)

    try:
        strategy.start()

        # 保持运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        log.info("[STRATEGY] 停止策略...")
        strategy.stop()