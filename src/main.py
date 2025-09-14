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
import os
from dotenv import load_dotenv
from logbook import Logger, StreamHandler
import sys
import arrow

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

class SymbolDataStream:
    """单个股票的数据流处理器"""
    
    def __init__(self, symbol: str, config: AlpacaConfig):
        self.symbol = symbol
        self.config = config
        
        # 该股票专属的回调处理器
        self.on_trade_callback: Optional[Callable[[float, datetime], None]] = None
        self.on_bar_callback: Optional[Callable[[BarData], None]] = None
        self.on_error_callback: Optional[Callable[[str], None]] = None
        
        # 股票专属的数据缓存
        self.latest_price: Optional[float] = None
        self.latest_bar: Optional[BarData] = None
        
    def set_trade_callback(self, callback: Callable[[float, datetime], None]):
        """设置交易数据回调"""
        self.on_trade_callback = callback
        
    def set_bar_callback(self, callback: Callable[[BarData], None]):
        """设置K线数据回调"""
        self.on_bar_callback = callback
        
    def set_error_callback(self, callback: Callable[[str], None]):
        """设置错误处理回调"""
        self.on_error_callback = callback
        
    def handle_trade_data(self, price: float, timestamp: datetime):
        """处理交易数据"""
        self.latest_price = price
        
        # 转换为美东时间并格式化
        et_time = arrow.get(timestamp).to('US/Eastern').format('YYYY-MM-DD HH:mm:ss.SSSSSS')
        log.info(f"[TRADE] {self.symbol} {et_time} ${price}")
        
        if self.on_trade_callback:
            try:
                self.on_trade_callback(price, timestamp)
            except Exception as e:
                log.error(f"[ERROR] {self.symbol} 交易回调错误: {e}")
                if self.on_error_callback:
                    self.on_error_callback(str(e))
                    
    def handle_bar_data(self, bar_data: BarData):
        """处理K线数据"""
        self.latest_bar = bar_data
        log.info(f"[BAR] {self.symbol} 收到K线数据: {bar_data}")
        
        if self.on_bar_callback:
            try:
                self.on_bar_callback(bar_data)
            except Exception as e:
                log.error(f"[ERROR] {self.symbol} K线回调错误: {e}")
                if self.on_error_callback:
                    self.on_error_callback(str(e))

class AlpacaDataStreamManager:
    """
    Alpaca实时数据流管理器
    管理所有股票的数据流实例
    """

    def __init__(self, config: AlpacaConfig):
        self.config = config
        self.stream = None
        self.symbol_streams: Dict[str, SymbolDataStream] = {}

        # 初始化数据流
        self._init_stream()

    def _init_stream(self):
        """初始化数据流"""
        self.stream = StockDataStream(
            api_key=self.config.api_key,
            secret_key=self.config.secret_key,
            feed=self.config.data_feed,
            url_override="wss://stream.data.alpaca.markets/v2/test" if self.config.is_test else None
        )

    def add_symbol(self, symbol: str) -> SymbolDataStream:
        """添加股票并返回其数据流实例"""
        if symbol in self.symbol_streams:
            return self.symbol_streams[symbol]
            
        symbol_stream = SymbolDataStream(symbol, self.config)
        self.symbol_streams[symbol] = symbol_stream
        
        return symbol_stream
        
    def get_symbol_stream(self, symbol: str) -> Optional[SymbolDataStream]:
        """获取指定股票的数据流实例"""
        return self.symbol_streams.get(symbol)
        
    async def _on_trade_data(self, trade):
        """全局交易数据处理器 - 分发到对应的股票实例"""
        symbol_stream = self.symbol_streams.get(trade.symbol)
        if symbol_stream:
            symbol_stream.handle_trade_data(float(trade.price), trade.timestamp)
        
    async def _on_bar_data(self, bar):
        """全局K线数据处理器 - 分发到对应的股票实例"""
        symbol_stream = self.symbol_streams.get(bar.symbol)
        if symbol_stream:
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
            symbol_stream.handle_bar_data(bar_data)

    def subscribe_symbols(self, symbol_list: List[str]) -> List[SymbolDataStream]:
        """订阅多个股票数据，返回对应的数据流实例列表"""
        # 首先为所有股票创建实例
        symbol_streams = [self.add_symbol(symbol) for symbol in symbol_list]
        
        # 然后统一订阅 WebSocket 数据流（全局唯一连接）
        self.stream.subscribe_trades(self._on_trade_data, *symbol_list)
        self.stream.subscribe_bars(self._on_bar_data, *symbol_list)
        
        return symbol_streams

    def run(self):
        """启动数据流"""
        log.info(f"[STREAM] 启动Alpaca数据流，数据源: {self.config.data_feed}")
        log.info(f"[STREAM] 已订阅股票: {list(self.symbol_streams.keys())}")
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
        self.stream_manager = AlpacaDataStreamManager(config)
        self.buffer = RealTimeDataBuffer(config.buffer_size)

        # 为每个股票创建数据流实例并设置回调
        self.symbol_streams: Dict[str, SymbolDataStream] = {}
        for symbol in self.symbols:
            symbol_stream = self.stream_manager.add_symbol(symbol)
            self.symbol_streams[symbol] = symbol_stream
            
            # 设置每个股票的专属回调
            symbol_stream.set_trade_callback(
                lambda price, timestamp, s=symbol: self._on_trade(s, price, timestamp)
            )
            symbol_stream.set_bar_callback(
                lambda bar_data, s=symbol: self._on_bar(s, bar_data)
            )

        # 策略回调
        self.strategy_callbacks: List[Callable] = []

        # 数据流线程
        self.stream_thread = None

    def _on_trade(self, symbol: str, price: float, timestamp: datetime):
        """处理交易事件 - 仅更新最新价格"""
        self.buffer.update_latest_trade_price(symbol, price)

    def _on_bar(self, symbol: str, bar_data: BarData):
        """处理K线事件"""
        self.buffer.add_bar(bar_data)
        self._trigger_strategy_callbacks(symbol, 'bar')

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
        
    def get_symbol_stream(self, symbol: str) -> Optional[SymbolDataStream]:
        """获取指定股票的数据流实例"""
        return self.symbol_streams.get(symbol)

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
        # 先订阅所有股票
        self.stream_manager.subscribe_symbols(self.symbols)
        
        # 在单独线程中运行数据流
        def run_stream():
            self.stream_manager.run()

        self.stream_thread = threading.Thread(target=run_stream, daemon=False)
        self.stream_thread.start()

        log.info(f"[STREAM] 已启动实时数据流，监听股票: {self.symbols}")

    def stop_stream(self):
        """停止实时数据流"""
        self.stream_manager.stop()

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

        # 等待数据流线程结束（或 Ctrl+C 中断）
        strategy.data_manager.stream_thread.join()

    except KeyboardInterrupt:
        log.info("[STRATEGY] 停止策略...")
        strategy.stop()