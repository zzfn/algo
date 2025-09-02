import talib
from backtesting import Strategy

from src.analysis.price_action_pipeline import PriceActionPipeline


class BacktestAdapter(Strategy):
    """
    适配器，作为策略 Pipeline 和 backtesting.py 框架的桥梁。
    """
    # 为满足 backtesting.py 框架要求，在此处声明参数。
    risk_per_trade = 0.02
    n_bars_for_trend = 10
    ema_slope_lookback = 5 
    symbol = "" # Add symbol parameter

    def init(self):
        """
        1. 初始化核心决策 Pipeline。
        2. **仅为绘图目的**，定义一个指标，让 plotting 函数可以显示它。
           这个指标不参与任何交易决策。
        """
        # Get symbol from self.data._symbol (provided by backtesting.py)
        # symbol = self.data._symbol # Removed

        self.pipeline = PriceActionPipeline(
            symbol=self.symbol, # Use self.symbol passed from engine
            n_bars_for_trend=self.n_bars_for_trend,
            ema_slope_lookback=self.ema_slope_lookback
        )

        # Initialize pipeline with historical data for warm-up (all data except the last bar)
        # The last bar will be processed by the first call to next()
        if len(self.data.df) > 1:
            self.pipeline.initialize_data(self.data.df.iloc[:-1])
        else:
            self.pipeline.initialize_data(pd.DataFrame())

        # Define indicator for plotting purposes only
        self.ema20_plot = self.I(talib.EMA, self.data.Close, timeperiod=20, name="EMA20")

    def next(self):
        """
        调用 Pipeline 获取决策，并执行交易。
        """
        current_position_size = self.position.size if self.position else 0.0

        # 每次只取最新的K线传递给 Pipeline
        new_bar = self.data.df.iloc[-1]

        # 调用 Pipeline 获取目标仓位和止损价
        target_shares, sl_price = self.pipeline.process_bar(
            new_bar=new_bar,
            current_position_size=current_position_size,
            risk_per_trade=self.risk_per_trade 
        )

        # --- 根据目标仓位执行交易 (手动调用 buy/sell/close) ---
        if target_shares > 0 and current_position_size == 0: 
            self.buy(size=target_shares, sl=sl_price)
        elif target_shares == 0 and current_position_size > 0: 
            self.position.close()