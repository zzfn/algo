import pandas as pd
from src.risk.position_sizer import calculate_position_size

class PriceActionPipeline:
    """
    一个事件驱动、有状态的策略核心。
    它接收单根K线，维护自己的历史数据，并返回要交易的数量。
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
        Processes a new bar and generates the quantity to trade.
        """
        # Append the new bar to the internal data buffer
        if isinstance(new_bar, pd.Series):
            new_bar_df = pd.DataFrame([new_bar], index=[new_bar.name])
        else:
            new_bar_df = new_bar 

        self.data_buffer = pd.concat([self.data_buffer, new_bar_df])

        # Now, all calculations are performed on self.data_buffer
        df = self.data_buffer 

        # Ensure enough data for calculations
        if len(df) < self.ema_slope_lookback + 2:
            return 0.0, None # No operation if not enough data

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

        # --- 4. 决策逻辑 (返回要交易的数量) ---
        shares_to_trade = 0.0 # 默认不操作
        stop_loss_price = None

        # --- 买入/加仓逻辑 ---
        if market_state == 'uptrend' and is_bullish_engulfing:
            entry_price = df['Close'].iloc[-1]
            sl_for_calc = df['Low'].iloc[-1]
            
            calculated_size = calculate_position_size(
                entry_price=entry_price,
                stop_loss_price=sl_for_calc,
                risk_per_trade=risk_per_trade
            )
            
            if calculated_size > 0: 
                # 如果目标数量大于当前持仓，则计算差额进行买入
                if calculated_size > current_position_size:
                    shares_to_trade = calculated_size - current_position_size
                    stop_loss_price = sl_for_calc

        # --- 卖出/平仓逻辑 ---
        elif current_position_size > 0: # 只有当前持有多头仓位才考虑卖出
            if df['Close'].iloc[-1] < df['ema_20'].iloc[-1]:
                shares_to_trade = -current_position_size # 卖出所有当前持仓
                stop_loss_price = None
        
        return shares_to_trade, stop_loss_price
