from typing import List, Optional
import pandas as pd

# 从我们定义的核心类型中导入Signal和TakeProfitTarget
from src.core.types import Signal, TakeProfitTarget

def analyze_data_and_generate_signals(df: pd.DataFrame, symbol: str) -> List[Signal]:
    """
    一个最简单的分析函数，用于生成交易信号。
    逻辑：如果当天的收盘价 > 前一天的收盘价，则产生一个买入信号。

    Args:
        df: 包含OHLCV数据的DataFrame。
        symbol: 正在分析的交易品种。

    Returns:
        一个包含所有产生信号的列表。如果没有信号，则返回空列表。
    """
    signals = []
    # 使用.iloc来安全地访问前一行
    for i in range(1, len(df)):
        previous_bar = df.iloc[i-1]
        current_bar = df.iloc[i]

        if current_bar['close'] > previous_bar['close']:
            # 创建一个简单的止盈目标
            tp_target = TakeProfitTarget(
                price=current_bar['close'] * 1.05, # 止盈5%
                portion=1.0 # 全部平仓
            )

            # 创建信号对象
            signal = Signal(
                symbol=symbol,
                timestamp=current_bar.name, # .name 属性是DataFrame的索引值
                action="BUY",
                signal_type="simple_close_higher",
                entry_price=current_bar['close'],
                stop_loss=current_bar['low'],
                take_profit_targets=[tp_target],
                reason=f"Close {current_bar['close']:.2f} > Previous Close {previous_bar['close']:.2f}"
            )
            signals.append(signal)
            
    return signals


