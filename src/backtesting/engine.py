import os
from datetime import datetime

from backtesting import Backtest
from omegaconf import DictConfig, OmegaConf

from src.backtesting.backtest_adapter import BacktestAdapter
from src.data.alpaca_loader import load_historical_data


def run_backtest(cfg: DictConfig) -> None:
    """Runs the backtest with the given configuration."""
    # Symbol list is now managed by Hydra
    symbol = cfg.data.symbols[0]

    # Dates are now managed by Hydra
    start_date = datetime.strptime(cfg.data.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(cfg.data.end_date, "%Y-%m-%d")

    data_dict = load_historical_data(
        symbols=[symbol],
        start_date=start_date,
        end_date=end_date,
        timeframe_str=cfg.data.timeframe,
    )
    data = data_dict[symbol]

    # backtesting.py needs specific column names: Open, High, Low, Close, Volume
    data.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        },
        inplace=True,
    )

    bt = Backtest(
        data,
        BacktestAdapter,
        cash=cfg.backtest.cash,
        commission=cfg.backtest.commission,
    )

    # Extract strategy params from config and run
    strategy_params = OmegaConf.to_container(cfg.strategy.params, resolve=True)
    stats = bt.run(**strategy_params)

    print(stats)

    # --- Save plot to file ---
    output_dir = "backtest-result"
    os.makedirs(output_dir, exist_ok=True)

    # Generate a filename
    start_date_str = cfg.data.start_date
    end_date_str = cfg.data.end_date
    filename = f"{output_dir}/{symbol}_{start_date_str}_to_{end_date_str}.html"

    bt.plot(filename=filename)
    print(f"Backtest plot saved to: {filename}")