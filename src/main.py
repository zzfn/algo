"""
Al Brooks价格行为量化策略 - 基于alpaca-py的数据层架构
使用alpaca-py官方包进行实时数据获取和交易执行
"""

from alpaca.data.live import StockDataStream

from typing import Dict
import threading

from config.config import TradingConfig
from utils.log import setup_logging
from utils.data_transforms import alpaca_bar_to_bar_data
from strategy.strategy_engine import StrategyEngine

log = setup_logging()

class TradingEngine:
    """交易引擎 - 完整的量化交易系统"""

    def __init__(self):
        self.config = TradingConfig.create()
        self.symbols = ["FAKEPACA"] if self.config.is_test else self.config.symbols

        self.strategy_engines: Dict[str, StrategyEngine] = {}
        for symbol in self.symbols:
            self.strategy_engines[symbol] = StrategyEngine(symbol, self.config)

        self.stream = None
        self.stream_thread = None
        self._init_stream()

    def _init_stream(self):
        """初始化数据流"""
        self.stream = StockDataStream(
            api_key=self.config.api_key,
            secret_key=self.config.secret_key,
            feed=self.config.data_feed,
            url_override="wss://stream.data.alpaca.markets/v2/test" if self.config.is_test else None
        )


    def start(self):
        """启动策略"""
        log.info("[ENGINE] 启动交易引擎...")

        async def on_bar_data(bar):
            if bar.symbol in self.strategy_engines:
                bar_data = alpaca_bar_to_bar_data(bar)
                log.info(f"[BAR] {bar.symbol} 收到K线数据: {bar_data}")
                self.strategy_engines[bar.symbol].process_new_bar(bar_data)

        self.stream.subscribe_bars(on_bar_data, *self.symbols)

        def run_stream():
            log.info(f"[STREAM] 启动Alpaca数据流，数据源: {self.config.data_feed}")
            log.info(f"[STREAM] 已订阅股票: {self.symbols}")
            try:
                self.stream.run()
            except Exception as e:
                log.error(f"[ERROR] 数据流运行错误: {e}")

        self.stream_thread = threading.Thread(target=run_stream, daemon=False)
        self.stream_thread.start()
        log.info(f"[ENGINE] 已启动实时数据流，监听股票: {self.symbols}")

    def stop(self):
        """停止策略"""
        log.info("[ENGINE] 停止交易引擎...")
        if self.stream:
            self.stream.stop()
        if self.stream_thread:
            self.stream_thread.join(timeout=5)
        log.info("[ENGINE] 交易引擎已停止")

if __name__ == "__main__":
    engine = TradingEngine()
    try:
        engine.start()
        engine.stream_thread.join()
    except KeyboardInterrupt:
        log.info("[ENGINE] 收到停止信号...")
        engine.stop()