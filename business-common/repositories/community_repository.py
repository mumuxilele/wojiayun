"""
Community Repository
社区增值服务数据访问层
"""
import logging
from typing import Dict, Any, List
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class CommunityCategoryRepository(BaseRepository):
    TABLE_NAME = 'ts_community_category'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'sort_order ASC, id ASC'


class CommunityServiceRepository(BaseRepository):
    TABLE_NAME = 'ts_community_service'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'sort_order ASC, id ASC'

    def find_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE category_id=%s AND status=1 AND deleted=0 ORDER BY {self.DEFAULT_ORDER}"
        return self.db.get_all(sql, [category_id]) or []


class CommunityActivityRepository(BaseRepository):
    TABLE_NAME = 'ts_community_activity'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'start_time DESC'

    def find_active(self, ec_id: str = None, project_id: str = None) -> List[Dict[str, Any]]:
        conditions = ["deleted=0", "status IN (1,2)"]
        params = []
        if ec_id:
            conditions.append("ec_id=%s")
            params.append(ec_id)
        if project_id:
            conditions.append("project_id=%s")
            params.append(project_id)
        where = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where} ORDER BY start_time ASC"
        return self.db.get_all(sql, params) or []


class CommunityActivitySignupRepository(BaseRepository):
    TABLE_NAME = 'ts_community_activity_signup'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'

    def find_by_activity(self, activity_id: int, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        offset = (page - 1) * page_size
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE activity_id=%s"
        total = (self.db.get_one(count_sql, [activity_id]) or {}).get('cnt', 0)
        data_sql = f"SELECT * FROM {self.TABLE_NAME} WHERE activity_id=%s ORDER BY created_at DESC LIMIT %s OFFSET %s"
        items = self.db.get_all(data_sql, [activity_id, page_size, offset]) or []
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}

    def check_signed_up(self, activity_id: int, user_id: str) -> bool:
        sql = f"SELECT 1 FROM {self.TABLE_NAME} WHERE activity_id=%s AND user_id=%s AND status=1 LIMIT 1"
        return self.db.get_one(sql, [activity_id, user_id]) is not None


class CommunityPostRepository(BaseRepository):
    TABLE_NAME = 'ts_community_post'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'

    def find_by_type(self, post_type: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        conditions = ["type=%s", "status=1", "deleted=0"]
        where = " AND ".join(conditions)
        offset = (page - 1) * page_size
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where}"
        total = (self.db.get_one(count_sql, [post_type]) or {}).get('cnt', 0)
        data_sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        items = self.db.get_all(data_sql, [post_type, page_size, offset]) or []
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}
