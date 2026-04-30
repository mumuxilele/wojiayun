"""
Cafeteria Repository
食堂数据访问层
"""
import logging
from typing import Dict, Any, List
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class CafeteriaCategoryRepository(BaseRepository):
    TABLE_NAME = 'ts_cafeteria_category'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'sort_order ASC, id ASC'


class CafeteriaDishRepository(BaseRepository):
    TABLE_NAME = 'ts_cafeteria_dish'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'sort_order ASC, id ASC'

    def find_by_category(self, category_id: int, status: int = 1) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE category_id=%s AND status=%s AND deleted=0 ORDER BY {self.DEFAULT_ORDER}"
        return self.db.get_all(sql, [category_id, status]) or []

    def find_on_sale(self, ec_id: str = None, project_id: str = None) -> List[Dict[str, Any]]:
        conditions = ["status=1", "deleted=0"]
        params = []
        if ec_id:
            conditions.append("ec_id=%s")
            params.append(ec_id)
        if project_id:
            conditions.append("project_id=%s")
            params.append(project_id)
        where = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where} ORDER BY {self.DEFAULT_ORDER}"
        return self.db.get_all(sql, params) or []


class CafeteriaOrderRepository(BaseRepository):
    TABLE_NAME = 'ts_cafeteria_order'
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
