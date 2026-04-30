"""
Member/Points/Coupon Repository
会员积分优惠券数据访问层
"""
import logging
from typing import Dict, Any, List, Optional
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MemberLevelRepository(BaseRepository):
    TABLE_NAME = 'ts_member_level'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'level ASC'


class MemberRepository(BaseRepository):
    TABLE_NAME = 'ts_member'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'

    def find_by_user(self, user_id: str, ec_id: str = None) -> Optional[Dict[str, Any]]:
        conditions = ["user_id=%s", "deleted=0"]
        params = [user_id]
        if ec_id:
            conditions.append("ec_id=%s")
            params.append(ec_id)
        where = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where} LIMIT 1"
        return self.db.get_one(sql, params)

    def add_points(self, member_id: int, points: int) -> int:
        sql = f"UPDATE {self.TABLE_NAME} SET points=points+%s, total_points=total_points+%s, updated_at=NOW() WHERE id=%s"
        return self.db.execute(sql, [points, points, member_id])

    def deduct_points(self, member_id: int, points: int) -> int:
        sql = f"UPDATE {self.TABLE_NAME} SET points=points-%s, updated_at=NOW() WHERE id=%s AND points>=%s"
        return self.db.execute(sql, [points, member_id, points])

    def add_balance(self, member_id: int, amount: float) -> int:
        sql = f"UPDATE {self.TABLE_NAME} SET balance=balance+%s, updated_at=NOW() WHERE id=%s"
        return self.db.execute(sql, [amount, member_id])

    def deduct_balance(self, member_id: int, amount: float) -> int:
        sql = f"UPDATE {self.TABLE_NAME} SET balance=balance-%s, updated_at=NOW() WHERE id=%s AND balance>=%s"
        return self.db.execute(sql, [amount, member_id, amount])


class PointsLogRepository(BaseRepository):
    TABLE_NAME = 'ts_points_log'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'

    def find_by_user(self, user_id: str, type_filter: str = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        conditions = ["user_id=%s"]
        params = [user_id]
        if type_filter:
            conditions.append("type=%s")
            params.append(type_filter)
        where = " AND ".join(conditions)
        offset = (page - 1) * page_size
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where}"
        total = (self.db.get_one(count_sql, params.copy()) or {}).get('cnt', 0)
        data_sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        items = self.db.get_all(data_sql, params + [page_size, offset]) or []
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}


class CouponTemplateRepository(BaseRepository):
    TABLE_NAME = 'ts_coupon_template'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'


class UserCouponRepository(BaseRepository):
    TABLE_NAME = 'ts_user_coupon'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'

    def find_by_user(self, user_id: str, status: int = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        conditions = ["user_id=%s"]
        params = [user_id]
        if status is not None:
            conditions.append("status=%s")
            params.append(status)
        where = " AND ".join(conditions)
        offset = (page - 1) * page_size
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where}"
        total = (self.db.get_one(count_sql, params.copy()) or {}).get('cnt', 0)
        data_sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        items = self.db.get_all(data_sql, params + [page_size, offset]) or []
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}

    def find_available_coupons(self, user_id: str) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE user_id=%s AND status=0 AND (expire_time IS NULL OR expire_time>NOW()) ORDER BY coupon_value DESC"
        return self.db.get_all(sql, [user_id]) or []


class ConsumptionLedgerRepository(BaseRepository):
    TABLE_NAME = 'ts_consumption_ledger'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'

    def find_by_user(self, user_id: str, module: str = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        conditions = ["user_id=%s"]
        params = [user_id]
        if module:
            conditions.append("module=%s")
            params.append(module)
        where = " AND ".join(conditions)
        offset = (page - 1) * page_size
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where}"
        total = (self.db.get_one(count_sql, params.copy()) or {}).get('cnt', 0)
        data_sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        items = self.db.get_all(data_sql, params + [page_size, offset]) or []
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}

    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        sql = """SELECT module, COUNT(*) as order_count, SUM(pay_amount) as total_amount
                 FROM ts_consumption_ledger WHERE user_id=%s GROUP BY module"""
        rows = self.db.get_all(sql, [user_id]) or []
        return rows
