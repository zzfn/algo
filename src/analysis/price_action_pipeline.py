import pandas as pd

class PriceActionPipeline:
    """
    一个完全自给自足的策略"黑盒"。
    它接收原始OHLCV数据，内部完成指标计算和逻辑判断，并返回交易信号。
    """
    def __init__(self, n_bars_for_trend: int = 10):
        self.n_bars_for_trend = n_bars_for_trend

    def generate_signal(self, data: pd.DataFrame, is_position_open: bool) -> (str, float | None):
        """
        :param data: 原始的 pandas DataFrame，必须包含 'Open', 'High', 'Low', 'Close' 列。
        :param is_position_open: 当前是否持有仓位。
        :return: 一个元组 (signal, stop_loss_price)。
        """
        if len(data) < self.n_bars_for_trend or len(data) < 2:
            return 'HOLD', None

        # 为了不修改原始数据，创建一个副本进行计算
        df = data.copy()

        # --- 1. 内部计算指标 ---
        df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()

        # --- 2. 判断市场状态 ---
        recent_closes = df['Close'][-self.n_bars_for_trend:]
        recent_emas = df['ema_20'][-self.n_bars_for_trend:]

        is_uptrend = all(close > ema for close, ema in zip(recent_closes, recent_emas))
        is_downtrend = all(close < ema for close, ema in zip(recent_closes, recent_emas))

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

        # --- 4. 决策逻辑 ---
        if not is_position_open:
            if (market_state == 'uptrend' and
                df['Low'].iloc[-1] <= df['ema_20'].iloc[-1] and
                is_bullish_engulfing):
                
                stop_loss_price = df['Low'].iloc[-1]
                return 'BUY', stop_loss_price
        
        elif is_position_open:
            if df['Close'].iloc[-1] < df['ema_20'].iloc[-1]:
                return 'SELL', None
        
        return 'HOLD', None