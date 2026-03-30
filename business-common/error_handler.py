"""
统一错误处理中间件
作用：捕获所有未处理异常，返回统一格式的错误响应，避免敏感信息泄露
"""
import logging
import traceback
from functools import wraps
from flask import jsonify

logger = logging.getLogger(__name__)


def handle_errors(f):
    """
    统一错误处理装饰器
    自动捕获异常并返回标准格式
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            # 参数验证错误
            logger.warning(f"[参数验证失败] {f.__name__}: {str(e)}")
            return jsonify({'success': False, 'msg': str(e)}), 400
        except PermissionError as e:
            # 权限错误
            logger.warning(f"[权限拒绝] {f.__name__}: {str(e)}")
            return jsonify({'success': False, 'msg': '权限不足'}), 403
        except KeyError as e:
            # 缺少必要参数
            logger.warning(f"[缺少参数] {f.__name__}: {str(e)}")
            return jsonify({'success': False, 'msg': f'缺少必要参数: {str(e)}'}), 400
        except Exception as e:
            # 未知错误，记录详细堆栈但不泄露给前端
            logger.error(f"[系统错误] {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            return jsonify({'success': False, 'msg': '系统错误，请稍后重试'}), 500
    return decorated


def register_error_handlers(app):
    """
    注册全局错误处理器
    在app.py中调用: register_error_handlers(app)
    """
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'success': False, 'msg': '请求参数错误'}), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'success': False, 'msg': '未授权，请先登录'}), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'success': False, 'msg': '权限不足'}), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'success': False, 'msg': '请求的资源不存在'}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'success': False, 'msg': '请求方法不支持'}), 405
    
    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"[服务器错误] {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'msg': '服务器内部错误'}), 500
    
    logger.info("全局错误处理器已注册")
