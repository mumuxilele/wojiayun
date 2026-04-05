"""
V29.0 后端分层架构 - 仓储层基类
提供统一的数据访问封装

设计原则:
  - 仓储层只负责数据访问
  - 不包含业务逻辑
  - 统一的异常处理
  - SQL参数化防注入
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from abc import ABC, abstractmethod
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """
    仓储基类

    所有数据访问类继承此类
    """

    # 表名，由子类覆盖
    TABLE_NAME: str = ''
    # 主键名，由子类覆盖
    PRIMARY_KEY: str = 'id'

    def __init__(self):
        from business_common import db
        self.db = db

    # ============ 基础CRUD ============

    def find_by_id(self, id_value: Any) -> Optional[Dict[str, Any]]:
        """根据ID查询"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {self.PRIMARY_KEY} = %s"
        return self.db.get_one(sql, [id_value])

    def find_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """查询所有"""
        sql = f"SELECT * FROM {self.TABLE_NAME} ORDER BY {self.PRIMARY_KEY} DESC LIMIT %s OFFSET %s"
        return self.db.get_all(sql, [limit, offset]) or []

    def find_by_field(self, field: str, value: Any) -> List[Dict[str, Any]]:
        """根据字段查询"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {field} = %s"
        return self.db.get_all(sql, [value]) or []

    def find_one_by_field(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        """根据字段查询单条"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {field} = %s LIMIT 1"
        return self.db.get_one(sql, [value])

    def insert(self, data: Dict[str, Any]) -> int:
        """插入数据"""
        fields = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {self.TABLE_NAME} ({fields}) VALUES ({placeholders})"
        self.db.execute(sql, list(data.values()))
        return self.db.get_db().cursor.lastrowid

    def update(self, id_value: Any, data: Dict[str, Any]) -> int:
        """更新数据"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE {self.PRIMARY_KEY} = %s"
        values = list(data.values()) + [id_value]
        return self.db.execute(sql, values)

    def delete(self, id_value: Any) -> int:
        """删除数据"""
        sql = f"DELETE FROM {self.TABLE_NAME} WHERE {self.PRIMARY_KEY} = %s"
        return self.db.execute(sql, [id_value])

    def count(self, where: str = '', params: List[Any] = None) -> int:
        """统计数量"""
        sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME}"
        if where:
            sql += f" WHERE {where}"
        result = self.db.get_one(sql, params or [])
        return result.get('cnt', 0) if result else 0

    # ============ 事务支持 ============

    @contextmanager
    def transaction(self):
        """
        事务上下文管理器

        使用示例:
            with repo.transaction():
                repo.insert(data1)
                repo.update(id, data2)
        """
        conn = self.db.get_db()
        cursor = conn.cursor()
        conn.begin()

        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def execute_in_transaction(self, operations: List[Dict[str, Any]]) -> bool:
        """
        执行事务操作

        Args:
            operations: 操作列表，每个元素 {'sql': xxx, 'params': [xxx]}
        """
        with self.transaction() as cursor:
            for op in operations:
                cursor.execute(op['sql'], op.get('params', []))
        return True


class MemberRepository(BaseRepository):
    """会员仓储"""

    TABLE_NAME = 'business_members'
    PRIMARY_KEY = 'user_id'

    def find_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """根据手机号查询"""
        return self.find_one_by_field('phone', phone)

    def find_by_openid(self, openid: str) -> Optional[Dict[str, Any]]:
        """根据微信OpenID查询"""
        return self.find_one_by_field('wx_openid', openid)

    def update_points(self, user_id: int, points_delta: int) -> int:
        """更新积分"""
        if points_delta > 0:
            sql = """UPDATE business_members
                     SET points = points + %s, total_points = total_points + %s
                     WHERE user_id = %s"""
        else:
            sql = """UPDATE business_members
                     SET points = points + %s
                     WHERE user_id = %s"""
            points_delta = abs(points_delta)
        return self.db.execute(sql, [points_delta, user_id])

    def update_balance(self, user_id: int, amount: float) -> int:
        """更新余额"""
        sql = """UPDATE business_members
                 SET balance = balance + %s WHERE user_id = %s"""
        return self.db.execute(sql, [amount, user_id])


class OrderRepository(BaseRepository):
    """订单仓储"""

    TABLE_NAME = 'business_orders'
    PRIMARY_KEY = 'id'

    def find_by_order_no(self, order_no: str) -> Optional[Dict[str, Any]]:
        """根据订单号查询"""
        return self.find_one_by_field('order_no', order_no)

    def find_by_user(self, user_id: int, status: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """查询用户的订单"""
        sql = "SELECT * FROM business_orders WHERE user_id = %s"
        params = [user_id]

        if status:
            sql += " AND order_status = %s"
            params.append(status)

        sql += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        return self.db.get_all(sql, params) or []

    def update_status(self, order_id: int, status: str) -> int:
        """更新订单状态"""
        sql = "UPDATE business_orders SET order_status = %s, updated_at = NOW() WHERE id = %s"
        return self.db.execute(sql, [status, order_id])


class PaymentRepository(BaseRepository):
    """支付仓储"""

    TABLE_NAME = 'business_payments'
    PRIMARY_KEY = 'id'

    def find_by_pay_no(self, pay_no: str) -> Optional[Dict[str, Any]]:
        """根据支付单号查询"""
        return self.find_one_by_field('pay_no', pay_no)

    def find_pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        """查询待支付"""
        sql = "SELECT * FROM business_payments WHERE status = 'pending' ORDER BY created_at LIMIT %s"
        return self.db.get_all(sql, [limit]) or []

    def find_by_user(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """查询用户的支付记录"""
        sql = "SELECT * FROM business_payments WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
        return self.db.get_all(sql, [user_id, limit]) or []


class ProductRepository(BaseRepository):
    """商品仓储"""

    TABLE_NAME = 'business_products'
    PRIMARY_KEY = 'id'

    def find_active(self, category_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """查询上架商品"""
        sql = "SELECT * FROM business_products WHERE status = 'active' AND deleted = 0"
        params = []

        if category_id:
            sql += " AND category_id = %s"
            params.append(category_id)

        sql += " ORDER BY sort_order, id LIMIT %s"
        params.append(limit)

        return self.db.get_all(sql, params) or []

    def increment_view(self, product_id: int) -> int:
        """增加浏览数"""
        sql = "UPDATE business_products SET view_count = view_count + 1 WHERE id = %s"
        return self.db.execute(sql, [product_id])

    def increment_sales(self, product_id: int, quantity: int = 1) -> int:
        """增加销量"""
        sql = "UPDATE business_products SET sales_count = sales_count + %s WHERE id = %s"
        return self.db.execute(sql, [quantity, product_id])


# 便捷实例
member_repo = MemberRepository()
order_repo = OrderRepository()
payment_repo = PaymentRepository()
product_repo = ProductRepository()
