"""
V35.0 Redis缓存服务完整实现
提供分布式缓存、会话管理、分布式限流等功能

功能清单:
- 通用缓存操作 (get/set/delete)
- 会话管理 (session)
- 分布式限流 (rate_limit)
- Token存储与验证
- 缓存预热

依赖:
- redis: Redis客户端
"""

import json
import logging
import os
import time
from typing import Any, Optional, Dict, List
from functools import wraps

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
DEFAULT_REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
DEFAULT_REDIS_DB = int(os.environ.get('REDIS_DB', 0))
DEFAULT_REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
DEFAULT_CACHE_TTL = 3600  # 默认缓存1小时


class RedisCache:
    """
    Redis缓存服务 - V35.0完整实现
    
    单例模式，确保全局只有一个Redis连接池
    """
    
    _instance = None
    _client = None
    _connected = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """建立Redis连接"""
        try:
            import redis
            self._client = redis.Redis(
                host=DEFAULT_REDIS_HOST,
                port=DEFAULT_REDIS_PORT,
                db=DEFAULT_REDIS_DB,
                password=DEFAULT_REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # 测试连接
            self._client.ping()
            self._connected = True
            logger.info(f"[RedisCache] 连接成功: {DEFAULT_REDIS_HOST}:{DEFAULT_REDIS_PORT}")
        except ImportError:
            logger.warning("[RedisCache] redis模块未安装，降级到内存缓存")
            self._client = None
            self._connected = False
        except Exception as e:
            logger.warning(f"[RedisCache] Redis连接失败: {e}，降级到内存缓存")
            self._client = None
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """检查Redis是否已连接"""
        return self._connected and self._client is not None
    
    # ============ 基础缓存操作 ============
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存key
        
        Returns:
            缓存值，不存在返回None
        """
        if not self.is_connected:
            return None
        
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError:
            return value
        except Exception as e:
            logger.error(f"[RedisCache] GET失败: {key}, {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存key
            value: 缓存值
            ttl: 过期时间（秒）
        
        Returns:
            bool: 是否成功
        """
        if not self.is_connected:
            return False
        
        try:
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, ensure_ascii=False)
            self._client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"[RedisCache] SET失败: {key}, {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存key
        
        Returns:
            bool: 是否成功
        """
        if not self.is_connected:
            return False
        
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"[RedisCache] DELETE失败: {key}, {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查key是否存在"""
        if not self.is_connected:
            return False
        
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error(f"[RedisCache] EXISTS失败: {key}, {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """设置key过期时间"""
        if not self.is_connected:
            return False
        
        try:
            return bool(self._client.expire(key, ttl))
        except Exception as e:
            logger.error(f"[RedisCache] EXPIRE失败: {key}, {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """获取key剩余生存时间"""
        if not self.is_connected:
            return -1
        
        try:
            return self._client.ttl(key)
        except Exception as e:
            logger.error(f"[RedisCache] TTL失败: {key}, {e}")
            return -1
    
    # ============ 批量操作 ============
    
    def mget(self, keys: List[str]) -> List[Any]:
        """批量获取"""
        if not self.is_connected:
            return [None] * len(keys)
        
        try:
            values = self._client.mget(keys)
            result = []
            for v in values:
                if v:
                    try:
                        result.append(json.loads(v))
                    except json.JSONDecodeError:
                        result.append(v)
                else:
                    result.append(None)
            return result
        except Exception as e:
            logger.error(f"[RedisCache] MGET失败: {e}")
            return [None] * len(keys)
    
    def mset(self, mapping: Dict[str, Any], ttl: int = DEFAULT_CACHE_TTL) -> bool:
        """批量设置"""
        if not self.is_connected:
            return False
        
        try:
            pipe = self._client.pipeline()
            for key, value in mapping.items():
                if isinstance(value, (dict, list, tuple)):
                    value = json.dumps(value, ensure_ascii=False)
                pipe.setex(key, ttl, value)
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"[RedisCache] MSET失败: {e}")
            return False
    
    def mdel(self, keys: List[str]) -> int:
        """批量删除"""
        if not self.is_connected:
            return 0
        
        try:
            return self._client.delete(*keys)
        except Exception as e:
            logger.error(f"[RedisCache] MDEL失败: {e}")
            return 0
    
    # ============ 会话管理 ============
    
    def set_session(self, session_id: str, data: Dict, ttl: int = 86400) -> bool:
        """
        存储会话
        
        Args:
            session_id: 会话ID
            data: 会话数据
            ttl: 过期时间（秒），默认24小时
        
        Returns:
            bool: 是否成功
        """
        return self.set(f"session:{session_id}", data, ttl)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话数据，不存在返回None
        """
        return self.get(f"session:{session_id}")
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            bool: 是否成功
        """
        return self.delete(f"session:{session_id}")
    
    def refresh_session(self, session_id: str, ttl: int = 86400) -> bool:
        """
        刷新会话过期时间
        
        Args:
            session_id: 会话ID
            ttl: 新的过期时间
        
        Returns:
            bool: 是否成功
        """
        return self.expire(f"session:{session_id}", ttl)
    
    # ============ Token管理 ============
    
    def set_token(self, token_id: str, user_id: int, ttl: int = 7200) -> bool:
        """
        存储Token
        
        Args:
            token_id: Token唯一标识（jti）
            user_id: 用户ID
            ttl: 过期时间（秒），默认2小时
        
        Returns:
            bool: 是否成功
        """
        return self.set(f"token:{token_id}", {'user_id': user_id}, ttl)
    
    def get_token(self, token_id: str) -> Optional[Dict]:
        """
        获取Token信息
        
        Args:
            token_id: Token唯一标识
        
        Returns:
            Token信息，不存在返回None
        """
        return self.get(f"token:{token_id}")
    
    def delete_token(self, token_id: str) -> bool:
        """
        删除Token（主动失效）
        
        Args:
            token_id: Token唯一标识
        
        Returns:
            bool: 是否成功
        """
        return self.delete(f"token:{token_id}")
    
    def token_exists(self, token_id: str) -> bool:
        """检查Token是否存在"""
        return self.exists(f"token:{token_id}")
    
    # ============ 分布式限流 ============
    
    def rate_limit(self, key: str, limit: int, window: int) -> Dict[str, Any]:
        """
        滑动窗口限流
        
        Args:
            key: 限流key
            limit: 时间窗口内允许的最大请求数
            window: 时间窗口（秒）
        
        Returns:
            Dict: {
                "allowed": bool,    # 是否允许通过
                "remaining": int,   # 剩余请求数
                "reset_at": int     # 窗口重置时间戳
            }
        """
        if not self.is_connected:
            # Redis不可用时，放行请求
            return {'allowed': True, 'remaining': limit, 'reset_at': int(time.time()) + window}
        
        try:
            now = time.time()
            window_start = now - window
            rate_key = f"rate:{key}"
            
            # 使用Redis事务保证原子性
            pipe = self._client.pipeline()
            
            # 删除窗口外的记录
            pipe.zremrangebyscore(rate_key, 0, window_start)
            
            # 获取当前请求数
            pipe.zcard(rate_key)
            
            # 添加当前请求
            pipe.zadd(rate_key, {str(now): now})
            
            # 设置过期时间
            pipe.expire(rate_key, window)
            
            results = pipe.execute()
            current_count = results[1]  # zcard结果
            
            if current_count >= limit:
                # 获取窗口内最早的请求时间
                oldest = self._client.zrange(rate_key, 0, 0, withscores=True)
                reset_at = int(oldest[0][1] + window) if oldest else int(now + window)
                
                return {
                    'allowed': False,
                    'remaining': 0,
                    'reset_at': reset_at
                }
            
            return {
                'allowed': True,
                'remaining': limit - current_count - 1,
                'reset_at': int(now + window)
            }
            
        except Exception as e:
            logger.error(f"[RedisCache] 限流检查失败: {e}")
            return {'allowed': True, 'remaining': limit, 'reset_at': int(time.time()) + window}
    
    def rate_limit_simple(self, key: str, limit: int, window: int) -> bool:
        """
        简单限流（固定窗口算法）
        
        Args:
            key: 限流key
            limit: 限制次数
            window: 时间窗口（秒）
        
        Returns:
            bool: True=允许, False=被限流
        """
        result = self.rate_limit(key, limit, window)
        return result['allowed']
    
    # ============ 分布式锁 ============
    
    def acquire_lock(self, lock_name: str, ttl: int = 10, 
                    owner: str = None) -> Optional[str]:
        """
        获取分布式锁
        
        Args:
            lock_name: 锁名称
            ttl: 锁过期时间（秒）
            owner: 锁持有者标识，默认使用进程ID
        
        Returns:
            str: 锁标识（用于释放锁），获取失败返回None
        """
        if not self.is_connected:
            return None
        
        try:
            import uuid
            owner = owner or str(uuid.uuid4())
            lock_key = f"lock:{lock_name}"
            
            # 使用SET NX EX保证原子性
            acquired = self._client.set(lock_key, owner, nx=True, ex=ttl)
            
            if acquired:
                logger.debug(f"[RedisCache] 获取锁成功: {lock_name}")
                return owner
            else:
                logger.debug(f"[RedisCache] 获取锁失败: {lock_name}，已被占用")
                return None
                
        except Exception as e:
            logger.error(f"[RedisCache] 获取锁异常: {e}")
            return None
    
    def release_lock(self, lock_name: str, owner: str) -> bool:
        """
        释放分布式锁
        
        Args:
            lock_name: 锁名称
            owner: 锁持有者标识
        
        Returns:
            bool: 是否成功释放
        """
        if not self.is_connected:
            return False
        
        try:
            lock_key = f"lock:{lock_name}"
            
            # 使用Lua脚本保证原子性：只有持有者才能释放
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = self._client.eval(lua_script, 1, lock_key, owner)
            
            if result:
                logger.debug(f"[RedisCache] 释放锁成功: {lock_name}")
                return True
            else:
                logger.debug(f"[RedisCache] 释放锁失败: {lock_name}，不是持有者")
                return False
                
        except Exception as e:
            logger.error(f"[RedisCache] 释放锁异常: {e}")
            return False
    
    # ============ 缓存预热 ============
    
    def cache_warmup(self, items: List[Dict], key_func, value_func, ttl: int = 3600) -> int:
        """
        缓存预热
        
        Args:
            items: 数据列表
            key_func: 生成缓存key的函数
            value_func: 生成缓存值的函数
            ttl: 过期时间
        
        Returns:
            int: 预热的数据条数
        """
        if not self.is_connected:
            return 0
        
        count = 0
        try:
            for item in items:
                key = key_func(item)
                value = value_func(item)
                if key and self.set(key, value, ttl):
                    count += 1
            
            logger.info(f"[RedisCache] 缓存预热完成: {count}/{len(items)}")
            return count
            
        except Exception as e:
            logger.error(f"[RedisCache] 缓存预热失败: {e}")
            return count
    
    # ============ 统计信息 ============
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Redis统计信息"""
        if not self.is_connected:
            return {'connected': False}
        
        try:
            info = self._client.info()
            return {
                'connected': True,
                'version': info.get('redis_version', 'unknown'),
                'uptime_seconds': info.get('uptime_in_seconds', 0),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0'),
                'total_commands': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
            }
        except Exception as e:
            logger.error(f"[RedisCache] 获取统计信息失败: {e}")
            return {'connected': False, 'error': str(e)}


# 便捷函数
_cache = None

def get_cache() -> RedisCache:
    """获取Redis缓存单例"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache

def cache_get(key: str) -> Optional[Any]:
    """快捷获取缓存"""
    return get_cache().get(key)

def cache_set(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """快捷设置缓存"""
    return get_cache().set(key, value, ttl)

def cache_delete(key: str) -> bool:
    """快捷删除缓存"""
    return get_cache().delete(key)

def cache_exists(key: str) -> bool:
    """快捷检查缓存是否存在"""
    return get_cache().exists(key)

def rate_limit(key: str, limit: int, window: int) -> Dict[str, Any]:
    """快捷限流"""
    return get_cache().rate_limit(key, limit, window)

# 缓存装饰器
def cached(key_prefix: str, ttl: int = DEFAULT_CACHE_TTL, 
          key_func: callable = None):
    """
    缓存装饰器
    
    Args:
        key_prefix: 缓存key前缀
        ttl: 过期时间
        key_func: 生成key的函数，接收函数参数
    
    Usage:
        @cached('user', ttl=3600)
        def get_user(user_id):
            return db.get_one(...)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # 生成缓存key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"[CacheHit] {cache_key}")
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            if result is not None:
                cache.set(cache_key, result, ttl)
                logger.debug(f"[CacheSet] {cache_key}, ttl={ttl}")
            
            return result
        return wrapper
    return decorator
