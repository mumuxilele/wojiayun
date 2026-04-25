"""
Stats Repository
统计数据访问层，集中管理所有统计 SQL
"""
import logging
from typing import Dict, Any, Optional
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class StatsRepository(BaseRepository):
    """统计仓储类 - 无固定表，提供多表聚合查询"""

    TABLE_NAME = 'business_applications'  # 默认表（基类需要）
    PRIMARY_KEY = 'id'

    def __init__(self):
        super().__init__()

    # ============ 申请单统计 ============

    def count_applications_by_status(self, scope_clause: str = "deleted=0",
                                      params: list = None) -> Dict[str, int]:
        """按状态统计申请单数量"""
        params = params or []
        sql = ("SELECT "
               "  SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending, "
               "  SUM(CASE WHEN status='processing' THEN 1 ELSE 0 END) as processing, "
               "  SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed, "
               "  SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) as rejected, "
               "  SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) as cancelled, "
               "  COUNT(*) as total "
               "FROM business_applications WHERE " + scope_clause)
        result = self.db.get_one(sql, params)
        if result:
            return {k: int(result.get(k, 0) or 0) for k in
                    ('pending', 'processing', 'completed', 'rejected', 'cancelled', 'total')}
        return {'pending': 0, 'processing': 0, 'completed': 0, 'rejected': 0, 'cancelled': 0, 'total': 0}

    def count_applications_by_status_group(self, scope_clause: str = "deleted=0",
                                            params: list = None):
        """按状态分组统计申请单（管理后台用）"""
        params = params or []
        sql = "SELECT status, COUNT(*) as cnt FROM business_applications WHERE " + scope_clause + " GROUP BY status"
        return self.db.get_all(sql, params) or []

    def count_today_applications(self, scope_clause: str = "deleted=0",
                                  params: list = None) -> int:
        """今日新增申请数"""
        params = params or []
        sql = ("SELECT COUNT(*) as cnt FROM business_applications "
               "WHERE DATE(created_at)=CURDATE() AND " + scope_clause)
        result = self.db.get_one(sql, params)
        return result.get('cnt', 0) if result else 0

    # ============ 订单统计 ============

    def count_orders_by_status_group(self, scope_clause: str = "deleted=0",
                                      params: list = None):
        """按状态分组统计订单（管理后台用）"""
        params = params or []
        sql = ("SELECT status, COUNT(*) as cnt, COALESCE(SUM(total_amount),0) as total "
               "FROM business_orders WHERE " + scope_clause + " GROUP BY status")
        return self.db.get_all(sql, params) or []

    def count_today_orders(self, scope_clause: str = "deleted=0",
                            params: list = None) -> int:
        """今日订单数"""
        params = params or []
        sql = ("SELECT COUNT(*) as cnt FROM business_orders "
               "WHERE DATE(created_at)=CURDATE() AND " + scope_clause)
        result = self.db.get_one(sql, params)
        return result.get('cnt', 0) if result else 0

    def sum_today_income(self, scope_clause: str = "deleted=0",
                          params: list = None) -> float:
        """今日收入"""
        params = params or []
        sql = ("SELECT COALESCE(SUM(actual_amount),0) as total FROM business_orders "
               "WHERE DATE(created_at)=CURDATE() AND status IN ('paid','completed') AND " + scope_clause)
        result = self.db.get_one(sql, params)
        return float(result.get('total', 0)) if result else 0.0
