"""日志工具"""

from logbook import Logger, StreamHandler
import sys


def setup_logging(level='INFO') -> Logger:
    """设置日志配置并返回logger实例"""
    StreamHandler(sys.stdout, level=level).push_application()
    return Logger('AlgoTrading')