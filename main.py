from dotenv import load_dotenv

# Load environment variables from .env file at the very beginning
load_dotenv()

import hydra
from omegaconf import DictConfig

from src.backtesting.engine import run_backtest


@hydra.main(version_base=None, config_path=".", config_name="config.yaml")
def main(cfg: DictConfig) -> None:
    """Main function to run the backtest."""
    run_backtest(cfg)


if __name__ == "__main__":
    main()
