"""
Booking Repository
预约数据访问层
"""
import logging
from typing import Optional, Dict, Any, List
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class BookingRepository(BaseRepository):
    """预约仓储类"""

    TABLE_NAME = 'business_venue_bookings'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'booking_time DESC'

    def find_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """查询用户的预约列表"""
        sql = ("SELECT * FROM business_venue_bookings "
               "WHERE user_id=%s AND deleted=0 ORDER BY booking_time DESC")
        return self.db.get_all(sql, [user_id]) or []
