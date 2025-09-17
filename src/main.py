"""
Al Brooks价格行为量化策略 - 基于alpaca-py的数据层架构
使用alpaca-py官方包进行实时数据获取和交易执行
"""

from alpaca.data.live import StockDataStream
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from typing import Dict, List
import threading
from datetime import datetime, timedelta

from config.config import TradingConfig
from utils.log import setup_logging
from utils.data_transforms import alpaca_bar_to_bar_data
from strategy.strategy_engine import StrategyEngine
from monitor.service import monitor
from monitor.data import SystemStatus
from monitor.web_server import WebMonitorServer
from models.market_data import BarData

log = setup_logging(module_prefix='ENGINE')

class TradingEngine:
    """交易引擎 - 完整的量化交易系统"""

    def __init__(self):
        self.config = TradingConfig.create()
        self.symbols = ["FAKEPACA"] if self.config.is_test else self.config.symbols

        # 初始化监控服务
        monitor.set_system_status(SystemStatus.STARTING)
        for symbol in self.symbols:
            monitor.update_symbol_status(symbol, trend="UNKNOWN", volatility=0.0, volume_profile="UNKNOWN")

        # 启动Web监控服务器
        self.web_monitor = WebMonitorServer(port=8080)
        if self.web_monitor.start():
            log.info(f"[MONITOR] 监控面板: {self.web_monitor.get_url()}")
        else:
            log.warning("[MONITOR] 监控面板启动失败")

        # 批量加载历史数据
        historical_data_by_symbol = self._load_historical_data_batch()

        self.strategy_engines: Dict[str, StrategyEngine] = {}
        for symbol in self.symbols:
            # 传入预加载的历史数据
            symbol_historical_data = historical_data_by_symbol.get(symbol, [])
            self.strategy_engines[symbol] = StrategyEngine(
                symbol,
                self.config,
                preloaded_historical_data=symbol_historical_data
            )

        self.stream = None
        self.stream_thread = None
        self._init_stream()

    def _load_historical_data_batch(self, days: int = 30) -> Dict[str, List[BarData]]:
        """批量加载所有symbol的历史数据"""
        historical_data_by_symbol = {}

        try:
            client = StockHistoricalDataClient(
                api_key=self.config.api_key,
                secret_key=self.config.secret_key
            )

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 一次性请求所有symbol的历史数据
            request = StockBarsRequest(
                symbol_or_symbols=self.symbols,
                timeframe=TimeFrame.Minute,
                start=start_date,
                end=end_date,
                feed=self.config.data_feed
            )

            bars = client.get_stock_bars(request)

            # 按symbol分组历史数据
            for symbol in self.symbols:
                symbol_bars = bars.data.get(symbol, [])
                if symbol_bars:
                    # 转换为BarData对象
                    symbol_bar_data = []
                    for bar in symbol_bars:
                        bar_data = BarData(
                            symbol=symbol,
                            timestamp=bar.timestamp,
                            open=float(bar.open),
                            high=float(bar.high),
                            low=float(bar.low),
                            close=float(bar.close),
                            volume=int(bar.volume)
                        )
                        symbol_bar_data.append(bar_data)

                    historical_data_by_symbol[symbol] = symbol_bar_data
                    log.info(f"{symbol}: 批量加载了{len(symbol_bars)}根历史K线")
                else:
                    log.warning(f"{symbol}: 未获取到历史数据")
                    historical_data_by_symbol[symbol] = []

        except Exception as e:
            log.error(f"批量加载历史数据失败: {e}")
            # 如果批量加载失败，返回空字典，StrategyEngine将回退到单独加载
            for symbol in self.symbols:
                historical_data_by_symbol[symbol] = []

        return historical_data_by_symbol

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
        log.info("启动交易引擎...")
        monitor.set_system_status(SystemStatus.RUNNING)
        monitor.set_connection_status(data_feed=False, trading_api=True)

        async def on_bar_data(bar):
            if bar.symbol in self.strategy_engines:
                bar_data = alpaca_bar_to_bar_data(bar)
                log.info(f"[BAR] {bar.symbol} 收到K线数据: {bar_data}")

                # 更新监控数据
                monitor.update_bar_received(bar.symbol)
                monitor.update_symbol_status(
                    bar.symbol,
                    current_price=bar_data.close,
                    price_change=None,  # TODO: 计算价格变化
                    price_change_pct=None  # TODO: 计算价格变化百分比
                )

                # 处理新K线数据
                signal = self.strategy_engines[bar.symbol].process_new_bar(bar_data)

                # 记录生成的信号
                if signal:
                    monitor.add_signal(
                        symbol=signal.symbol,
                        signal_type=signal.signal_type,
                        price=signal.price,
                        confidence=signal.confidence,
                        reason=signal.reason
                    )

        self.stream.subscribe_bars(on_bar_data, *self.symbols)

        def run_stream():
            log.info(f"[STREAM] 启动Alpaca数据流，数据源: {self.config.data_feed}")
            log.info(f"[STREAM] 已订阅股票: {self.symbols}")
            try:
                monitor.set_connection_status(data_feed=True)
                self.stream.run()
            except Exception as e:
                log.error(f"[ERROR] 数据流运行错误: {e}")
                monitor.set_connection_status(data_feed=False)
                monitor.increment_error_count()

        self.stream_thread = threading.Thread(target=run_stream, daemon=False)
        self.stream_thread.start()
        log.info(f"已启动实时数据流，监听股票: {self.symbols}")

    def stop(self):
        """停止策略"""
        log.info("停止交易引擎...")
        monitor.set_system_status(SystemStatus.STOPPED)

        if self.stream:
            self.stream.stop()
        if self.stream_thread:
            self.stream_thread.join(timeout=5)

        # 停止Web监控服务器
        if hasattr(self, 'web_monitor'):
            self.web_monitor.stop()

        log.info("交易引擎已停止")

if __name__ == "__main__":
    engine = TradingEngine()
    try:
        engine.start()
        engine.stream_thread.join()
    except KeyboardInterrupt:
        log.info("收到停止信号...")
        engine.stop()