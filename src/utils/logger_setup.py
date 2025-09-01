import sys
from loguru import logger

def setup_logging(config: dict):
    """
    根据配置设置全局 loguru 日志记录器 (仅控制台).
    """
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO').upper()

    # 移除默认的处理器，以便完全自定义
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.info("Logging system initialized (Console only).")