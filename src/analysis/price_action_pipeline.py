import pandas as pd
from src.risk.position_sizer import calculate_position_size
from src.core.types import Signal, TakeProfitTarget
from datetime import datetime
from typing import List

class PriceActionPipeline:
    """
    一个事件驱动、有状态的策略核心。
    它接收单根K线，维护自己的历史数据，并返回要交易的数量。
    """
    def __init__(self, symbol: str):
        self.symbol = symbol
        
        self.data_history = pd.DataFrame() # Internal data store for stateful processing

    def initialize_data(self, historical_data: pd.DataFrame):
        """
        Initializes the pipeline with historical data for warm-up.
        This method is called once at the beginning of the backtest.
        """
        self.data_history = historical_data.copy()

    def process_bar(self, 
                    new_bar: pd.Series, 
                    current_position_size: float, 
                    risk_per_trade: float
                   ) -> Signal | None:
        """
        Processes a new bar and generates the quantity to trade.
        """
        # Append the new bar to the internal data buffer
        if isinstance(new_bar, pd.Series):
            new_bar_df = pd.DataFrame([new_bar], index=[new_bar.name])
        else:
            new_bar_df = new_bar 

        self.data_history = pd.concat([self.data_history, new_bar_df])

        # Now, all calculations are performed on self.data_history
        df = self.data_history 

        

        df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()

        # --- 2. 判断市场状态 (基于EMA和价格关系) ---
        market_state = 'range'
        if df['Close'].iloc[-1] > df['ema_20'].iloc[-1]:
            market_state = 'uptrend'
        elif df['Close'].iloc[-1] < df['ema_20'].iloc[-1]:
            market_state = 'downtrend'

        df['market_state'] = market_state # Store market state in DataFrame

        

        # --- 3. 判断K线形态 ---
        is_bullish_engulfing = (df['Close'].iloc[-1] > df['Open'].iloc[-1]) and \
                               (df['Close'].iloc[-2] < df['Open'].iloc[-2]) and \
                               (df['Close'].iloc[-1] > df['Open'].iloc[-2]) and \
                               (df['Open'].iloc[-1] < df['Close'].iloc[-2])

        # New: Trend Bar detection
        # A simple definition: large body, closes near high/low
        # Body size relative to total range
        body_range = abs(df['Close'].iloc[-1] - df['Open'].iloc[-1])
        total_range = df['High'].iloc[-1] - df['Low'].iloc[-1]
        # Avoid division by zero
        body_ratio = body_range / total_range if total_range > 0 else 0

        # Close position relative to bar range
        close_to_high_ratio = (df['High'].iloc[-1] - df['Close'].iloc[-1]) / total_range if total_range > 0 else 0
        close_to_low_ratio = (df['Close'].iloc[-1] - df['Low'].iloc[-1]) / total_range if total_range > 0 else 0

        # Bullish Trend Bar: large body, closes near high
        is_bullish_trend_bar = (df['Close'].iloc[-1] > df['Open'].iloc[-1]) and \
                               (body_ratio > 0.7) and \
                               (close_to_high_ratio < 0.2) # Closes in top 20% of range

        # Bearish Trend Bar: large body, closes near low
        is_bearish_trend_bar = (df['Close'].iloc[-1] < df['Open'].iloc[-1]) and \
                               (body_ratio > 0.7) and \
                               (close_to_low_ratio < 0.2) # Closes in bottom 20% of range

        # New: Pin Bar detection
        # A simple definition: small body, long wick on one side, small wick on other
        # Body size relative to total range (e.g., < 0.3)
        # Wick size relative to total range (e.g., long wick > 0.6, short wick < 0.1)

        # Bullish Pin Bar: small body, long lower wick, small upper wick, close in upper half
        is_bullish_pin_bar = (body_ratio < 0.3) and \
                             (close_to_low_ratio > 0.6) and \
                             (close_to_high_ratio < 0.1) and \
                             (df['Close'].iloc[-1] > df['Open'].iloc[-1]) # Bullish body

        # Bearish Pin Bar: small body, long upper wick, small lower wick, close in lower half
        is_bearish_pin_bar = (body_ratio < 0.3) and \
                             (close_to_high_ratio > 0.6) and \
                             (close_to_low_ratio < 0.1) and \
                             (df['Close'].iloc[-1] < df['Open'].iloc[-1]) # Bearish body

        # --- 4. 决策逻辑 (返回要交易的数量) ---
        shares_to_trade = 0.0 # 默认不操作
        stop_loss_price = None

        # --- 买入/加仓逻辑 ---
        if market_state == 'uptrend' and is_bullish_engulfing:
            entry_price = df['Close'].iloc[-1]
            sl_for_calc = df['Low'].iloc[-1]
            
            # If target quantity is greater than current position, calculate the difference to buy
            # The actual position sizing will be handled by the external calculate_position_size
            if True: # Always generate signal if conditions met, let external function decide size
                return Signal(
                    symbol=self.symbol,
                    timestamp=df.index[-1].to_pydatetime(), # Convert pandas Timestamp to datetime
                    action="BUY",
                    signal_type="Bullish Engulfing",
                    entry_price=entry_price,
                    stop_loss=sl_for_calc,
                    reason="Uptrend and Bullish Engulfing"
                )
        elif market_state == 'uptrend' and is_bullish_trend_bar:
            entry_price = df['Close'].iloc[-1]
            sl_for_calc = df['Low'].iloc[-1] # Use low of the trend bar as SL

            if True: # Always generate signal if conditions met
                return Signal(
                    symbol=self.symbol,
                    timestamp=df.index[-1].to_pydatetime(),
                    action="BUY",
                    signal_type="Bullish Trend Bar",
                    entry_price=entry_price,
                    stop_loss=sl_for_calc,
                    reason="Uptrend and Bullish Trend Bar"
                )
        elif market_state == 'uptrend' and is_bullish_pin_bar:
            entry_price = df['Close'].iloc[-1]
            sl_for_calc = df['Low'].iloc[-1] # Use low of the pin bar as SL

            if True: # Always generate signal if conditions met
                return Signal(
                    symbol=self.symbol,
                    timestamp=df.index[-1].to_pydatetime(),
                    action="BUY",
                    signal_type="Bullish Pin Bar",
                    entry_price=entry_price,
                    stop_loss=sl_for_calc,
                    reason="Uptrend and Bullish Pin Bar"
                )

        # --- 卖出/平仓逻辑 ---
        elif current_position_size > 0: # 只有当前持有多头仓位才考虑卖出
            # 市场状态从上涨转为下跌，且有持仓，则考虑平仓
            if market_state == 'downtrend' and self.data_history['market_state'].iloc[-2] == 'uptrend':
                return Signal(
                    symbol=self.symbol,
                    timestamp=df.index[-1].to_pydatetime(),
                    action="SELL",
                    signal_type="Trend Reversal (Uptrend to Downtrend)",
                    entry_price=df['Close'].iloc[-1], # Exit price
                    stop_loss=0.0, # Not applicable for exit signal
                    reason="Market trend reversed from uptrend to downtrend"
                )
            elif df['Close'].iloc[-1] < df['ema_20'].iloc[-1]:
                return Signal(
                    symbol=self.symbol,
                    timestamp=df.index[-1].to_pydatetime(),
                    action="SELL",
                    signal_type="Close below EMA20",
                    entry_price=df['Close'].iloc[-1], # Exit price
                    stop_loss=0.0, # Not applicable for exit signal
                    reason="Close below EMA20"
                )
        elif current_position_size > 0 and market_state == 'downtrend' and is_bearish_pin_bar:
            # Sell signal to close existing long position
            return Signal(
                symbol=self.symbol,
                timestamp=df.index[-1].to_pydatetime(),
                action="SELL",
                signal_type="Bearish Pin Bar",
                entry_price=df['Close'].iloc[-1], # Exit price
                stop_loss=0.0, # Not applicable for exit signal
                reason="Downtrend and Bearish Pin Bar"
            )
        
        return None
