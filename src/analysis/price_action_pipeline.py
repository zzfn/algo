import pandas as pd
from src.risk.position_sizer import calculate_position_size

class PriceActionPipeline:
    """
    一个完全自给自足的策略"黑盒"。
    它接收原始OHLCV数据，内部完成指标计算和逻辑判断，并返回交易信号。
    """
    def __init__(self, n_bars_for_trend: int = 10):
        self.n_bars_for_trend = n_bars_for_trend

    def generate_signal(self, data: pd.DataFrame, current_position_size: float, risk_per_trade: float) -> (float, float | None):
        """
        :param data: 原始的 pandas DataFrame，必须包含 'Open', 'High', 'Low', 'Close' 列。
        :param current_position_size: 当前持有的股票数量 (正数表示多头，负数表示空头，0表示空仓)。
        :param risk_per_trade: 每笔交易的风险敞口（占总资金的百分比）。
        :return: 一个元组 (target_shares, stop_loss_price)。
                 target_shares 是策略希望持有的股票数量。
                 stop_loss_price 是建议的止损价，仅在 BUY 信号时有效。
        """
        EMA_SLOPE_LOOKBACK = 5
        if len(data) < EMA_SLOPE_LOOKBACK + 2:
            return current_position_size, None # Return current position if not enough data

        df = data.copy()
        df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()

        # --- 2. 判断市场状态 ---
        is_uptrend = df['ema_20'].iloc[-1] > df['ema_20'].iloc[-1 - EMA_SLOPE_LOOKBACK]
        is_downtrend = df['ema_20'].iloc[-1] < df['ema_20'].iloc[-1 - EMA_SLOPE_LOOKBACK]

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
        target_shares = current_position_size # 默认保持当前仓位
        stop_loss_price = None

        # 买入逻辑：如果当前空仓，且满足买入条件
        if current_position_size == 0:
            if market_state == 'uptrend' and is_bullish_engulfing:
                entry_price = df['Close'].iloc[-1]
                sl_for_calc = df['Low'].iloc[-1]
                
                # 计算要买入的股票数量
                calculated_size = calculate_position_size(
                    entry_price=entry_price,
                    stop_loss_price=sl_for_calc,
                    risk_per_trade=risk_per_trade
                )
                if calculated_size > 0:
                    target_shares = calculated_size
                    stop_loss_price = sl_for_calc

        # 卖出逻辑：如果当前持有多头仓位，且满足卖出条件
        elif current_position_size > 0:
            if df['Close'].iloc[-1] < df['ema_20'].iloc[-1]:
                target_shares = 0.0 # 目标是平仓
                stop_loss_price = None
        
        return target_shares, stop_loss_price