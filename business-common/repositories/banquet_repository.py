"""
Banquet Repository
包间数据访问层
"""
import logging
from typing import Dict, Any, List
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class BanquetRoomRepository(BaseRepository):
    TABLE_NAME = 'ts_banquet_room'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'sort_order ASC, id ASC'

    def find_available(self, ec_id: str = None) -> List[Dict[str, Any]]:
        conditions = ["status=1", "deleted=0"]
        params = []
        if ec_id:
            conditions.append("ec_id=%s")
            params.append(ec_id)
        where = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where} ORDER BY {self.DEFAULT_ORDER}"
        return self.db.get_all(sql, params) or []


class BanquetBookingRepository(BaseRepository):
    TABLE_NAME = 'ts_banquet_booking'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'

    def find_by_user(self, user_id: str, status: str = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        conditions = ["user_id=%s", "deleted=0"]
        params = [user_id]
        if status:
            conditions.append("status=%s")
            params.append(status)
        where = " AND ".join(conditions)
        offset = (page - 1) * page_size
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where}"
        total = (self.db.get_one(count_sql, params.copy()) or {}).get('cnt', 0)
        data_sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        items = self.db.get_all(data_sql, params + [page_size, offset]) or []
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}

    def check_conflict(self, room_id: int, booking_date: str, start_time: str, end_time: str, exclude_id: int = None) -> bool:
        """检查包间时间冲突"""
        conditions = ["room_id=%s", "booking_date=%s", "status NOT IN ('cancelled','rejected')", "deleted=0",
                       "((start_time<%s AND end_time>%s) OR (start_time<%s AND end_time>%s) OR (start_time>=%s AND end_time<=%s))"]
        params = [room_id, booking_date, end_time, start_time, end_time, start_time, start_time, end_time]
        if exclude_id:
            conditions.append("id!=%s")
            params.append(exclude_id)
        where = " AND ".join(conditions)
        sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where}"
        result = self.db.get_one(sql, params)
        return (result or {}).get('cnt', 0) > 0
