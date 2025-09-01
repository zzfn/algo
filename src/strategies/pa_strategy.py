from backtesting import Strategy
from src.risk.position_sizer import calculate_position_size
from src.analysis.price_action import analyze_price_action

class PriceActionStrategy(Strategy):
    risk_per_trade = 0.02

    def init(self):
        """
        在回测开始时，准备好所有分析数据。
        这里是适配层：将 backtesting.py 的大写列名数据转换为我们内部的小写标准。
        """
        # 1. 从 backtesting.py 获取数据 (大写列名)
        uppercase_df = self.data.df

        # 2. 创建副本并转换为我们内部的小写标准
        lowercase_df = uppercase_df.copy()
        lowercase_df.columns = [col.lower() for col in uppercase_df.columns]

        # 3. 使用我们标准化的数据调用分析函数
        self.analyzed_data = analyze_price_action(lowercase_df)

    def next(self):
        current_date = self.data.index[-1]
        try:
            current_analysis = self.analyzed_data.loc[current_date]
        except KeyError:
            return

        if not self.position:
            if current_analysis['signal'] == 'buy_pullback':
                entry_price = self.data.Close[-1]
                stop_loss_price = self.data.Low[-1]

                size = calculate_position_size(
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price,
                    risk_per_trade=self.risk_per_trade
                )
                if size > 0:
                    self.buy(size=size, sl=stop_loss_price)
        
        elif self.position.is_long:
            if self.data.Close[-1] < current_analysis['ema_20']:
                self.position.close()
