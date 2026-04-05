#!/usr/bin/env python3
"""
Redis缓存适配层 V21.0
提供Redis缓存接口，兼容本地缓存
当Redis不可用时自动回退到内存缓存
"""
import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 尝试导入Redis，如果未安装则使用本地缓存
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class RedisCache:
    """
    Redis缓存适配器
    
    支持功能:
    - 自动连接重试
    - 连接池管理
    - 序列化/反序列化
    - 自动过期时间
    - 本地缓存降级
    """
    
    _pool = None
    _client = None
    _use_local = False
    
    def __init__(self):
        self._connect()
    
    def _connect(self):
        """建立Redis连接"""
        if not HAS_REDIS:
            logger.warning("Redis模块未安装，将使用本地内存缓存")
            self._use_local = True
            return
        
        # 从环境变量获取Redis配置
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', '6379'))
        redis_db = int(os.environ.get('REDIS_DB', '0'))
        redis_password = os.environ.get('REDIS_PASSWORD')
        
        try:
            # 创建连接池
            if RedisCache._pool is None:
                pool_config = {
                    'host': redis_host,
                    'port': redis_port,
                    'db': redis_db,
                    'decode_responses': True,
                    'socket_connect_timeout': 5,
                    'socket_timeout': 5,
                    'retry_on_timeout': True,
                    'max_connections': 20,
                }
                if redis_password:
                    pool_config['password'] = redis_password
                
                RedisCache._pool = redis.ConnectionPool(**pool_config)
            
            # 创建客户端
            if RedisCache._client is None:
                RedisCache._client = redis.Redis(connection_pool=RedisCache._pool)
                # 测试连接
                RedisCache._client.ping()
            
            logger.info(f"Redis连接成功: {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.warning(f"Redis连接失败，将使用本地内存缓存: {e}")
            self._use_local = True
            RedisCache._client = None
    
    def get(self, key):
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值或None
        """
        if self._use_local:
            return self._local_get(key)
        
        try:
            value = RedisCache._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis GET失败: {e}")
            return None
    
    def set(self, key, value, expire_seconds=300):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值（会被JSON序列化）
            expire_seconds: 过期时间（秒），默认5分钟
        
        Returns:
            是否成功
        """
        if self._use_local:
            return self._local_set(key, value, expire_seconds)
        
        try:
            serialized = json.dumps(value, default=str)
            RedisCache._client.setex(key, expire_seconds, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis SET失败: {e}")
            return False
    
    def delete(self, key):
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            是否成功
        """
        if self._use_local:
            return self._local_delete(key)
        
        try:
            RedisCache._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE失败: {e}")
            return False
    
    def exists(self, key):
        """检查键是否存在"""
        if self._use_local:
            return self._local_exists(key)
        
        try:
            return RedisCache._client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Redis EXISTS失败: {e}")
            return False
    
    def expire(self, key, seconds):
        """设置过期时间"""
        if self._use_local:
            return self._local_expire(key, seconds)
        
        try:
            return RedisCache._client.expire(key, seconds)
        except Exception as e:
            logger.warning(f"Redis EXPIRE失败: {e}")
            return False
    
    def ttl(self, key):
        """获取剩余生存时间"""
        if self._use_local:
            return self._local_ttl(key)
        
        try:
            return RedisCache._client.ttl(key)
        except Exception as e:
            logger.warning(f"Redis TTL失败: {e}")
            return -1
    
    def flush_pattern(self, pattern):
        """删除匹配模式的所有键"""
        if self._use_local:
            return self._local_flush_pattern(pattern)
        
        try:
            keys = RedisCache._client.keys(pattern)
            if keys:
                RedisCache._client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning(f"Redis FLUSH_PATTERN失败: {e}")
            return 0
    
    # ========== 本地内存缓存（降级方案）============
    _local_cache = {}
    _local_expiry = {}
    
    def _local_get(self, key):
        """本地缓存获取"""
        if key in RedisCache._local_cache:
            expiry = RedisCache._local_expiry.get(key)
            if expiry is None or expiry > datetime.now():
                return RedisCache._local_cache.get(key)
            else:
                # 已过期，清理
                self._local_delete(key)
        return None
    
    def _local_set(self, key, value, expire_seconds):
        """本地缓存设置"""
        RedisCache._local_cache[key] = value
        if expire_seconds > 0:
            RedisCache._local_expiry[key] = datetime.now() + timedelta(seconds=expire_seconds)
        else:
            RedisCache._local_expiry[key] = None
        return True
    
    def _local_delete(self, key):
        """本地缓存删除"""
        RedisCache._local_cache.pop(key, None)
        RedisCache._local_expiry.pop(key, None)
        return True
    
    def _local_exists(self, key):
        """本地缓存检查"""
        value = self._local_get(key)
        return value is not None
    
    def _local_expire(self, key, seconds):
        """本地缓存设置过期"""
        if key in RedisCache._local_cache:
            RedisCache._local_expiry[key] = datetime.now() + timedelta(seconds=seconds)
            return True
        return False
    
    def _local_ttl(self, key):
        """本地缓存TTL"""
        expiry = RedisCache._local_expiry.get(key)
        if expiry is None:
            return -1
        if expiry > datetime.now():
            return int((expiry - datetime.now()).total_seconds())
        self._local_delete(key)
        return -2
    
    def _local_flush_pattern(self, pattern):
        """本地缓存模式清理"""
        import fnmatch
        keys_to_delete = [k for k in RedisCache._local_cache.keys() 
                         if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_delete:
            self._local_delete(key)
        return len(keys_to_delete)


# 全局缓存实例
_cache = None

def get_cache():
    """获取缓存实例（单例）"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache

# 兼容原有API
def cache_get(key):
    """获取缓存（兼容原有API）"""
    return get_cache().get(key)

def cache_set(key, value, expire_seconds=300):
    """设置缓存（兼容原有API）"""
    return get_cache().set(key, value, expire_seconds)

def cache_delete(key):
    """删除缓存（兼容原有API）"""
    return get_cache().delete(key)

def cache_exists(key):
    """检查缓存存在（兼容原有API）"""
    return get_cache().exists(key)

def cache_clear_pattern(pattern):
    """清空匹配模式的缓存"""
    return get_cache().flush_pattern(pattern)
