"""
API版本管理中间件 V32.0
功能:
  - API版本检测与路由
  - 版本兼容处理
  - 废弃API预警
  - 请求日志记录
"""
import logging
import time
import json
from functools import wraps
from flask import request, g, jsonify

logger = logging.getLogger(__name__)


class APIVersionMiddleware:
    """API版本管理中间件"""

    # 当前支持的API版本
    SUPPORTED_VERSIONS = ['v1', 'v2', 'v3']
    CURRENT_VERSION = 'v3'
    DEPRECATED_VERSIONS = ['v1']  # 即将废弃的版本
    OBSOLETE_VERSIONS = []  # 已废弃的版本

    # 版本兼容性映射
    VERSION_BREAKING_CHANGES = {
        'v3': {
            'field_renames': {
                'product_name': 'name',
                'shop_id': 'store_id',
            },
            'response_format': 'new'
        },
        'v2': {
            'field_renames': {},
            'response_format': 'legacy'
        }
    }

    @classmethod
    def get_version(cls):
        """获取请求的API版本"""
        path = request.path
        for version in cls.SUPPORTED_VERSIONS:
            if f'/api/{version}/' in path or f'/api/{version}' == path:
                return version

        version_header = request.headers.get('X-API-Version')
        if version_header:
            version_header = version_header.lower().strip()
            if version_header in cls.SUPPORTED_VERSIONS:
                return version_header

        version_param = request.args.get('api_version')
        if version_param:
            version_param = version_param.lower().strip()
            if version_param in cls.SUPPORTED_VERSIONS:
                return version_param

        return cls.CURRENT_VERSION

    @classmethod
    def should_upgrade(cls, version):
        """检查是否需要升级版本"""
        if version in cls.OBSOLETE_VERSIONS:
            return 'obsolete'
        elif version in cls.DEPRECATED_VERSIONS:
            return 'deprecated'
        elif version not in cls.SUPPORTED_VERSIONS:
            return 'unsupported'
        return 'ok'

    @classmethod
    def transform_request(cls, data, from_version, to_version):
        """转换请求数据以兼容旧版本"""
        if from_version == to_version:
            return data
        if from_version in cls.VERSION_BREAKING_CHANGES:
            renames = cls.VERSION_BREAKING_CHANGES[from_version].get('field_renames', {})
            for old_name, new_name in renames.items():
                if old_name in data:
                    data[new_name] = data.pop(old_name)
        return data

    @classmethod
    def transform_response(cls, data, from_version, to_version):
        """转换响应数据以兼容旧版本"""
        if from_version == to_version:
            return data
        if to_version in cls.VERSION_BREAKING_CHANGES:
            renames = cls.VERSION_BREAKING_CHANGES[to_version].get('field_renames', {})
            data = cls._rename_fields_recursive(data, renames)
        return data

    @classmethod
    def _rename_fields_recursive(cls, obj, renames):
        """递归转换字段名"""
        if isinstance(obj, dict):
            return {
                renames.get(k, k): cls._rename_fields_recursive(v, renames)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [cls._rename_fields_recursive(item, renames) for item in obj]
        return obj


def require_api_version(version=None):
    """装饰器：要求特定API版本"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            request_version = APIVersionMiddleware.get_version()
            status = APIVersionMiddleware.should_upgrade(request_version)

            if status == 'obsolete':
                return jsonify({
                    'success': False,
                    'msg': f'API版本 {request_version} 已废弃，请升级到最新版本',
                    'error_code': 'API_VERSION_OBSOLETE',
                    'current_version': APIVersionMiddleware.CURRENT_VERSION
                }), 410

            if status == 'unsupported':
                return jsonify({
                    'success': False,
                    'msg': f'不支持的API版本: {request_version}',
                    'error_code': 'API_VERSION_UNSUPPORTED',
                    'supported_versions': APIVersionMiddleware.SUPPORTED_VERSIONS
                }), 400

            if version and request_version != version:
                return jsonify({
                    'success': False,
                    'msg': f'此接口需要API版本 {version}，当前版本: {request_version}',
                    'error_code': 'API_VERSION_MISMATCH'
                }), 400

            g.api_version = request_version
            return f(*args, **kwargs)
        return decorated
    return decorator


def deprecated_api(replacement=None, remove_version=None):
    """装饰器：标记废弃API"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-API-Deprecated'] = 'true'
                response.headers['X-API-Replacement'] = replacement or ''
            return response
        return decorated
    return decorator


class RequestLogger:
    """请求日志记录器"""

    @classmethod
    def log_request(cls, response_data=None, duration_ms=0):
        """记录API请求日志"""
        try:
            log_data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'method': request.method,
                'path': request.path,
                'version': getattr(g, 'api_version', 'unknown'),
                'user_id': getattr(g, 'user_id', None),
                'ip': request.remote_addr,
                'duration_ms': duration_ms,
            }

            if duration_ms > 1000:
                logger.warning(f"慢请求: {json.dumps(log_data)}")
            else:
                logger.info(f"API请求: {json.dumps(log_data, ensure_ascii=False)}")

        except Exception as e:
            logger.error(f"记录请求日志失败: {e}")


def setup_versioning(app):
    """设置API版本管理"""
    @app.before_request
    def before_request():
        g.start_time = time.time()
        g.api_version = APIVersionMiddleware.get_version()
        g.version_status = APIVersionMiddleware.should_upgrade(g.api_version)

    @app.after_request
    def after_request(response):
        duration_ms = 0
        if hasattr(g, 'start_time'):
            duration_ms = int((time.time() - g.start_time) * 1000)

        response.headers['X-API-Version'] = getattr(g, 'api_version', APIVersionMiddleware.CURRENT_VERSION)
        response.headers['X-Response-Time'] = f'{duration_ms}ms'

        if getattr(g, 'version_status', 'ok') == 'deprecated':
            response.headers['X-API-Deprecated'] = 'true'
            response.headers['Warning'] = f'API version {g.api_version} is deprecated'

        RequestLogger.log_request(duration_ms=duration_ms)
        return response
