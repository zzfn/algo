import argparse
import yaml
import arrow
from dotenv import load_dotenv
from loguru import logger
import asyncio
import os

# 核心模块导入
from src.utils.logger_setup import setup_logging
from src.data.alpaca_loader import load_historical_data
from src.backtesting.engine import run_pa_backtest
from alpaca.data.live.stock import StockDataStream

async def run_live(args, config):
    """
    主函数：执行实盘交易
    """
    logger.info("--- Starting Live Trading Mode ---")
    symbols = config.get('trading', {}).get('symbols', [])
    if not symbols:
        logger.error("No symbols to trade. Please specify 'symbols' in your config file.")
        return

    logger.info(f"Using config file: {args.config}")
    logger.info(f"Subscribing to symbols: {symbols}")
    
    # --- WebSocket 连接逻辑 ---
    # 1. 初始化 live client
    wss_client = StockDataStream(
        config['alpaca']['api_key'],
        config['alpaca']['secret_key']
    )

    # 2. 定义一个异步的处理器，用来处理接收到的数据
    async def trade_handler(data):
        # 当接收到新的交易数据时，这个函数会被调用
        # data 对象包含了交易的所有信息
        logger.info(f"Received trade: {data}")

    # 3. 订阅我们感兴趣的交易品种
    for symbol in symbols:
        wss_client.subscribe_trades(trade_handler, symbol)

    # 4. 启动并运行 WebSocket 客户端
    await wss_client._run_forever()

def run_backtest(args, config):
    """
    主函数：执行回测
    """
    logger.info("--- Starting Backtest Mode ---")
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = config.get('trading', {}).get('symbols', [])
    
    if not symbols:
        logger.error("No symbols to backtest. Please specify in config file or via --symbols.")
        return

    logger.info(f"Using config file: {args.config}")
    logger.info(f"Backtesting symbols: {symbols}")
    logger.info(f"Start date: {args.start_date}")
    logger.info(f"End date: {args.end_date}")

    try:
        tz = "America/New_York"
        start_date = arrow.get(args.start_date, "YYYY-MM-DD", tzinfo=tz).datetime
        end_date = arrow.get(args.end_date, "YYYY-MM-DD", tzinfo=tz).datetime
        timeframe = config.get('trading', {}).get('timeframe', '1Day')

        logger.info(f"Loading data for {symbols} from {start_date.date()} to {end_date.date()}...")
        
        load_dotenv()

        all_data = load_historical_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe_str=timeframe
        )

        if not all_data:
            logger.warning("No data loaded. Exiting.")
            return

        logger.success(f"Data loaded successfully for symbols: {list(all_data.keys())}")
        
        for symbol, df in all_data.items():
            logger.info(f"--- Preparing data for {symbol} ---")
            
            data_for_bt = df.copy()
            data_for_bt.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            logger.info(f"Running backtest for {symbol}...")
            initial_capital = config.get('backtesting', {}).get('initial_capital', 100000.0)
            
            run_pa_backtest(
                data=data_for_bt,
                initial_capital=initial_capital
            )

    except Exception:
        logger.exception("An error occurred during backtest preparation:")

def main():
    """
    解析命令行参数并根据模式调用相应的主函数
    """
    parser = argparse.ArgumentParser(
        description="Al Brooks Price Action Trading System",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to the configuration file (default: config.yaml)'
    )

    subparsers = parser.add_subparsers(dest='mode', required=True, help='Execution mode')

    live_parser = subparsers.add_parser('live', help='Run in live mode (uses symbols from config)')
    live_parser.set_defaults(func=run_live)

    backtest_parser = subparsers.add_parser('backtest', help='Run in backtesting mode')
    backtest_parser.add_argument(
        '--start-date',
        required=True,
        help='Backtest start date (YYYY-MM-DD)'
    )
    backtest_parser.add_argument(
        '--end-date',
        required=True,
        help='Backtest end date (YYYY-MM-DD)'
    )
    backtest_parser.add_argument(
        '-s', '--symbols',
        nargs='+',
        help='(Optional) Override the symbols to backtest from the config file'
    )
    backtest_parser.set_defaults(func=run_backtest)

    args = parser.parse_args()
    
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{args.config}' not found.") # Logger not available yet
        return

    setup_logging(config)

    if args.mode == 'live':
        load_dotenv()
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        if not api_key or not secret_key:
            logger.error("API keys not found for live trading. Please set them in your .env file.")
            return
        config['alpaca']['api_key'] = api_key
        config['alpaca']['secret_key'] = secret_key
        
        try:
            asyncio.run(args.func(args, config))
        except KeyboardInterrupt:
            logger.info("Live trading stopped by user.")
    else:
        args.func(args, config)

if __name__ == "__main__":
    main()