"""
统一异常处理模块 V34.0
为服务层提供标准化的异常处理机制

使用方式：
  from exception_handler import try_except, ServiceError, error_context

  # 方式1: 装饰器
  @try_except(logger)
  def my_function():
      ...

  # 方式2: 上下文管理器
  with error_context('操作描述', logger):
      do_something()

  # 方式3: 直接使用
  try:
      risky_operation()
  except ServiceError as e:
      return {'success': False, 'msg': e.message, 'code': e.code}
  except Exception as e:
      handle_unknown_error(e, logger)
"""
import logging
import traceback
from functools import wraps
from typing import Optional, Callable, Any, Dict
from contextlib import contextmanager


class ServiceError(Exception):
    """
    业务服务异常基类

    Attributes:
        code: 错误码
        message: 错误信息
        details: 详细错误信息（可选）
    """
    DEFAULT_CODE = 'SERVICE_ERROR'

    def __init__(self, message: str, code: str = None, details: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.DEFAULT_CODE
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'success': False,
            'msg': self.message,
            'code': self.code,
            'details': self.details
        }

    def __str__(self):
        return f"[{self.code}] {self.message}"


class ValidationError(ServiceError):
    """参数验证错误"""
    DEFAULT_CODE = 'VALIDATION_ERROR'

    def __init__(self, message: str, field: str = None):
        super().__init__(message, code=self.DEFAULT_CODE)
        self.field = field


class NotFoundError(ServiceError):
    """资源不存在错误"""
    DEFAULT_CODE = 'NOT_FOUND'

    def __init__(self, resource: str, identifier: Any = None):
        msg = f"{resource}不存在"
        if identifier:
            msg += f": {identifier}"
        super().__init__(msg, code=self.DEFAULT_CODE)


class PermissionError(ServiceError):
    """权限错误"""
    DEFAULT_CODE = 'PERMISSION_DENIED'

    def __init__(self, message: str = '权限不足'):
        super().__init__(message, code=self.DEFAULT_CODE)


class DatabaseError(ServiceError):
    """数据库操作错误"""
    DEFAULT_CODE = 'DATABASE_ERROR'


class ExternalServiceError(ServiceError):
    """外部服务调用错误"""
    DEFAULT_CODE = 'EXTERNAL_SERVICE_ERROR'


# ============ 异常处理工具 ============

def handle_unknown_error(error: Exception, logger: logging.Logger,
                         context: str = None) -> Dict[str, Any]:
    """
    处理未知异常，记录详细日志但返回安全信息

    Args:
        error: 捕获的异常
        logger: 日志记录器
        context: 操作上下文描述

    Returns:
        dict: 标准错误响应
    """
    error_type = type(error).__name__
    error_msg = str(error)

    log_msg = f"[{error_type}]"
    if context:
        log_msg += f" {context}:"
    log_msg += f" {error_msg}"

    # 记录完整堆栈跟踪
    logger.error(f"{log_msg}\n{traceback.format_exc()}")

    # 返回安全的错误信息给前端
    return {
        'success': False,
        'msg': '操作失败，请稍后重试',
        'error_type': error_type  # 仅记录错误类型，不泄露详细信息
    }


def try_except(logger: logging.Logger,
               default_return: Any = None,
               context: str = None,
               raise_on_error: bool = False):
    """
    异常处理装饰器

    Args:
        logger: 日志记录器
        default_return: 默认返回值（失败时）
        context: 操作上下文描述
        raise_on_error: 是否抛出异常而非返回错误

    Usage:
        @try_except(logger, default_return={'success': False})
        def risky_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ServiceError as e:
                logger.warning(f"[业务异常] {func.__name__}: {e}")
                if raise_on_error:
                    raise
                return e.to_dict()
            except Exception as e:
                return handle_unknown_error(
                    e, logger,
                    context or func.__name__
                ) if default_return is not None else default_return
        return wrapper
    return decorator


@contextmanager
def error_context(context: str, logger: logging.Logger = None,
                  suppress_errors: bool = True):
    """
    异常处理上下文管理器

    Args:
        context: 操作描述
        logger: 日志记录器
        suppress_errors: 是否抑制异常（True时捕获并返回错误，False时向上抛出）

    Usage:
        with error_context('保存用户', logger):
            db.save(user)
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    try:
        yield
    except ServiceError as e:
        logger.warning(f"[业务异常] {context}: {e}")
        if not suppress_errors:
            raise
        yield {'success': False, 'msg': e.message, 'code': e.code}
    except Exception as e:
        result = handle_unknown_error(e, logger, context)
        if not suppress_errors:
            raise ServiceError(result['msg'], details=e)
        yield result


def safe_execute(func: Callable, *args,
                 logger: logging.Logger = None,
                 default: Any = None,
                 **kwargs) -> Any:
    """
    安全执行函数，捕获所有异常

    Args:
        func: 要执行的函数
        *args: 函数位置参数
        logger: 日志记录器
        default: 执行失败时的默认值
        **kwargs: 函数关键字参数

    Returns:
        函数执行结果或默认值
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    try:
        return func(*args, **kwargs)
    except ServiceError as e:
        logger.warning(f"[业务异常] {func.__name__}: {e}")
        return default
    except Exception as e:
        handle_unknown_error(e, logger, func.__name__)
        return default


# ============ 服务基类增强 ============

class SafeServiceMixin:
    """
    服务基类混入，提供标准化的异常处理能力

    Usage:
        class MyService(SafeServiceMixin):
            def __init__(self):
                self.logger = logging.getLogger(__name__)

            def safe_operation(self):
                with self.error_context('操作描述'):
                    # 业务逻辑
                    pass
    """

    @property
    def logger(self) -> logging.Logger:
        """获取日志记录器"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger

    @contextmanager
    def error_context(self, context: str, suppress: bool = True):
        """
        带上下文的异常处理

        Args:
            context: 操作描述
            suppress: 是否抑制异常
        """
        with error_context(context, self.logger, suppress) as result:
            yield result

    def try_call(self, func: Callable, *args, default: Any = None, **kwargs) -> Any:
        """安全调用函数"""
        return safe_execute(func, *args, logger=self.logger, default=default, **kwargs)
