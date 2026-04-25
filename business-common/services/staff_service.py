"""
Staff Service
员工端业务逻辑层
"""
import logging
from typing import Dict, Any

from .base_service import BaseService
from ..repositories.application_repository import ApplicationRepository
from ..repositories.order_repository import OrderRepository
from ..repositories.stats_repository import StatsRepository
from ..repositories.member_repository import MemberRepository

logger = logging.getLogger(__name__)


class StaffService(BaseService):
    """员工端服务"""

    SERVICE_NAME = 'StaffService'

    def __init__(self):
        super().__init__()
        self.app_repo = ApplicationRepository()
        self.order_repo = OrderRepository()
        self.stats_repo = StatsRepository()
        self.member_repo = MemberRepository()

    # ============ 申请单 ============

    def list_applications(self, user: dict, status: str = None,
                          keyword: str = None, page: int = 1,
                          page_size: int = 20) -> Dict[str, Any]:
        """员工端查询申请列表"""
        try:
            result = self.app_repo.find_all_with_filters(
                ec_id=user.get('ec_id'),
                project_id=user.get('project_id'),
                status=status,
                keyword=keyword,
                page=page,
                page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error("员工端查询申请列表失败: %s", e)
            return self.error('查询失败')

    def get_application_detail(self, app_id: int) -> Dict[str, Any]:
        """获取申请详情"""
        try:
            data = self.app_repo.find_detail_by_id(app_id)
            if not data:
                return self.error('申请不存在')
            return self.success(data)
        except Exception as e:
            self.logger.error("查询申请详情失败: %s", e)
            return self.error('查询失败')

    # ============ 订单 ============

    def list_orders(self, user: dict, status: str = None,
                    page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """员工端查询订单列表"""
        try:
            scope = "deleted=0"
            params = []
            if user.get('ec_id'):
                scope += " AND ec_id=%s"
                params.append(user['ec_id'])
            if user.get('project_id'):
                scope += " AND project_id=%s"
                params.append(user['project_id'])
            if status:
                scope += " AND status=%s"
                params.append(status)

            offset = (page - 1) * page_size
            count_sql = "SELECT COUNT(*) as cnt FROM business_orders WHERE " + scope
            count_result = self.order_repo.db.get_one(count_sql, params.copy())
            total = count_result.get('cnt', 0) if count_result else 0

            data_sql = ("SELECT * FROM business_orders WHERE " + scope +
                        " ORDER BY created_at DESC LIMIT %s OFFSET %s")
            items = self.order_repo.db.get_all(data_sql, params + [page_size, offset]) or []

            return self.success({
                'items': items, 'total': total,
                'page': page, 'page_size': page_size
            })
        except Exception as e:
            self.logger.error("员工端查询订单列表失败: %s", e)
            return self.error('查询失败')

    # ============ 统计 ============

    def get_statistics(self, user: dict) -> Dict[str, Any]:
        """员工端统计数据"""
        try:
            scope = "deleted=0"
            params = []
            if user.get('ec_id'):
                scope += " AND ec_id=%s"
                params.append(user['ec_id'])
            if user.get('project_id'):
                scope += " AND project_id=%s"
                params.append(user['project_id'])

            app_stats = self.stats_repo.count_applications_by_status(scope, params.copy())
            today_orders = self.stats_repo.count_today_orders(scope, params.copy())
            today_income = self.stats_repo.sum_today_income(scope, params.copy())

            return self.success({
                'pending_applications': app_stats.get('pending', 0),
                'processing_applications': app_stats.get('processing', 0),
                'today_orders': today_orders,
                'today_income': today_income
            })
        except Exception as e:
            self.logger.error("获取员工端统计失败: %s", e)
            return self.error('获取统计失败')

    # ============ 会员 ============

    def list_members(self, keyword: str = None,
                     page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """查询会员列表"""
        try:
            result = self.member_repo.find_members_with_filter(
                keyword=keyword, page=page, page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error("查询会员列表失败: %s", e)
            return self.error('查询失败')
