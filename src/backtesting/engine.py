import pandas as pd
from backtesting import Backtest
from src.backtesting.pa_strategy import PriceActionStrategy
from loguru import logger

def run_pa_backtest(
    data: pd.DataFrame,
    initial_capital: float = 100000.0,
):
    """
    使用 backtesting.py 库运行价格行为策略回测。

    Args:
        data: 包含OHLCV数据的DataFrame，列名需为大写的Open, High, Low, Close。
        initial_capital: 初始资金。
    """
    logger.info("--- Running Backtest with backtesting.py ---")
    
    bt = Backtest(
        data,
        PriceActionStrategy,
        cash=initial_capital,
        commission=.002 # 0.2% 的手续费
    )
    
    stats = bt.run()
    
    # 使用 logger.info 打印结果，并用换行符美化
    logger.info("\n--- Backtest Results ---\n" + stats.to_string())
    
    # logger.info("To view the interactive plot, uncomment the bt.plot() line below.")
    # bt.plot()
