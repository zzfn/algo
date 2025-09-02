from loguru import logger
from src.core.types import Signal

def _calculate_target_position_size_from_risk(
    entry_price: float,
    stop_loss_price: float,
    risk_per_trade: float
) -> float:
    """
    根据固定分数风险模型计算仓位大小。

    Args:
        entry_price: 入场价格。
        stop_loss_price: 止损价格。
        risk_per_trade: 您愿意为这笔交易承担的风险占总资产的比例 (e.g., 0.02 for 2%).

    Returns:
        适用于 backtesting.py 的仓位大小（0.0到1.0之间的浮点数）。
        如果参数无效，则返回0.0。
    """
    if entry_price <= 0 or stop_loss_price <= 0:
        logger.warning("Entry price and stop loss price must be positive.")
        return 0.0

    # 计算每股风险
    risk_per_share = entry_price - stop_loss_price
    
    if risk_per_share <= 0:
        logger.warning(f"Stop loss ({stop_loss_price}) must be below entry price ({entry_price}) for a long trade.")
        return 0.0

    # 这是核心公式：
    # 仓位比例 = (单次交易风险比例 / 每股风险比例)
    # 其中，每股风险比例 = (入场价 - 止损价) / 入场价
    
    risk_per_share_fraction = risk_per_share / entry_price
    
    position_size_fraction = risk_per_trade / risk_per_share_fraction
    
    # 确保仓位大小不超过100%
    final_size = min(position_size_fraction, 1.0)
    
    logger.debug(
        f"Calculated position size: {final_size:.4f} "
        f"(Entry: {entry_price}, SL: {stop_loss_price}, Risk: {risk_per_trade*100}%)"
    )
    
    return final_size


def calculate_position_size(
    signal: Signal,
    current_position_size: float,
    current_profit_loss: float, # This parameter is not used in the current logic, but kept as per user's request
    risk_per_trade: float
) -> float:
    """
    根据交易信号、当前持仓和风险参数计算目标仓位大小。

    Args:
        signal: 交易信号对象。
        current_position_size: 当前持有的仓位大小。
        current_profit_loss: 当前仓位的盈亏。
        risk_per_trade: 每笔交易的风险比例。

    Returns:
        新的目标仓位大小。
    """
    if signal is None:
        logger.debug("No signal received, returning 0.0 (no action).")
        return 0.0

    if signal.action == "BUY":
        # Calculate target position size based on the signal's entry and stop loss
        target_size = _calculate_target_position_size_from_risk(
            entry_price=signal.entry_price,
            stop_loss_price=signal.stop_loss,
            risk_per_trade=risk_per_trade
        )
        logger.debug(f"BUY signal received. Target size: {target_size:.4f}")
        # If target_size is greater than current_position_size, return the difference to buy
        if target_size > current_position_size:
            return target_size - current_position_size
        else:
            return 0.0 # No action needed (already at or above target)
    elif signal.action == "SELL":
        # For a SELL signal, return a negative value to indicate selling the current position
        logger.debug(f"SELL signal received. Returning -{current_position_size:.4f} to close position.")
        return -current_position_size
    else:
        logger.warning(f"Unknown signal action: {signal.action}. Returning 0.0 (no action).")
        return 0.0


if __name__ == '__main__':
    # --- 测试用例 ---
    from loguru import logger
    logger.add(lambda msg: print(msg)) # 在独立运行时添加一个简单的打印处理器
    
    equity = 100000
    risk_pct = 0.02 # 承担2%的风险
    
    print("\n--- Test Case 1: Standard ---")
    entry = 150.0
    stop_loss = 145.0
    # 预期: 每股风险$5 (3.33%)。总风险$2000。可买400股，总值$60000。仓位比例 60000/100000 = 0.6
    size = calculate_position_size(entry, stop_loss, risk_pct)
    print(f"Calculated Size: {size:.2f}") # Expected: 0.60
    print(f"Position Value: ${equity * size:,.2f}")

    print("\n--- Test Case 2: Tight Stop ---")
    entry = 150.0
    stop_loss = 149.0
    # 预期: 每股风险$1 (0.66%)。总风险$2000。可买2000股，总值$300000。超过总资产，应限制为100%。
    size = calculate_position_size(entry, stop_loss, risk_pct)
    print(f"Calculated Size: {size:.2f}") # Expected: 1.00 (capped)
    print(f"Position Value: ${equity * size:,.2f}")

    print("\n--- Test Case 3: Invalid Stop ---")
    entry = 150.0
    stop_loss = 151.0
    size = calculate_position_size(entry, stop_loss, risk_pct)
    print(f"Calculated Size: {size:.2f}") # Expected: 0.00
