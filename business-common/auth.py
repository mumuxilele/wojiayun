"""
用户认证模块 - 带缓存版本
优化：对Token验证结果进行内存缓存（TTL=60s），大幅减少对认证服务的HTTP请求次数
"""
import urllib.request
import urllib.parse
import json
import time
import logging
from .config import USER_SERVICE_URL, USER_SERVICE_URL_CLOUD, STAFF_SERVICE_URL_CLOUD

logger = logging.getLogger(__name__)

# ============ Token 缓存 ============
# 格式: { token: {'data': user_dict, 'expire': timestamp} }
_token_cache = {}
TOKEN_CACHE_TTL = 60  # 缓存有效期（秒）


def _cache_get(token):
    """从缓存读取Token验证结果"""
    entry = _token_cache.get(token)
    if entry and time.time() < entry['expire']:
        return entry['data']
    # 过期则清除
    if entry:
        del _token_cache[token]
    return None


def _cache_set(token, user_data):
    """写入Token缓存"""
    _token_cache[token] = {
        'data': user_data,
        'expire': time.time() + TOKEN_CACHE_TTL
    }
    # 简单防止内存膨胀：超过1000条时清理最旧的20%
    if len(_token_cache) > 1000:
        sorted_keys = sorted(_token_cache.keys(), key=lambda k: _token_cache[k]['expire'])
        for k in sorted_keys[:200]:
            del _token_cache[k]


def _fetch_user(url_base, token, isdev):
    """向认证服务发起HTTP请求验证Token"""
    try:
        url = f"{url_base}?access_token={urllib.parse.quote(token)}&isdev={isdev}"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('success') and data.get('data'):
                u = data['data']
                return {
                    'user_id': u.get('userId') or u.get('id'),
                    'user_name': u.get('userName') or u.get('empName'),
                    'phone': u.get('userPhone') or u.get('empPhone'),
                    'emp_id': u.get('empId'),
                    'staff_id': u.get('staffId'),
                    'ec_id': u.get('ecId'),
                    'project_id': u.get('projectId'),
                    'is_staff': bool(u.get('empId') or u.get('staffId')),
                    'raw_data': u
                }
    except Exception as e:
        logger.warning(f'Token验证请求失败 [{url_base}]: {e}')
    return None


def verify_user(token, isdev='0', use_cloud=False):
    """
    验证用户Token并获取用户信息
    - 优先读缓存，缓存未命中才发HTTP请求
    - 支持本地/云端自动回退
    """
    if not token:
        return None

    cache_key = f"user:{token}:{isdev}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # 选择服务URL列表
    if use_cloud:
        urls_to_try = [USER_SERVICE_URL_CLOUD, USER_SERVICE_URL]
    else:
        urls_to_try = [USER_SERVICE_URL, USER_SERVICE_URL_CLOUD]

    for url_base in urls_to_try:
        user = _fetch_user(url_base, token, isdev)
        if user:
            _cache_set(cache_key, user)
            return user

    return None


def verify_staff(token, isdev='0'):
    """
    验证员工身份 - 使用员工端云端服务
    - 员工必须有 empId 或 staffId
    """
    if not token:
        return None

    cache_key = f"staff:{token}:{isdev}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    urls_to_try = [
        STAFF_SERVICE_URL_CLOUD,
        USER_SERVICE_URL_CLOUD,
        USER_SERVICE_URL
    ]

    for url_base in urls_to_try:
        user = _fetch_user(url_base, token, isdev)
        if user and (user.get('is_staff') or user.get('raw_data', {}).get('empName')):
            _cache_set(cache_key, user)
            return user

    return None


def invalidate_token(token):
    """手动使某个Token缓存失效（登出时调用）"""
    for prefix in ('user:', 'staff:'):
        for isdev in ('0', '1'):
            key = f"{prefix}{token}:{isdev}"
            _token_cache.pop(key, None)
