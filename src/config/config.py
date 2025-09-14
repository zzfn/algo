"""策略配置管理"""

from dataclasses import dataclass
from typing import List
from alpaca.data.enums import DataFeed
import yaml
import os
from pathlib import Path


@dataclass
class TradingConfig:
    """交易策略配置"""
    # 股票代码列表
    symbols: List[str]

    # API密钥
    api_key: str
    secret_key: str

    # 环境设置
    is_test: bool

    # 数据设置
    data_feed: DataFeed
    buffer_size: int

    @classmethod
    def create(cls, config_path: str = None) -> 'TradingConfig':
        """创建配置实例，自动加载所有配置"""
        if config_path is None:
            # 默认配置文件路径 - 当前工作目录下的 config.yaml
            config_path = Path.cwd() / "config.yaml"

        # 从YAML文件加载symbols
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        symbols = config_data.get('symbols', [])

        # 从环境变量加载API密钥
        api_key = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_SECRET_KEY", "")

        return cls(
            symbols=symbols,
            api_key=api_key,
            secret_key=secret_key,
            is_test=True,  # 默认测试模式
            data_feed=DataFeed.IEX,  # 默认数据源
            buffer_size=1000  # 默认缓存大小
        )