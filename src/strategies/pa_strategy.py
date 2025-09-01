from backtesting import Strategy
from src.risk.position_sizer import calculate_position_size

class PriceActionStrategy(Strategy):
    """
    一个集成了风险管理的简单动量策略。
    - 逻辑1: 如果收盘价上涨且当前没有持仓，则根据风险比例计算仓位并买入。
    - 逻辑2: 如果收盘价下跌且当前有持仓，则卖出平仓。
    """
    # --- 可配置的策略参数 ---
    risk_per_trade = 0.02  # 默认为2%的风险

    def init(self):
        pass

    def next(self):
        # 如果当前没有持仓，则寻找买入机会
        if not self.position:
            if self.data.Close[-1] > self.data.Close[-2]:
                
                # --- 集成风险管理 ---
                # 1. 定义入场和止损价格
                entry_price = self.data.Close[-1]
                stop_loss_price = self.data.Low[-1] # 以信号K线的最低点为止损

                # 2. 调用函数计算仓位大小
                size = calculate_position_size(
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price,
                    risk_per_trade=self.risk_per_trade
                )

                # 3. 如果计算出的仓位有效，则下单
                if size > 0:
                    self.buy(size=size, sl=stop_loss_price)
        
        # 如果当前有持仓，则根据条件寻找卖出机会
        elif self.data.Close[-1] < self.data.Close[-2]:
            self.position.close()
