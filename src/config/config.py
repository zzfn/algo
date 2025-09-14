"""策略配置管理"""

from dataclasses import dataclass
from alpaca.data.enums import DataFeed


@dataclass
class TradingConfig:
    """交易策略配置"""
    # API密钥
    api_key: str = ""
    secret_key: str = ""

    # 环境设置
    is_test: bool = False  # True为测试模式

    # 数据设置
    data_feed: DataFeed = DataFeed.IEX  # iex, sip
    buffer_size: int = 1000  # 数据缓存大小