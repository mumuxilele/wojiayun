"""
Order Item Repository
订单明细数据访问层
"""
import logging
from typing import Dict, Any, List
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class OrderItemRepository(BaseRepository):
    """订单明细仓储类"""

    TABLE_NAME = 'business_order_items'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'id ASC'

    def find_by_order_id(self, order_id: int) -> List[Dict[str, Any]]:
        """根据订单ID查询明细"""
        sql = "SELECT * FROM business_order_items WHERE order_id=%s"
        return self.db.get_all(sql, [order_id]) or []

    def insert_item(self, data: Dict[str, Any]) -> int:
        """插入订单明细"""
        return self.insert(data)
