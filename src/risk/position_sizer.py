from loguru import logger

def calculate_position_size(
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
