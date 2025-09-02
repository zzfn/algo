import os
import warnings
from datetime import datetime

from backtesting import Backtest
from omegaconf import DictConfig, OmegaConf

from src.backtesting.backtest_adapter import BacktestAdapter
from src.data.alpaca_loader import load_historical_data


def run_backtest(cfg: DictConfig) -> None:
    """Runs the backtest with the given configuration."""
    symbol = cfg.data.symbols[0]
    start_date = datetime.strptime(cfg.data.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(cfg.data.end_date, "%Y-%m-%d")

    data_dict = load_historical_data(
        symbols=[symbol],
        start_date=start_date,
        end_date=end_date,
        timeframe_str=cfg.data.timeframe,
    )
    data = data_dict[symbol]

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
        finalize_trades=True,
    )

    strategy_params = OmegaConf.to_container(cfg.strategy.params, resolve=True)
    strategy_params['symbol'] = symbol
    stats = bt.run(**strategy_params)

    print(stats)

    output_dir = "backtest-result"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    start_date_str = cfg.data.start_date
    end_date_str = cfg.data.end_date
    filename = f"{output_dir}/{symbol}_{start_date_str}_to_{end_date_str}_{timestamp}.html"

    # Suppress the known, benign warning about timezones from Bokeh
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, message=".*no explicit representation of timezones.*")
        bt.plot(filename=filename,open_browser=False)
    
    print(f"Backtest plot saved to: {filename}")