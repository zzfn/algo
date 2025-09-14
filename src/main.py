"""
Al Brooks价格行为量化策略 - 基于alpaca-py的数据层架构
使用alpaca-py官方包进行实时数据获取和交易执行
"""

from alpaca.data.live import StockDataStream

from typing import Dict, List, Optional
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


class AlpacaDataStreamManager:
    """
    Alpaca实时数据流管理器
    直接与策略引擎交互
    """

    def __init__(self, config: TradingConfig, data_manager=None):
        self.config = config
        self.stream = None
        self.data_manager = data_manager
        self.subscribed_symbols: List[str] = []

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

    async def _on_trade_data(self, trade):
        """全局交易数据处理器 - 直接传递给数据管理器"""
        if self.data_manager:
            # 使用纯函数转换时间格式
            et_time = format_timestamp_to_et(trade.timestamp)
            log.info(f"[TRADE] {trade.symbol} {et_time} ${trade.price}")

            self.data_manager._process_trade(trade.symbol, float(trade.price))

    async def _on_bar_data(self, bar):
        """全局K线数据处理器 - 直接传递给数据管理器"""
        if self.data_manager:
            # 使用纯函数转换数据
            bar_data = alpaca_bar_to_bar_data(bar)
            log.info(f"[BAR] {bar.symbol} 收到K线数据: {bar_data}")

            self.data_manager._process_strategy(bar.symbol, bar_data)

    def subscribe_symbols(self, symbol_list: List[str]):
        """订阅多个股票数据"""
        self.subscribed_symbols = symbol_list

        # 统一订阅 WebSocket 数据流（全局唯一连接）
        self.stream.subscribe_trades(self._on_trade_data, *symbol_list)
        self.stream.subscribe_bars(self._on_bar_data, *symbol_list)

    def run(self):
        """启动数据流"""
        log.info(f"[STREAM] 启动Alpaca数据流，数据源: {self.config.data_feed}")
        log.info(f"[STREAM] 已订阅股票: {self.subscribed_symbols}")
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
    整合实时流，协调策略引擎
    """

    def __init__(self, config: TradingConfig, symbols: List[str], strategy_engines: Dict[str, StrategyEngine] = None):
        self.config = config
        # 测试模式下使用 FAKEPACA 符号
        self.symbols = ["FAKEPACA"] if config.is_test else symbols

        # 策略引擎引用
        self.strategy_engines = strategy_engines or {}

        # 初始化数据流管理器，传入自己作为回调目标
        self.stream_manager = AlpacaDataStreamManager(config, self)

        # 数据流线程
        self.stream_thread = None

    def _process_strategy(self, symbol: str, bar_data: BarData):
        """处理单个股票的策略逻辑"""
        if symbol in self.strategy_engines:
            strategy_engine = self.strategy_engines[symbol]
            # 策略引擎自己管理数据缓存和处理
            strategy_engine.process_new_bar(bar_data)

    def _process_trade(self, symbol: str, price: float):
        """处理交易数据"""
        if symbol in self.strategy_engines:
            self.strategy_engines[symbol].update_trade_price(price)


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