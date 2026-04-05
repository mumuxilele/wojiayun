"""
V29.0 后端分层架构 - 服务层基类
提供统一的业务逻辑封装

设计原则:
  - 每个服务类对应一个业务领域
  - 统一的CRUD操作模板
  - 事务管理和异常处理
  - 服务间依赖注入
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    服务基类

    所有业务服务继承此类，获得:
    - 统一的日志记录
    - 统一的时间戳管理
    - 服务健康检查支持
    """

    # 服务名称，由子类覆盖
    SERVICE_NAME = 'BaseService'

    def __init__(self):
        self._start_time = datetime.now()
        logger.info(f"[{self.SERVICE_NAME}] Service initialized")

    @property
    def uptime(self) -> float:
        """获取服务运行时间（秒）"""
        return (datetime.now() - self._start_time).total_seconds()

    def health_check(self) -> Dict[str, Any]:
        """服务健康检查，子类可覆盖"""
        return {
            'service': self.SERVICE_NAME,
            'status': 'healthy',
            'uptime': self.uptime
        }

    @staticmethod
    def now() -> datetime:
        """获取当前时间"""
        return datetime.now()

    @staticmethod
    def now_str() -> str:
        """获取当前时间字符串"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class CRUDService(BaseService):
    """
    通用CRUD服务基类

    提供标准的增删改查操作模板
    """

    def __init__(self, table_name: str, primary_key: str = 'id'):
        super().__init__()
        self.table_name = table_name
        self.primary_key = primary_key

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建记录"""
        from business_common import db

        fields = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        values = list(data.values())

        sql = f"INSERT INTO {self.table_name} ({fields}) VALUES ({placeholders})"

        try:
            db.execute(sql, values)
            logger.info(f"[{self.SERVICE_NAME}] Created record in {self.table_name}")
            return {'success': True, 'msg': '创建成功'}
        except Exception as e:
            logger.error(f"[{self.SERVICE_NAME}] Create failed: {e}")
            return {'success': False, 'msg': f'创建失败: {e}'}

    def get_by_id(self, id_value: Any) -> Optional[Dict[str, Any]]:
        """根据ID获取记录"""
        from business_common import db

        sql = f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = %s"
        return db.get_one(sql, [id_value])

    def get_all(self, filters: Optional[Dict[str, Any]] = None,
                order_by: Optional[str] = None,
                limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有符合条件的记录"""
        from business_common import db

        where_clause = ""
        values = []

        if filters:
            conditions = [f"{k} = %s" for k in filters.keys()]
            where_clause = " WHERE " + " AND ".join(conditions)
            values = list(filters.values())

        order = f" ORDER BY {order_by}" if order_by else ""

        sql = f"SELECT * FROM {self.table_name}{where_clause}{order} LIMIT %s"
        values.append(limit)

        return db.get_all(sql, values) or []

    def update(self, id_value: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新记录"""
        from business_common import db

        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        values = list(data.values()) + [id_value]

        sql = f"UPDATE {self.table_name} SET {set_clause} WHERE {self.primary_key} = %s"

        try:
            affected = db.execute(sql, values)
            logger.info(f"[{self.SERVICE_NAME}] Updated {affected} record(s)")
            return {'success': True, 'msg': f'更新了 {affected} 条记录'}
        except Exception as e:
            logger.error(f"[{self.SERVICE_NAME}] Update failed: {e}")
            return {'success': False, 'msg': f'更新失败: {e}'}

    def delete(self, id_value: Any) -> Dict[str, Any]:
        """删除记录"""
        from business_common import db

        sql = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = %s"

        try:
            affected = db.execute(sql, [id_value])
            logger.info(f"[{self.SERVICE_NAME}] Deleted {affected} record(s)")
            return {'success': True, 'msg': f'删除了 {affected} 条记录'}
        except Exception as e:
            logger.error(f"[{self.SERVICE_NAME}] Delete failed: {e}")
            return {'success': False, 'msg': f'删除失败: {e}'}

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计记录数"""
        from business_common import db

        where_clause = ""
        values = []

        if filters:
            conditions = [f"{k} = %s" for k in filters.keys()]
            where_clause = " WHERE " + " AND ".join(conditions)
            values = list(filters.values())

        sql = f"SELECT COUNT(*) as cnt FROM {self.table_name}{where_clause}"
        result = db.get_one(sql, values)

        return result.get('cnt', 0) if result else 0


class TransactionService(BaseService):
    """
    事务性服务基类

    提供事务管理能力，确保数据一致性
    """

    def __init__(self):
        super().__init__()
        from business_common import db
        self.db = db

    def execute_transaction(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行事务操作

        operations: 操作列表，每个元素包含:
            - sql: SQL语句
            - params: 参数列表
        """
        conn = self.db.get_db()
        cursor = conn.cursor()
        conn.begin()

        try:
            results = []
            for op in operations:
                cursor.execute(op['sql'], op.get('params', []))
                results.append(cursor.rowcount)

            conn.commit()
            logger.info(f"[{self.SERVICE_NAME}] Transaction committed: {len(operations)} operations")
            return {'success': True, 'results': results}

        except Exception as e:
            conn.rollback()
            logger.error(f"[{self.SERVICE_NAME}] Transaction rolled back: {e}")
            return {'success': False, 'msg': f'事务失败: {e}'}

        finally:
            cursor.close()
            conn.close()


class ServiceRegistry:
    """
    服务注册中心

    提供服务的统一注册和访问
    """

    _services: Dict[str, BaseService] = {}

    @classmethod
    def register(cls, name: str, service: BaseService):
        """注册服务"""
        cls._services[name] = service
        logger.info(f"Service registered: {name}")

    @classmethod
    def get(cls, name: str) -> Optional[BaseService]:
        """获取服务"""
        return cls._services.get(name)

    @classmethod
    def list_services(cls) -> List[str]:
        """列出所有服务"""
        return list(cls._services.keys())

    @classmethod
    def health_check_all(cls) -> Dict[str, Any]:
        """检查所有服务健康状态"""
        results = {}
        for name, service in cls._services.items():
            try:
                results[name] = service.health_check()
            except Exception as e:
                results[name] = {
                    'service': name,
                    'status': 'unhealthy',
                    'error': str(e)
                }
        return results
