# Makefile for the Al Brooks Trading System

# Default variables for backtesting. Can be overridden from the command line.
# e.g., make backtest START_DATE=2023-01-01 END_DATE=2023-12-31 SYMBOLS="[SPY,QQQ]"
START_DATE ?= $(shell date +%Y-01-01)
END_DATE   ?= $(shell date +%Y-%m-%d)
SYMBOLS    ?= "[SPY]" # Hydra expects a list-like string

# Define .PHONY to avoid conflicts with files of the same name
.PHONY: help install live backtest

help:
	@echo "Available commands:"
	@echo "  install    - Sync dependencies from pyproject.toml using uv"
	@echo "  live       - Run the system in live trading mode"
	@echo "  backtest   - Run a backtest with default or specified parameters"
	@echo "               e.g., make backtest START_DATE=2023-01-01 SYMBOLS=\"[SPY,AAPL]\""

install:
	@echo "--- Syncing dependencies with uv ---"
	uv pip sync

live:
	@echo "--- Starting Live Trading Mode ---"
	uv run main.py live

backtest:
	@echo "--- Running Backtest [Symbols: $(SYMBOLS), Period: $(START_DATE) to $(END_DATE)] ---"
	uv run main.py data.start_date=$(START_DATE) data.end_date=$(END_DATE) data.symbols=$(SYMBOLS)