# Al Brooks 价格行为自动化交易系统

本项目致力于实现一个基于 Al Brooks 价格行为理论的自动化交易系统。系统旨在通过代码识别价格行为中的关键模式（如趋势、通道、盘整、关键K线），并据此执行交易决策。

## 系统架构 (System Architecture)

本系统采用模块化设计，分为以下几个核心组件，以便于开发、测试和维护。

### 1. 数据模块 (Data Module)
- **职责**: 负责从 Alpaca 获取、清洗和管理市场数据。
- **功能**:
    - 连接 Alpaca 的实时数据 API。
    - 从 Alpaca 下载历史数据用于回测。
    - 数据标准化，处理缺失数据和异常值。
    - 提供统一的数据接口供其他模块调用。

### 2. 分析与信号模块 (Analysis & Signal Module)
- **职责**: 系统的核心决策引擎。实现Al Brooks价格行为分析逻辑，并生成交易信号。
- **功能**:
    - **市场状态分析**: 识别当前是趋势市还是盘整市。
    - **K线与形态分析**: 识别信号K线、入场K线、趋势线、通道、楔形、三角形等。
    - **信号生成**: 根据价格行为理论，在满足特定条件时生成明确的买入 (Buy)、卖出 (Sell)、止损 (Stop-Loss) 和止盈 (Take-Profit) 信号。

### 3. 交易执行模块 (Execution Module)
- **职责**: 通过 Alpaca API 精确执行交易指令。
- **功能**:
    - 接收信号模块的交易指令。
    - 管理订单（下单、撤单、修改订单）。
    - 处理订单成交回报，更新持仓状态。
    - 错误处理与重试机制。

### 4. 风险与仓位管理模块 (Risk & Position Management Module)
- **职责**: 管理整体投资组合风险和单笔交易的仓位。
- **功能**:
    - 根据账户总资金和风险度（如2%原则）计算每笔交易的仓位大小。
    - 跟踪和管理当前所有持仓的风险暴露。
    - 实时更新账户净值、可用资金等。

### 5. 回测引擎 (Backtesting Engine)
- **职责**: 使用历史数据模拟交易，评估策略表现。
- **功能**:
    - 模拟真实的市场环境和交易执行。
    - 根据历史数据运行分析和信号模块。
    - 生成详细的性能报告，包括胜率、盈亏比、夏普比率、最大回撤等关键指标。

### 6. 主控与调度模块 (Main Control & Scheduling Module)
- **职责**: 作为系统的入口点，协调其他模块按预定逻辑运行。
- **功能**:
    - 初始化所有模块。
    - 在实时交易中，按固定的时间频率（如每个K线结束时）驱动整个流程。
    - 在回测中，按顺序遍历历史数据。

### 7. 配置与日志模块 (Configuration & Logging Module)
- **职责**: 管理系统配置并记录关键信息。
- **功能**:
    - **配置**: 通过 `.env` 文件管理API密钥，通过 `config.yaml` 管理交易品种、策略参数等。
    - **日志**: 记录系统运行状态、交易信号、订单执行情况和潜在错误，方便调试和监控。

## 技术栈 (暂定)
- **语言**: Python 3.11+
- **核心库**:
    - `pandas`: 数据处理与分析。
    - `numpy`: 数值计算。
    - `alpaca-py`: 用于连接 Alpaca API 进行数据获取和交易执行。

## 数据与接口标准

### 1. 核心数据格式 (K线)

为了保证系统各模块之间数据传递的一致性，我们定义所有核心市场数据（K线）都必须遵循以下 `pandas.DataFrame` 格式：

*   **索引 (Index)**:
    *   类型: `pandas.DatetimeIndex`
    *   要求: 必须是时区感知的（Timezone-aware），统一使用 **UTC** 时间。
*   **基础列 (Base Columns)**:
    *   `open`: `float64` - K线开盘价
    *   `high`: `float64` - K线最高价
    *   `low`: `float64` - K线最低价
    *   `close`: `float64` - K线收盘价
    *   `volume`: `float64` - K线成交量
*   **扩展列 (Extended Columns)**:
    *   分析模块会在此基础上添加技术指标和分析结果列。
    *   `ema_20`: `float64` - 20周期指数移动平均线，用于判断趋势。
    
    *   `is_swing_high`: `bool` - 是否为波段高点。
    *   `is_swing_low`: `bool` - 是否为波段低点。
    *   `bar_type`: `string` - K线类型（如 `bull_trend_bar`, `doji` 等）。
    *   `market_state`: `string` - 市场状态（如 `trending`, `ranging`）。

### 2. 模块输入输出 (I/O) 定义

#### a. 数据模块 (`data/alpaca_loader.py`)
*   **输入**:
    *   `symbol`: `str` - 交易品种，如 "SPY"。
    *   `start_date`: `datetime` - 数据开始时间。
    *   `end_date`: `datetime` - 数据结束时间。
    *   `timeframe`: `str` - K线周期，如 "1Day"。
*   **输出**:
    *   `pandas.DataFrame` - 遵循上述核心数据格式的K线数据。

#### b. 分析与信号模块 (`analysis/price_action.py`)
*   **输入**:
    *   `pandas.DataFrame` - K线数据。
*   **输出**:
    *   `Signal` 对象 (`src/core/types.py`) 或 `None`。

#### c. 风险与仓位管理模块 (`risk/position_sizer.py`)
*   **输入**:
    *   `Signal` 对象 - 来自分析模块的交易信号。
    *   `account_equity`: `float` - 当前账户总净值。
*   **输出**:
    *   `Order` 对象 (`src/core/types.py`) 或 `None`。

#### d. 交易执行模块 (`execution/alpaca_trader.py`)
*   **输入**:
    *   `Order` (`dict`) - 来自风险管理模块的订单指令。
*   **输出**:
    *   `dict` (订单确认 `Confirmation`)。
    *   **Confirmation 字典结构**:
        ```python
        {
            "order_id": "alpaca_order_id_12345",
            "symbol": "SPY",
            "status": "FILLED", # "SUBMITTED", "FILLED", "FAILED", etc.
            "filled_quantity": 65,
            "filled_avg_price": 152.48,
            "timestamp": "2023-10-27T11:30:00Z",
            "error_message": None # 如果失败，则包含错误信息
        }
        ```� - 来自风险管理模块的订单指令。
*   **输出**:
    *   `Confirmation` 对象 (`src/core/types.py`)。