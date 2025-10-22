"""策略配置管理"""

from dataclasses import dataclass
from typing import List
from alpaca.data.enums import DataFeed
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv
from utils.log import setup_logging


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str
    port: int
    password: str
    db: int


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

    # Redis配置
    redis: RedisConfig

    # 交易执行设置
    default_order_qty: int
    time_in_force: str

    @classmethod
    def create(cls, config_path: str = None) -> 'TradingConfig':
        """创建配置实例，自动加载所有配置"""
        # 加载环境变量
        load_dotenv()

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

        # 加载Redis配置
        redis_config = config_data.get('redis', {})
        redis = RedisConfig(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            password=redis_config.get('password', ''),
            db=redis_config.get('db', 0)
        )

        # 交易执行相关配置
        default_order_qty = int(os.getenv("ALPACA_DEFAULT_ORDER_QTY", "1"))
        time_in_force = "IOC"
        is_test = os.getenv("ALPACA_IS_TEST", "false").lower() == "true"

        return cls(
            symbols=symbols,
            api_key=api_key,
            secret_key=secret_key,
            is_test=is_test,
            data_feed=DataFeed.IEX,  # 默认数据源
            buffer_size=1000,  # 默认缓存大小
            redis=redis,
            default_order_qty=default_order_qty,
            time_in_force=time_in_force
        )
