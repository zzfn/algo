from backtesting import Strategy

from src.analysis.price_action_pipeline import PriceActionPipeline
from src.risk.position_sizer import calculate_position_size


class BacktestAdapter(Strategy):
    """
    极简的适配器，作为策略 Pipeline 和 backtesting.py 框架的桥梁。
    - init: 初始化策略"黑盒" (Pipeline)。
    - next: 将数据传递给Pipeline，获取信号，然后执行交易。
    """
    # 为满足 backtesting.py 框架要求，在此处声明参数。
    # 实际值将在运行时由 bt.run() 从配置文件中动态注入并覆盖。
    risk_per_trade = 0.02
    n_bars_for_trend = 10

    def init(self):
        """
        初始化核心决策 Pipeline。
        """
        self.pipeline = PriceActionPipeline(n_bars_for_trend=self.n_bars_for_trend)

    def next(self):
        """
        调用 Pipeline 获取决策，并执行交易。
        """
        # 直接将 self.data.df (包含OHLCV的原始数据) 传递给 pipeline
        signal, stop_loss_price = self.pipeline.generate_signal(
            data=self.data.df,
            is_position_open=bool(self.position)
        )

        if signal == 'BUY' and not self.position:
            entry_price = self.data.Close[-1]

            size = calculate_position_size(
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                risk_per_trade=self.risk_per_trade
            )
            if size > 0:
                self.buy(size=size, sl=stop_loss_price)

        elif signal == 'SELL' and self.position:
            self.position.close()
