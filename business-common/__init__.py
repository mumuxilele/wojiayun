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

# 订单状态流转模块
from .order_status import OrderStatusTransition, OrderStatusValidator, OrderStatus

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

# V23.0: 统一错误码与响应构建器
from .response_builder import ErrorCode, ResponseBuilder, success_resp, error_resp, paginated_resp

# V24.0: 拼团服务
from .group_buy_service import GroupBuyService, group_buy

    # V14: WebSocket消息推送（延迟导入，避免强制依赖）
    # from .websocket_service import init_websocket, push_notification

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
    # 订单状态流转
    'OrderStatusTransition',
    'OrderStatusValidator',
    'OrderStatus',
    # 装饰器
    'require_admin',
    'require_staff',
    'require_login',
    'with_data_scope',
    'add_scope_filter',
    'log_api_call',
    'validate_json',
    'catch_errors',
    # V23.0: 统一错误码
    'ErrorCode',
    'ResponseBuilder',
    'success_resp',
    'error_resp',
    'paginated_resp',
    # V24.0: 拼团服务
    'GroupBuyService',
    'group_buy',
]
