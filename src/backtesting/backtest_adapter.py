import talib
from backtesting import Strategy

from src.analysis.price_action_pipeline import PriceActionPipeline
from src.core.types import Signal
from src.risk.position_sizer import calculate_position_size


class BacktestAdapter(Strategy):
    """
    适配器，作为策略 Pipeline 和 backtesting.py 框架的桥梁。
    """
    # 为满足 backtesting.py 框架要求，在此处声明参数。
    symbol = "" 
    risk_per_trade = 0.02 
    ema_slope_lookback = 5 

    def init(self):
        """
        1. 初始化核心决策 Pipeline。
        2. **仅为绘图目的**，定义一个指标，让 plotting 函数可以显示它。
           这个指标不参与任何交易决策。
        """
        self.pipeline = PriceActionPipeline(
            symbol=self.symbol,
            # n_bars_for_trend=self.n_bars_for_trend, # Removed
            
        )

        # Initialize pipeline with historical data for warm-up (all data except the last bar)
        if len(self.data.df) > 1:
            self.pipeline.initialize_data(self.data.df.iloc[:-1])
        else:
            self.pipeline.initialize_data(pd.DataFrame())

        # Define indicator for plotting purposes only
        self.ema20_plot = self.I(talib.EMA, self.data.Close, timeperiod=20, name="EMA20")
        self.current_stop_loss_price = None # Initialize stop loss price

    def next(self):
        """
        调用 Pipeline 获取决策，并执行交易。
        """
        current_position_size = self.position.size if self.position else 0.0

        # 每次只取最新的K线传递给 Pipeline
        new_bar = self.data.df.iloc[-1]

        # 调用 Pipeline 获取要交易的数量和止损价
        signal = self.pipeline.process_bar(
            new_bar=new_bar,
            current_position_size=current_position_size,
            risk_per_trade=self.risk_per_trade 
        )

        # --- 根据 Signal 对象执行交易 ---
        if signal:
            shares_to_trade = calculate_position_size(
                signal=signal,
                current_position_size=current_position_size,
                risk_per_trade=self.risk_per_trade
            )

            if shares_to_trade > 0:
                self.buy(size=shares_to_trade)
                self.current_stop_loss_price = signal.stop_loss # Store the stop loss price from the signal
            elif shares_to_trade < 0:
                self.sell(size=abs(shares_to_trade)) # Sell the absolute amount
                self.current_stop_loss_price = None # Reset stop loss after closing position

        # --- Stop Loss Check ---
        if self.position and self.current_stop_loss_price is not None:
            if self.data.Close[-1] < self.current_stop_loss_price:
                self.sell(size=self.position.size) # Close entire position on stop loss
                self.current_stop_loss_price = None # Reset stop loss after closing position