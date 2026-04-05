"""
通用缓存服务 V14.0（升级版）
V14变更: 自动使用Redis缓存适配器，支持降级为内存缓存

原有接口完全兼容，无需修改调用方代码。
"""
import logging

logger = logging.getLogger(__name__)

# V14: 使用新的Redis缓存适配器
from business_common.redis_cache_service import (
    CacheService,
    cache_get,
    cache_set,
    cache_delete,
    cache_clear,
)

DEFAULT_TTL = 300  # 保持兼容

# 兼容性：保留原有便捷方法（已从redis_cache_service导入）
__all__ = ['CacheService', 'cache_get', 'cache_set', 'cache_delete', 'cache_clear', 'DEFAULT_TTL']
