import argparse
import yaml
from datetime import datetime

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

    # TODO: 在这里添加回测的逻辑
    print("\nBacktesting logic not yet implemented.")

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

    # --- 实盘模式子命令 (无 --symbols 参数) ---
    live_parser = subparsers.add_parser('live', help='Run in live mode (uses symbols from config)')
    live_parser.set_defaults(func=run_live)

    # --- 回测模式子命令 (有 --symbols 参数) ---
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

    # 调用选定模式对应的函数
    args.func(args, config)

if __name__ == "__main__":
    main()