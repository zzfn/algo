import argparse
import yaml
import arrow  # 使用 arrow 库处理时间
from dotenv import load_dotenv

# 假设的模块导入，如果IDE报错请暂时忽略
from src.data.alpaca_loader import load_historical_data
from src.core.types import Signal, Order, Confirmation

def run_live(args, config):
    """
    主函数：执行实盘交易
    """
    # 实盘模式下，symbols 固定从配置文件读取
    symbols = config.get('trading', {}).get('symbols', [])
    if not symbols:
        print("Error: No symbols to trade. Please specify 'symbols' in your config file.")
        return

    print("--- Starting Live Trading Mode ---")
    print(f"Using config file: {args.config}")
    print(f"Trading symbols from config: {symbols}")
    
    # TODO: 在这里添加实盘交易的初始化和主循环逻辑
    print("\nLive trading logic not yet implemented.")

def run_backtest(args, config):
    """
    主函数：执行回测
    """
    # 回测模式下，优先使用命令行传入的symbols，否则从配置读取
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = config.get('trading', {}).get('symbols', [])
    
    if not symbols:
        print("Error: No symbols to backtest. Please specify in config file or via --symbols.")
        return

    print("--- Starting Backtest Mode ---")
    print(f"Using config file: {args.config}")
    print(f"Backtesting symbols: {symbols}")
    print(f"Start date: {args.start_date}")
    print(f"End date: {args.end_date}")

    try:
        # 使用 arrow 将字符串日期转换为时区感知的datetime对象
        tz = "America/New_York"  # A common timezone for US stocks
        start_date = arrow.get(args.start_date, "YYYY-MM-DD", tzinfo=tz).datetime
        end_date = arrow.get(args.end_date, "YYYY-MM-DD", tzinfo=tz).datetime
        timeframe = config.get('trading', {}).get('timeframe', '1Day')

        print(f"\nLoading data for {symbols} from {start_date.date()} to {end_date.date()}...")
        
        # 加载环境变量，确保API密钥可用
        load_dotenv()

        # 调用数据加载模块
        all_data = load_historical_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe_str=timeframe
        )

        if not all_data:
            print("No data loaded. Exiting.")
            return

        print("Data loaded successfully for symbols:", list(all_data.keys()))
        sample_symbol = list(all_data.keys())[0]
        print(f"\n--- Sample data for {sample_symbol} ---")
        print(all_data[sample_symbol].head(3))

        # TODO: 在这里添加回测引擎的调用逻辑
        print("\nBacktesting engine logic not yet implemented.")

    except (ValueError, Exception) as e:
        print(f"\nAn error occurred during backtest preparation: {e}")


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

    # --- 实盘模式子命令 ---
    live_parser = subparsers.add_parser('live', help='Run in live mode (uses symbols from config)')
    live_parser.set_defaults(func=run_live)

    # --- 回测模式子命令 ---
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
        print(f"Error: Config file '{args.config}' not found.")
        return

    args.func(args, config)

if __name__ == "__main__":
    main()
