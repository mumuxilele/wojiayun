"""
Redis缓存适配器 V14.0
支持: Redis缓存（推荐）/ 内存缓存（降级）
通过环境变量 REDIS_URL 自动切换：
  - 有 REDIS_URL → 使用Redis
  - 无 REDIS_URL → 降级为进程内内存缓存（兼容原有行为）

接口与原 CacheService 100% 兼容：
  cache_get(key)
  cache_set(key, value, ttl=300)
  cache_delete(key)
  cache_clear(pattern=None)
"""
import os
import json
import time
import logging
import threading

logger = logging.getLogger(__name__)

# ============ 配置 ============
REDIS_URL = os.environ.get('REDIS_URL', '')  # e.g. redis://localhost:6379/0
DEFAULT_TTL = 300  # 默认5分钟

# ============ Redis后端 ============

class RedisBackend:
    """Redis缓存后端"""

    def __init__(self, url):
        try:
            import redis
            self._client = redis.from_url(url, decode_responses=True)
            # 测试连接
            self._client.ping()
            self._available = True
            logger.info(f"Redis缓存已连接: {url.split('@')[-1] if '@' in url else url}")
        except Exception as e:
            logger.warning(f"Redis连接失败，降级为内存缓存: {e}")
            self._available = False
            self._client = None

    @property
    def available(self):
        return self._available

    def get(self, key):
        if not self._available:
            return None
        try:
            val = self._client.get(key)
            if val is not None:
                return json.loads(val)
            return None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    def set(self, key, value, ttl=None):
        if not self._available:
            return
        try:
            ttl = ttl if ttl is not None else DEFAULT_TTL
            self._client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    def delete(self, key):
        if not self._available:
            return
        try:
            self._client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")

    def clear(self, pattern=None):
        if not self._available:
            return
        try:
            if pattern is None:
                self._client.flushdb()
            else:
                keys = self._client.keys(pattern + '*')
                if keys:
                    self._client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")

    def get_stats(self):
        if not self._available:
            return {'total': 0, 'expired': 0, 'active': 0}
        try:
            info = self._client.info()
            return {
                'total': self._client.dbsize(),
                'expired': 0,  # Redis自动清理过期key
                'active': self._client.dbsize()
            }
        except Exception:
            return {'total': 0, 'expired': 0, 'active': 0}

    def publish(self, channel, message):
        """发布消息到频道（用于WebSocket推送）"""
        if not self._available:
            return
        try:
            self._client.publish(channel, json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Redis publish error: {e}")


# ============ 内存缓存后端（降级方案，与原CacheService一致）============

class MemoryBackend:
    """内存缓存后端（进程内，多进程部署时缓存不共享）"""

    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()
        self._max_items = 1000

    def get(self, key):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry['expire_at'] < time.time():
                del self._store[key]
                return None
            return entry['value']

    def set(self, key, value, ttl=None):
        ttl = ttl if ttl is not None else DEFAULT_TTL
        with self._lock:
            self._store[key] = {
                'value': value,
                'expire_at': time.time() + ttl,
                'created_at': time.time()
            }
            if len(self._store) > self._max_items:
                self._cleanup()

    def delete(self, key):
        with self._lock:
            self._store.pop(key, None)

    def clear(self, pattern=None):
        with self._lock:
            if pattern is None:
                self._store.clear()
            else:
                keys_to_delete = [k for k in self._store.keys() if k.startswith(pattern)]
                for k in keys_to_delete:
                    del self._store[k]

    def get_stats(self):
        with self._lock:
            now = time.time()
            expired = sum(1 for v in self._store.values() if v['expire_at'] < now)
            return {
                'total': len(self._store),
                'expired': expired,
                'active': len(self._store) - expired
            }

    def _cleanup(self):
        """清理过期和最老的缓存"""
        now = time.time()
        expired_keys = [k for k, v in self._store.items() if v['expire_at'] < now]
        for k in expired_keys:
            del self._store[k]
        if len(self._store) > self._max_items:
            sorted_keys = sorted(self._store.keys(), key=lambda k: self._store[k]['created_at'])
            for k in sorted_keys[:len(self._store) - 800]:
                del self._store[k]

    def publish(self, channel, message):
        """内存后端不支持发布/订阅"""
        pass


# ============ 统一缓存服务（自动选择后端）============

# 尝试创建Redis后端
_redis_backend = None
if REDIS_URL:
    _redis_backend = RedisBackend(REDIS_URL)

# 选择后端：Redis可用则用Redis，否则用内存
if _redis_backend and _redis_backend.available:
    _backend = _redis_backend
    _backend_type = 'redis'
else:
    _backend = MemoryBackend()
    _backend_type = 'memory'

logger.info(f"缓存后端: {_backend_type}")


class CacheService:
    """统一缓存服务（自动选择Redis或内存后端）"""

    @staticmethod
    def get(key):
        return _backend.get(key)

    @staticmethod
    def set(key, value, ttl=None):
        _backend.set(key, value, ttl)

    @staticmethod
    def delete(key):
        _backend.delete(key)

    @staticmethod
    def clear(pattern=None):
        _backend.clear(pattern)

    @staticmethod
    def _cleanup():
        if hasattr(_backend, '_cleanup'):
            _backend._cleanup()

    @staticmethod
    def get_stats():
        stats = _backend.get_stats()
        stats['backend'] = _backend_type
        return stats

    @staticmethod
    def get_backend_type():
        return _backend_type

    @staticmethod
    def publish(channel, message):
        """发布消息（用于实时推送）"""
        _backend.publish(channel, message)

    @staticmethod
    def get_redis_client():
        """获取原生Redis客户端（高级用法）"""
        if _backend_type == 'redis' and _redis_backend and _redis_backend._available:
            return _redis_backend._client
        return None


# ============ 便捷方法（保持原有接口不变）============

def cache_get(key):
    return CacheService.get(key)

def cache_set(key, value, ttl=None):
    return CacheService.set(key, value, ttl)

def cache_delete(key):
    return CacheService.delete(key)

def cache_clear(pattern=None):
    return CacheService.clear(pattern)
