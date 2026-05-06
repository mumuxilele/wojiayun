# service/base_service.py - 业务层基类
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from utils.log_util import logger


class BaseService:
    """业务服务基类：提供统一返回、事务管理"""
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def success(data: Optional[Any] = None, message: str = "操作成功") -> Dict:
        return {"code": 200, "message": message, "data": data or {}}

    @staticmethod
    def error(message: str = "操作失败", code: int = 500) -> Dict:
        return {"code": code, "message": message, "data": {}}

    def begin(self):
        """开始事务：已有活跃事务时使用savepoint嵌套，避免重复begin异常"""
        if self.db.in_transaction():
            self.db.begin_nested()
        else:
            self.db.begin()

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
        logger.error("事务已回滚", exc_info=True)
