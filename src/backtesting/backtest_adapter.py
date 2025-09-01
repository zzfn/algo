import talib
from backtesting import Strategy

from src.analysis.price_action_pipeline import PriceActionPipeline


class BacktestAdapter(Strategy):
    """
    适配器，作为策略 Pipeline 和 backtesting.py 框架的桥梁。
    """
    # 为满足 backtesting.py 框架要求，在此处声明参数。
    risk_per_trade = 0.02
    n_bars_for_trend = 10

    def init(self):
        """
        1. 初始化核心决策 Pipeline。
        2. **仅为绘图目的**，定义一个指标，让 plotting 函数可以显示它。
           这个指标不参与任何交易决策。
        """
        self.pipeline = PriceActionPipeline(n_bars_for_trend=self.n_bars_for_trend)

        # Define indicator for plotting purposes only
        self.ema20_plot = self.I(talib.EMA, self.data.Close, timeperiod=20, name="EMA20")

    def next(self):
        """
        调用 Pipeline 获取决策，并执行交易。
        """
        # 获取当前仓位大小 (0.0 表示空仓，正数表示多头，负数表示空头)
        current_position_size = self.position.size if self.position else 0.0

        # 调用 Pipeline 获取目标仓位和止损价
        target_shares, sl_price = self.pipeline.generate_signal(
            data=self.data.df,
            current_position_size=current_position_size,
            risk_per_trade=self.risk_per_trade # 将风险参数传递给 Pipeline
        )

        # --- 根据目标仓位执行交易 (手动调用 buy/sell/close) ---
        # 策略只发出开多和平多的信号
        if target_shares > 0 and current_position_size == 0: # 目标是开多仓，且当前空仓
            self.buy(size=target_shares, sl=sl_price)
        elif target_shares == 0 and current_position_size > 0: # 目标是平多仓，且当前持有多仓
            self.position.close()
        # 其他情况 (如目标是保持当前仓位，或目标与当前仓位不符但未发出明确开平仓信号)，则不操作。