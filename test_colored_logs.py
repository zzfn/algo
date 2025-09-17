#!/usr/bin/env python3
"""测试彩色日志输出"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.log import setup_logging

def test_colored_logs():
    """测试不同模块的彩色日志输出"""

    print("=== 测试彩色日志输出 ===\n")

    # 测试不同模块的日志
    modules = ['STRATEGY', 'EXECUTION', 'MONITOR', 'DATA', 'ENGINE']

    for module in modules:
        logger = setup_logging(level='DEBUG', module_prefix=module)

        print(f"--- {module} 模块日志测试 ---")
        logger.debug(f"{module}: 这是调试信息")
        logger.info(f"{module}: 这是普通信息")
        logger.warning(f"{module}: 这是警告信息")
        logger.error(f"{module}: 这是错误信息")
        logger.critical(f"{module}: 这是严重错误信息")
        print()

    # 测试无颜色模式
    print("--- 无颜色模式测试 ---")
    plain_logger = setup_logging(level='INFO', module_prefix='TEST', use_colors=False)
    plain_logger.info("这是无颜色的日志输出")
    plain_logger.error("这是无颜色的错误信息")

    print("\n=== 彩色日志测试完成 ===")

if __name__ == "__main__":
    test_colored_logs()