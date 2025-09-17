"""日志工具"""

from logbook import Logger, StreamHandler
from colorama import init, Fore, Back, Style
import sys

# 初始化colorama以支持跨平台彩色输出
init()


class ColoredStreamHandler(StreamHandler):
    """支持彩色输出的StreamHandler"""

    # 日志级别颜色映射
    LEVEL_COLORS = {
        'TRACE': Fore.CYAN,
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
    }

    # 模块前缀颜色映射
    MODULE_COLORS = {
        'STRATEGY': Fore.MAGENTA,
        'EXECUTION': Fore.CYAN,
        'MONITOR': Fore.BLUE,
        'DATA': Fore.YELLOW,
        'ENGINE': Fore.GREEN,
    }

    def format(self, record):
        """格式化日志记录，添加颜色"""
        # 先用父类格式化获得基础格式
        formatted = super().format(record)

        # 获取级别颜色
        level_color = self.LEVEL_COLORS.get(record.level_name, '')

        # 获取模块颜色
        module_color = ''
        if hasattr(record, 'channel') and record.channel:
            # 从channel中提取模块名 (如 AlgoTrading.STRATEGY -> STRATEGY)
            parts = record.channel.split('.')
            if len(parts) > 1:
                module_name = parts[-1]
                module_color = self.MODULE_COLORS.get(module_name, Fore.WHITE)

        # 对已格式化的字符串进行颜色替换
        if level_color:
            # 替换级别名为彩色版本
            colored_level = f"{level_color}{record.level_name}{Style.RESET_ALL}"
            formatted = formatted.replace(record.level_name, colored_level, 1)

        if module_color and hasattr(record, 'channel'):
            # 替换频道名为彩色版本
            colored_channel = f"{module_color}{record.channel}{Style.RESET_ALL}"
            formatted = formatted.replace(record.channel, colored_channel, 1)

        # 添加时间的灰色显示（如果格式中包含时间）
        import re
        # 匹配时间格式 (如 2024-01-01 12:34:56 或 12:34:56)
        time_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|\d{2}:\d{2}:\d{2})'
        formatted = re.sub(time_pattern, f"{Style.DIM}\\1{Style.RESET_ALL}", formatted)

        return formatted


def setup_logging(level='INFO', module_prefix: str = None, use_colors: bool = True) -> Logger:
    """
    设置日志配置并返回logger实例

    Args:
        level: 日志级别
        module_prefix: 模块前缀
        use_colors: 是否使用彩色输出
    """
    if use_colors:
        handler = ColoredStreamHandler(sys.stdout, level=level)
    else:
        handler = StreamHandler(sys.stdout, level=level)

    handler.push_application()
    logger_name = f'AlgoTrading.{module_prefix}' if module_prefix else 'AlgoTrading'
    return Logger(logger_name)