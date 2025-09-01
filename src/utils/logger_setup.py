import sys
from loguru import logger

def setup_logging(config: dict):
    """
    根据配置设置全局 loguru 日志记录器。
    """
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO').upper()
    log_file = log_config.get('file', 'trading_log.log')

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

    # 添加文件输出
    if log_file:
        logger.add(
            log_file,
            level=log_level,
            rotation="10 MB",  # 每10MB轮换一个新文件
            retention="7 days", # 保留7天的日志
            enqueue=True,     # 使日志写入异步，防止阻塞
            backtrace=True,   # 记录完整的堆栈跟踪
            diagnose=True,    # 添加异常诊断信息
            format="{time} {level} {message}"
        )
    
    logger.info("Loguru logging system initialized.")
