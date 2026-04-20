"""
Service 基类
提供统一的业务逻辑处理模板
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseService:
    """服务基类"""
    
    SERVICE_NAME: str = 'BaseService'
    
    def __init__(self):
        """初始化服务"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"[{self.SERVICE_NAME}] Service initialized")
    
    @staticmethod
    def success(data: Any = None, msg: str = '操作成功') -> Dict[str, Any]:
        """返回成功响应"""
        return {
            'success': True,
            'msg': msg,
            'data': data
        }
    
    @staticmethod
    def error(msg: str = '操作失败', code: int = None) -> Dict[str, Any]:
        """返回错误响应"""
        result = {
            'success': False,
            'msg': msg
        }
        if code is not None:
            result['code'] = code
        return result
    
    @staticmethod
    def now() -> datetime:
        """获取当前时间"""
        return datetime.now()
    
    @staticmethod
    def now_str() -> str:
        """获取当前时间字符串"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
