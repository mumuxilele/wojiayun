"""
通用装饰器集合
提取重复逻辑，简化代码
"""
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def require_admin(f):
    """
    管理员认证装饰器
    验证用户是否为管理员
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import g, jsonify
        
        user = g.get('admin_user')
        if not user:
            return jsonify({'success': False, 'msg': '请先登录'}), 401
        
        # 检查是否为管理员（可根据业务逻辑调整）
        # if not user.get('is_admin', False):
        #     return jsonify({'success': False, 'msg': '需要管理员权限'}), 403
        
        return f(user, *args, **kwargs)
    return decorated


def require_staff(f):
    """
    员工认证装饰器
    验证用户是否为员工
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import g, jsonify
        
        user = g.get('staff_user')
        if not user:
            return jsonify({'success': False, 'msg': '请使用员工账号登录'}), 401
        
        # 检查是否为员工
        if not user.get('is_staff', False):
            return jsonify({'success': False, 'msg': '需要员工权限'}), 403
        
        return f(user, *args, **kwargs)
    return decorated


def require_login(f):
    """
    用户登录装饰器
    验证用户是否已登录
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import g, jsonify
        
        user = g.get('current_user')
        if not user:
            return jsonify({'success': False, 'msg': '请先登录'}), 401
        
        return f(user, *args, **kwargs)
    return decorated


def with_data_scope(f):
    """
    数据范围过滤装饰器
    自动为查询添加 ec_id 和 project_id 过滤
    
    使用示例:
        @with_data_scope
        def get_applications(user):
            ec_id, project_id = g.data_scope
            # 查询时自动应用数据范围
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import g
        
        # 从当前用户获取数据范围
        user = g.get('admin_user') or g.get('staff_user') or g.get('current_user')
        if not user:
            g.data_scope = (None, None)
        else:
            g.data_scope = (user.get('ec_id'), user.get('project_id'))
        
        return f(*args, **kwargs)
    return decorated


def add_scope_filter(where, params, table_alias='', user=None):
    """
    添加数据范围过滤条件
    
    参数:
        where: 原始WHERE条件
        params: 原始参数列表
        table_alias: 表别名（用于多表JOIN）
        user: 用户信息（如果不提供则从g获取）
    
    返回:
        (new_where, new_params)
    """
    from flask import g
    
    if not user:
        user = g.get('admin_user') or g.get('staff_user') or g.get('current_user')
    
    if not user:
        return where, params
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    prefix = table_alias + '.' if table_alias else ''
    
    if ec_id:
        where += f" AND {prefix}ec_id=%s"
        params.append(ec_id)
    
    if project_id:
        where += f" AND {prefix}project_id=%s"
        params.append(project_id)
    
    return where, params


def log_api_call(f):
    """
    API调用日志装饰器
    记录API调用信息
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request
        
        # 记录请求信息
        logger.info(f"[API调用] {request.method} {request.path} - IP:{request.remote_addr}")
        
        # 执行请求
        result = f(*args, **kwargs)
        
        # 记录响应状态
        if hasattr(result, 'status_code'):
            logger.debug(f"[API响应] {request.path} - 状态码:{result.status_code}")
        
        return result
    return decorated


def validate_json(*required_fields):
    """
    JSON参数验证装饰器
    
    参数:
        required_fields: 必填字段列表
    
    使用示例:
        @validate_json('app_type', 'title')
        def create_application():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import request, jsonify
            
            data = request.get_json() or {}
            
            # 检查必填字段
            missing = [field for field in required_fields if not data.get(field)]
            if missing:
                return jsonify({
                    'success': False,
                    'msg': f'缺少必要参数: {", ".join(missing)}'
                }), 400
            
            return f(*args, **kwargs)
        return decorated
    return decorator


def catch_errors(fallback_msg='操作失败，请稍后重试'):
    """
    错误捕获装饰器
    捕获未处理异常，返回友好提示
    
    参数:
        fallback_msg: 默认错误提示
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"[操作失败] {f.__name__}: {e}", exc_info=True)
            from flask import jsonify
            return jsonify({'success': False, 'msg': fallback_msg}), 500
    return decorated
