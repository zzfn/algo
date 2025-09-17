"""日志工具"""

from logbook import Logger, StreamHandler
import sys


def setup_logging(level='INFO', module_prefix: str = None) -> Logger:
    """设置日志配置并返回logger实例"""
    StreamHandler(sys.stdout, level=level).push_application()
    logger_name = f'AlgoTrading.{module_prefix}' if module_prefix else 'AlgoTrading'
    return Logger(logger_name)