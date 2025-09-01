import talib
from backtesting import Strategy
from src.risk.position_sizer import calculate_position_size

class PriceActionStrategy(Strategy):
    """
    一个事件驱动的、更真实的价格行为策略。
    所有分析都在 next() 方法中，逐根K线进行，以模拟实盘。
    """
    risk_per_trade = 0.02
    n_bars_for_trend = 10 # 定义趋势所需要的连续K线数

    def init(self):
        """
        在回测开始时，使用 self.I() '注册' 需要的指标。
        backtesting.py 会在后台高效地计算它们。
        """
        self.ema20 = self.I(talib.EMA, self.data.Close, timeperiod=20)

    def next(self):
        """
        在每个时间点（K线）被调用，执行分析和决策。
        """
        # --- 1. 判断市场状态 ---
        # 获取最近N条K线的收盘价和EMA值
        recent_closes = self.data.Close[-self.n_bars_for_trend:]
        recent_emas = self.ema20[-self.n_bars_for_trend:]
        
        is_uptrend = all(close > ema for close, ema in zip(recent_closes, recent_emas))
        is_downtrend = all(close < ema for close, ema in zip(recent_closes, recent_emas))
        
        market_state = 'range'
        if is_uptrend:
            market_state = 'uptrend'
        elif is_downtrend:
            market_state = 'downtrend'

        # --- 2. 判断K线形态 ---
        # 看涨吞没
        is_bullish_engulfing = (self.data.Close[-1] > self.data.Open[-1]) and \
                               (self.data.Close[-2] < self.data.Open[-2]) and \
                               (self.data.Close[-1] > self.data.Open[-2]) and \
                               (self.data.Open[-1] < self.data.Close[-2])

        # --- 3. 决策逻辑 ---
        # 如果当前没有持仓，则寻找买入机会
        if not self.position:
            # 信号: 在上升趋势中，回调至EMA并形成看涨吞没形态
            if (market_state == 'uptrend' and 
                self.data.Low[-1] <= self.ema20[-1] and
                is_bullish_engulfing):
                
                entry_price = self.data.Close[-1]
                stop_loss_price = self.data.Low[-1]

                size = calculate_position_size(
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price,
                    risk_per_trade=self.risk_per_trade
                )
                if size > 0:
                    self.buy(size=size, sl=stop_loss_price)
        
        # 如果有持仓，则寻找卖出机会
        elif self.position.is_long:
            if self.data.Close[-1] < self.ema20[-1]:
                self.position.close()