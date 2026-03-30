"""
请求限流模块
使用Flask-Limiter限制API请求频率，防止滥用
"""
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# 简单的内存限流器（生产环境建议使用Redis）
_rate_limit_store = {}

class InMemoryRateLimiter:
    """内存限流器（用于开发环境）"""
    
    def __init__(self):
        self.store = {}  # {key: [timestamp1, timestamp2, ...]}
    
    def check(self, key, limit, window_seconds=60):
        """
        检查是否超过限流
        
        参数:
            key: 限流键（如用户ID或IP）
            limit: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口（秒）
        
        返回:
            (is_allowed, remaining, reset_time)
        """
        import time
        now = time.time()
        window_start = now - window_seconds
        
        # 获取该键的历史记录
        if key not in self.store:
            self.store[key] = []
        
        # 清理过期记录
        self.store[key] = [t for t in self.store[key] if t > window_start]
        
        # 检查是否超限
        current_count = len(self.store[key])
        if current_count >= limit:
            # 计算重置时间（最早的请求过期时间）
            reset_time = int(self.store[key][0] + window_seconds)
            return False, 0, reset_time
        
        # 记录本次请求
        self.store[key].append(now)
        remaining = limit - current_count - 1
        reset_time = int(now + window_seconds)
        return True, remaining, reset_time
    
    def reset(self, key):
        """重置指定键的限流记录"""
        if key in self.store:
            del self.store[key]


# 全局限流器实例
_limiter = InMemoryRateLimiter()


def rate_limit(limit=60, window_seconds=60, key_func=None):
    """
    请求限流装饰器
    
    参数:
        limit: 时间窗口内允许的最大请求数
        window_seconds: 时间窗口（秒）
        key_func: 限流键函数，接收request返回key（默认使用remote_addr）
    
    使用示例:
        @app.route('/api/test')
        @rate_limit(limit=10, window_seconds=60)  # 每分钟最多10次
        def test():
            return 'success'
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import request, jsonify
            
            # 获取限流键
            if key_func:
                key = key_func(request)
            else:
                # 默认使用IP地址作为限流键
                key = request.remote_addr or '127.0.0.1'
            
            # 检查限流
            allowed, remaining, reset_time = _limiter.check(key, limit, window_seconds)
            
            if not allowed:
                logger.warning(f"[限流触发] IP:{key}, 路由:{request.path}")
                # 设置响应头
                response = jsonify({
                    'success': False,
                    'msg': f'请求过于频繁，请{window_seconds}秒后重试'
                })
                response.status_code = 429
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(reset_time)
                return response
            
            # 执行请求
            result = f(*args, **kwargs)
            
            # 添加限流响应头
            if hasattr(result, 'headers'):
                result.headers['X-RateLimit-Limit'] = str(limit)
                result.headers['X-RateLimit-Remaining'] = str(remaining)
                result.headers['X-RateLimit-Reset'] = str(reset_time)
            
            return result
        return decorated
    return decorator


# 预定义的限流配置
LIMITS = {
    'strict': {'limit': 10, 'window': 60},       # 严格限流：10次/分钟
    'normal': {'limit': 60, 'window': 60},      # 普通限流：60次/分钟
    'loose': {'limit': 300, 'window': 60},     # 宽松限流：300次/分钟
    'api': {'limit': 30, 'window': 60},         # API限流：30次/分钟
}


def get_limit(name='normal'):
    """获取预定义的限流配置"""
    return LIMITS.get(name, LIMITS['normal'])


# 便捷装饰器
strict_limit = lambda f: rate_limit(**LIMITS['strict'])(f)
normal_limit = lambda f: rate_limit(**LIMITS['normal'])(f)
loose_limit = lambda f: rate_limit(**LIMITS['loose'])(f)
api_limit = lambda f: rate_limit(**LIMITS['api'])(f)


def clear_expired():
    """清理过期的限流记录"""
    _limiter.store.clear()
    logger.info("限流记录已清理")
