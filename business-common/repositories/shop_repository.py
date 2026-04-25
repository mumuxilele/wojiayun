"""
Shop Repository
门店数据访问层
"""
import logging
from typing import Optional, Dict, Any, List
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ShopRepository(BaseRepository):
    """门店仓储类"""

    TABLE_NAME = 'business_shops'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'id ASC'

    def find_open_shops(self, shop_type: str = None) -> List[Dict[str, Any]]:
        """查询营业中的门店"""
        if shop_type:
            sql = "SELECT * FROM business_shops WHERE shop_type=%s AND status='open' AND deleted=0"
            return self.db.get_all(sql, [shop_type]) or []
        sql = "SELECT * FROM business_shop WHERE status='open' AND deleted=0"
        return self.db.get_all(sql) or []

    def find_all_shops(self) -> List[Dict[str, Any]]:
        """查询所有门店（管理后台）"""
        sql = "SELECT * FROM business_shops WHERE deleted=0 ORDER BY id"
        return self.db.get_all(sql) or []

    def insert_shop(self, data: Dict[str, Any]) -> int:
        """插入门店"""
        fields = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = "INSERT INTO business_shops (" + fields + ") VALUES (" + placeholders + ")"
        self.db.execute(sql, list(data.values()))
        result = self.db.get_one("SELECT LAST_INSERT_ID() as id")
        return result.get('id', 0) if result else 0

    def update_shop(self, shop_id: int, data: Dict[str, Any]) -> int:
        """更新门店"""
        set_clause = ', '.join([k + "=%s" for k in data.keys()])
        sql = "UPDATE business_shops SET " + set_clause + " WHERE id=%s"
        return self.db.execute(sql, list(data.values()) + [shop_id])

    def soft_delete_shop(self, shop_id: int) -> int:
        """软删除门店"""
        sql = "UPDATE business_shops SET deleted=1 WHERE id=%s"
        return self.db.execute(sql, [shop_id])
