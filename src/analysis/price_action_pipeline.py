import pandas as pd
from src.risk.position_sizer import calculate_position_size

class PriceActionPipeline:
    """
    一个事件驱动、有状态的策略核心。
    它接收单根K线，维护自己的历史数据，并返回目标仓位。
    """
    def __init__(self, symbol: str, n_bars_for_trend: int, ema_slope_lookback: int):
        self.symbol = symbol
        self.n_bars_for_trend = n_bars_for_trend
        self.ema_slope_lookback = ema_slope_lookback
        self.data_buffer = pd.DataFrame() # Internal data store for stateful processing

    def initialize_data(self, historical_data: pd.DataFrame):
        """
        Initializes the pipeline with historical data for warm-up.
        This method is called once at the beginning of the backtest.
        """
        self.data_buffer = historical_data.copy()

    def process_bar(self, 
                    new_bar: pd.Series, 
                    current_position_size: float, 
                    risk_per_trade: float
                   ) -> (float, float | None):
        """
        Processes a new bar and generates a target position.
        """
        # Append the new bar to the internal data buffer
        # Ensure new_bar is a DataFrame with a DatetimeIndex for concat
        if isinstance(new_bar, pd.Series):
            new_bar_df = pd.DataFrame([new_bar], index=[new_bar.name])
        else:
            new_bar_df = new_bar # Should already be a DataFrame if passed as such

        self.data_buffer = pd.concat([self.data_buffer, new_bar_df])

        # Now, all calculations are performed on self.data_buffer
        df = self.data_buffer # Use the internal buffer

        # Ensure enough data for calculations
        if len(df) < self.ema_slope_lookback + 2:
            return current_position_size, None 

        df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()

        # --- 2. 判断市场状态 (基于EMA斜率) ---
        is_uptrend = df['ema_20'].iloc[-1] > df['ema_20'].iloc[-1 - self.ema_slope_lookback]
        is_downtrend = df['ema_20'].iloc[-1] < df['ema_20'].iloc[-1 - self.ema_slope_lookback]

        market_state = 'range'
        if is_uptrend:
            market_state = 'uptrend'
        elif is_downtrend:
            market_state = 'downtrend'

        # --- 3. 判断K线形态 ---
        is_bullish_engulfing = (df['Close'].iloc[-1] > df['Open'].iloc[-1]) and \
                               (df['Close'].iloc[-2] < df['Open'].iloc[-2]) and \
                               (df['Close'].iloc[-1] > df['Open'].iloc[-2]) and \
                               (df['Open'].iloc[-1] < df['Close'].iloc[-2])

        # --- 4. 决策逻辑 (返回目标仓位) ---
        target_shares = current_position_size 
        stop_loss_price = None

        if current_position_size == 0:
            if market_state == 'uptrend' and is_bullish_engulfing:
                entry_price = df['Close'].iloc[-1]
                sl_for_calc = df['Low'].iloc[-1]
                
                calculated_size = calculate_position_size(
                    entry_price=entry_price,
                    stop_loss_price=sl_for_calc,
                    risk_per_trade=risk_per_trade
                )
                if calculated_size > 0:
                    target_shares = calculated_size
                    stop_loss_price = sl_for_calc

        elif current_position_size > 0:
            if df['Close'].iloc[-1] < df['ema_20'].iloc[-1]:
                target_shares = 0.0 
                stop_loss_price = None
        
        return target_shares, stop_loss_price
