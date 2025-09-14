"""
Al Brooks价格行为量化策略 - 基于alpaca-py的数据层架构
使用alpaca-py官方包进行实时数据获取和交易执行
"""

from alpaca.data.live import StockDataStream

from datetime import datetime
from typing import Dict, List, Optional, Callable
import threading

from config.config import TradingConfig
from utils.log import setup_logging
from utils.data_transforms import (
    alpaca_bar_to_bar_data,
    format_timestamp_to_et
)
from models.market_data import BarData
from strategy.strategy_engine import StrategyEngine

# 初始化日志
log = setup_logging()

# ========================================
# 3. 实时数据流管理 (Real-time Data Stream)
# ========================================

class SymbolDataStream:
    """单个股票的数据流处理器"""
    
    def __init__(self, symbol: str, config: TradingConfig):
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

        # 使用纯函数转换时间格式
        et_time = format_timestamp_to_et(timestamp)
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

    def __init__(self, config: TradingConfig):
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
            # 使用纯函数转换数据
            bar_data = alpaca_bar_to_bar_data(bar)
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
# 4. 主数据管理器 (Main Data Manager)
# ========================================

class AlpacaDataManager:
    """
    Alpaca数据管理器主类
    整合实时流、历史数据，协调策略引擎
    """

    def __init__(self, config: TradingConfig, symbols: List[str], strategy_engines: Dict[str, StrategyEngine] = None):
        self.config = config
        # 测试模式下使用 FAKEPACA 符号
        self.symbols = ["FAKEPACA"] if config.is_test else symbols

        # 初始化组件
        self.stream_manager = AlpacaDataStreamManager(config)

        # 策略引擎引用
        self.strategy_engines = strategy_engines or {}

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

        # 数据流线程
        self.stream_thread = None

    def _on_trade(self, symbol: str, price: float, timestamp: datetime):
        """处理交易事件 - 传递给策略引擎"""
        self._process_trade(symbol, price)

    def _on_bar(self, symbol: str, bar_data: BarData):
        """处理K线事件并直接执行策略"""
        # 直接传递给策略引擎处理
        if symbol in self.strategy_engines:
            self._process_strategy(symbol, bar_data)

    def _process_strategy(self, symbol: str, bar_data: BarData):
        """处理单个股票的策略逻辑"""
        strategy_engine = self.strategy_engines[symbol]

        # 策略引擎自己管理数据缓存和处理
        strategy_engine.process_new_bar(bar_data)

    def _process_trade(self, symbol: str, price: float):
        """处理交易数据"""
        if symbol in self.strategy_engines:
            self.strategy_engines[symbol].update_trade_price(price)
        
    def get_symbol_stream(self, symbol: str) -> Optional[SymbolDataStream]:
        """获取指定股票的数据流实例"""
        return self.symbol_streams.get(symbol)


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

    # 数据访问接口（现在通过策略引擎获取）
    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        if symbol in self.strategy_engines:
            return self.strategy_engines[symbol].get_current_price()
        return None


# ========================================
# 6. 使用示例
# ========================================

class TradingEngine:
    """交易引擎 - 协调所有股票的数据管理和策略执行"""

    def __init__(self):
        # 自动加载所有配置
        config = TradingConfig.create()
        self.symbols = config.symbols

        # 为每个股票创建策略引擎
        self.strategy_engines: Dict[str, StrategyEngine] = {}
        for symbol in self.symbols:
            self.strategy_engines[symbol] = StrategyEngine(symbol)

        # 创建数据管理器，传入策略引擎引用
        self.data_manager = AlpacaDataManager(
            config,
            config.symbols,
            self.strategy_engines
        )

        # 策略引擎自己管理历史数据，无需预加载


    def start(self):
        """启动策略"""
        log.info("[STRATEGY] 启动实时数据流...")
        self.data_manager.start_stream()

    def stop(self):
        """停止策略"""
        self.data_manager.stop_stream()

if __name__ == "__main__":
    engine = TradingEngine()

    try:
        engine.start()

        # 等待数据流线程结束（或 Ctrl+C 中断）
        engine.data_manager.stream_thread.join()

    except KeyboardInterrupt:
        log.info("[ENGINE] 停止交易引擎...")
        engine.stop()