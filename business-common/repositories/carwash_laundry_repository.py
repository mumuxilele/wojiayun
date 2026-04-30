"""
Carwash/Laundry Repository
洗车洗衣数据访问层
"""
import logging
from typing import Dict, Any, List
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class CarwashServiceRepository(BaseRepository):
    TABLE_NAME = 'ts_carwash_service'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'sort_order ASC, id ASC'


class CarwashStationRepository(BaseRepository):
    TABLE_NAME = 'ts_carwash_station'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'id ASC'


class CarwashOrderRepository(BaseRepository):
    TABLE_NAME = 'ts_carwash_order'
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


class LaundryServiceRepository(BaseRepository):
    TABLE_NAME = 'ts_laundry_service'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'sort_order ASC, id ASC'


class LaundryPriceRepository(BaseRepository):
    TABLE_NAME = 'ts_laundry_price'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'sort_order ASC, id ASC'

    def find_by_service(self, service_id: int) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE service_id=%s AND deleted=0 ORDER BY {self.DEFAULT_ORDER}"
        return self.db.get_all(sql, [service_id]) or []


class LaundryOrderRepository(BaseRepository):
    TABLE_NAME = 'ts_laundry_order'
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
