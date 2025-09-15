"""Redis客户端工具"""

import redis
from typing import Optional, Any
from config.config import RedisConfig
from log import setup_logging

# 使用统一日志工具
logger = setup_logging()


class RedisClient:
    """Redis客户端封装"""

    def __init__(self, config: RedisConfig):
        """初始化Redis客户端"""
        self.config = config
        self._client: Optional[redis.Redis] = None
        logger.info(f"初始化Redis客户端: {config.host}:{config.port}, DB={config.db}")

    @property
    def client(self) -> redis.Redis:
        """获取Redis客户端连接"""
        if self._client is None:
            try:
                logger.info(f"正在连接Redis服务器: {self.config.host}:{self.config.port}")
                self._client = redis.Redis(
                    host=self.config.host,
                    port=self.config.port,
                    password=self.config.password,
                    db=self.config.db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # 测试连接
                self._client.ping()
                logger.info("✅ Redis连接建立成功")
            except Exception as e:
                logger.error(f"❌ Redis连接失败: {e}")
                raise
        return self._client

    def ping(self) -> bool:
        """测试连接"""
        try:
            result = self.client.ping()
            logger.debug("Redis ping测试成功")
            return result
        except Exception as e:
            logger.error(f"Redis ping测试失败: {e}")
            return False

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置键值"""
        try:
            result = self.client.set(key, value, ex=ex)
            logger.debug(f"设置键值成功: {key}")
            return result
        except Exception as e:
            logger.error(f"设置键值失败 {key}: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        """获取值"""
        try:
            value = self.client.get(key)
            logger.debug(f"获取键值: {key} = {value}")
            return value
        except Exception as e:
            logger.error(f"获取键值失败 {key}: {e}")
            return None

    def delete(self, key: str) -> bool:
        """删除键"""
        try:
            result = bool(self.client.delete(key))
            logger.debug(f"删除键: {key}, 结果: {result}")
            return result
        except Exception as e:
            logger.error(f"删除键失败 {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            result = bool(self.client.exists(key))
            logger.debug(f"检查键存在: {key} = {result}")
            return result
        except Exception as e:
            logger.error(f"检查键存在失败 {key}: {e}")
            return False

    def close(self):
        """关闭连接"""
        if self._client:
            logger.info("关闭Redis连接")
            self._client.close()
            self._client = None