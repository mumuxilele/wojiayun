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

# V32.0: 服务层架构升级
from .order_service import OrderService, order_service
from .member_service import MemberService, member_service
from .product_service import ProductService, product_service

# V33.0: 新增服务
from .invoice_service import InvoiceService, invoice_service
from .backup_service import BackupService, backup_service
from .task_queue_service import TaskQueueService, task_queue_service

# V29.0: 申请审批服务
from .application_service import ApplicationService

# V35.0: Redis缓存服务
from .redis_cache_v35 import RedisCache

# V34.0: 异常处理模块
from .exception_handler import (
    ServiceError,
    ValidationError,
    NotFoundError,
    PermissionError as ServicePermissionError,
    DatabaseError,
    ExternalServiceError,
    try_except,
    error_context,
    SafeServiceMixin
)
