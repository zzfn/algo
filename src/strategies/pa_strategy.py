from backtesting import Strategy

class PriceActionStrategy(Strategy):
    """
    一个更合理的简单动量策略。
    - 逻辑1: 如果收盘价上涨且当前没有持仓，则买入。
    - 逻辑2: 如果收盘价下跌且当前有持仓，则卖出平仓。
    """
    def init(self):
        pass

    def next(self):
        # self.position 会告诉我们当前是否有持仓
        if self.data.Close[-1] > self.data.Close[-2] and not self.position:
            self.buy()
        
        elif self.data.Close[-1] < self.data.Close[-2] and self.position:
            self.position.close()