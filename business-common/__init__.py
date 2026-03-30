"""
公共模块导出
统一导出所有公共功能，简化导入
"""

# 数据库模块
from . import db
from . import config

# 认证模块
from . import auth

# 工具模块
from . import utils

# 错误处理模块
from .error_handler import handle_errors, register_error_handlers

# 审计日志模块
from .audit_log import log_action, get_audit_logs, CREATE_AUDIT_LOG_SQL

# 限流模块
from .rate_limiter import rate_limit, get_limit

# 装饰器模块
from .decorators import (
    require_admin,
    require_staff,
    require_login,
    with_data_scope,
    add_scope_filter,
    log_api_call,
    validate_json,
    catch_errors
)

__all__ = [
    # 数据库
    'db',
    'config',
    # 认证
    'auth',
    # 工具
    'utils',
    # 错误处理
    'handle_errors',
    'register_error_handlers',
    # 审计日志
    'log_action',
    'get_audit_logs',
    'CREATE_AUDIT_LOG_SQL',
    # 限流
    'rate_limit',
    'get_limit',
    # 装饰器
    'require_admin',
    'require_staff',
    'require_login',
    'with_data_scope',
    'add_scope_filter',
    'log_api_call',
    'validate_json',
    'catch_errors',
]
