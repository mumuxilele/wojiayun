"""
Admin Service
管理端业务逻辑层
"""
import logging
from typing import Dict, Any, List

from .base_service import BaseService
from ..models.application import Application
from ..repositories.application_repository import ApplicationRepository
from ..repositories.order_repository import OrderRepository
from ..repositories.order_item_repository import OrderItemRepository
from ..repositories.stats_repository import StatsRepository
from ..repositories.shop_repository import ShopRepository
from ..repositories.member_repository import MemberRepository

logger = logging.getLogger(__name__)


class AdminService(BaseService):
    """管理端服务"""

    SERVICE_NAME = 'AdminService'

    def __init__(self):
        super().__init__()
        self.app_repo = ApplicationRepository()
        self.order_repo = OrderRepository()
        self.order_item_repo = OrderItemRepository()
        self.stats_repo = StatsRepository()
        self.shop_repo = ShopRepository()
        self.member_repo = MemberRepository()

    # ============ 申请单管理 ============

    def list_applications(self, status: str = None, app_type: str = None,
                          keyword: str = None, start_date: str = None,
                          end_date: str = None, page: int = 1,
                          page_size: int = 20) -> Dict[str, Any]:
        """管理端查询申请列表（多条件筛选）"""
        try:
            conditions = ["deleted=0"]
            params = []

            if status:
                conditions.append("status=%s")
                params.append(status)
            if app_type:
                conditions.append("(app_type=%s OR type_code=%s)")
                params.extend([app_type, app_type])
            if keyword:
                conditions.append("(title LIKE %s OR content LIKE %s OR user_name LIKE %s OR app_no LIKE %s)")
                kw = "%" + keyword + "%"
                params.extend([kw, kw, kw, kw])
            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date + ' 23:59:59')

            where_clause = " AND ".join(conditions)
            offset = (page - 1) * page_size

            # 总数
            count_sql = "SELECT COUNT(*) as cnt FROM business_applications WHERE " + where_clause
            count_result = self.app_repo.db.get_one(count_sql, params.copy())
            total = count_result.get('cnt', 0) if count_result else 0

            # 数据
            data_sql = ("SELECT * FROM business_applications WHERE " + where_clause +
                        " ORDER BY created_at DESC LIMIT %s OFFSET %s")
            items = self.app_repo.db.get_all(data_sql, params + [page_size, offset]) or []

            return self.success({
                'items': items, 'total': total,
                'page': page, 'page_size': page_size
            })
        except Exception as e:
            self.logger.error("管理端查询申请列表失败: %s", e)
            return self.error('查询失败')

    def get_application(self, app_id: int) -> Dict[str, Any]:
        """获取申请详情"""
        try:
            data = self.app_repo.find_by_id(app_id)
            if not data:
                return self.error('申请不存在')
            return self.success(data)
        except Exception as e:
            self.logger.error("获取申请详情失败: %s", e)
            return self.error('查询失败')

    def update_application(self, app_id: int, data: dict) -> Dict[str, Any]:
        """修改申请单"""
        try:
            fields = ['title', 'content', 'status', 'priority', 'result',
                       'assignee_id', 'assignee_name']
            updates = {}
            for field in fields:
                if field in data:
                    updates[field] = data[field]

            if not updates:
                return self.error('无更新内容')

            affected = self.app_repo.update(app_id, updates)
            if affected > 0:
                return self.success(msg='修改成功')
            return self.error('修改失败')
        except Exception as e:
            self.logger.error("修改申请失败: %s", e)
            return self.error('修改失败')

    def delete_application(self, app_id: int) -> Dict[str, Any]:
        """软删除申请单"""
        try:
            affected = self.app_repo.soft_delete(app_id)
            if affected > 0:
                return self.success(msg='删除成功')
            return self.error('删除失败')
        except Exception as e:
            self.logger.error("删除申请失败: %s", e)
            return self.error('删除失败')

    # ============ 订单管理 ============

    def list_orders(self, status: str = None, keyword: str = None,
                    start_date: str = None, end_date: str = None,
                    page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """管理端查询订单列表"""
        try:
            conditions = ["deleted=0"]
            params = []

            if status:
                conditions.append("status=%s")
                params.append(status)
            if keyword:
                conditions.append("(order_no LIKE %s OR user_name LIKE %s)")
                kw = "%" + keyword + "%"
                params.extend([kw, kw])
            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date + ' 23:59:59')

            where_clause = " AND ".join(conditions)
            offset = (page - 1) * page_size

            # 总数
            count_sql = "SELECT COUNT(*) as cnt FROM business_orders WHERE " + where_clause
            count_result = self.order_repo.db.get_one(count_sql, params.copy())
            total = count_result.get('cnt', 0) if count_result else 0

            # 数据
            data_sql = ("SELECT * FROM business_orders WHERE " + where_clause +
                        " ORDER BY created_at DESC LIMIT %s OFFSET %s")
            items = self.order_repo.db.get_all(data_sql, params + [page_size, offset]) or []

            return self.success({
                'items': items, 'total': total,
                'page': page, 'page_size': page_size
            })
        except Exception as e:
            self.logger.error("管理端查询订单列表失败: %s", e)
            return self.error('查询失败')

    def get_order(self, order_id: int) -> Dict[str, Any]:
        """获取订单详情（含明细）"""
        try:
            order = self.order_repo.find_by_id(order_id)
            if not order:
                return self.error('订单不存在')
            items = self.order_item_repo.find_by_order_id(order_id)
            return self.success({'order': order, 'items': items})
        except Exception as e:
            self.logger.error("获取订单详情失败: %s", e)
            return self.error('查询失败')

    def update_order(self, order_id: int, data: dict) -> Dict[str, Any]:
        """修改订单"""
        try:
            fields = ['status', 'pay_status', 'total_amount', 'remark']
            updates = {}
            for field in fields:
                if field in data:
                    updates[field] = data[field]
            if not updates:
                return self.error('无更新内容')
            affected = self.order_repo.update(order_id, updates)
            if affected > 0:
                return self.success(msg='修改成功')
            return self.error('修改失败')
        except Exception as e:
            self.logger.error("修改订单失败: %s", e)
            return self.error('修改失败')

    def delete_order(self, order_id: int) -> Dict[str, Any]:
        """软删除订单"""
        try:
            affected = self.order_repo.soft_delete(order_id)
            if affected > 0:
                return self.success(msg='删除成功')
            return self.error('删除失败')
        except Exception as e:
            self.logger.error("删除订单失败: %s", e)
            return self.error('删除失败')

    # ============ 门店管理 ============

    def list_shops(self) -> Dict[str, Any]:
        """查询所有门店"""
        try:
            shops = self.shop_repo.find_all_shops()
            return self.success(shops)
        except Exception as e:
            self.logger.error("查询门店列表失败: %s", e)
            return self.error('查询失败')

    def get_shop(self, shop_id: int) -> Dict[str, Any]:
        """获取门店详情"""
        try:
            shop = self.shop_repo.find_by_id(shop_id)
            return self.success(shop)
        except Exception as e:
            self.logger.error("获取门店详情失败: %s", e)
            return self.error('查询失败')

    def create_shop(self, data: dict) -> Dict[str, Any]:
        """创建门店"""
        try:
            shop_id = self.shop_repo.insert_shop(data)
            if shop_id:
                return self.success({'id': shop_id}, '创建成功')
            return self.error('创建失败')
        except Exception as e:
            self.logger.error("创建门店失败: %s", e)
            return self.error('创建失败')

    def update_shop(self, shop_id: int, data: dict) -> Dict[str, Any]:
        """修改门店"""
        try:
            fields = ['shop_name', 'shop_type', 'address', 'phone', 'status', 'description']
            updates = {}
            for field in fields:
                if field in data:
                    updates[field] = data[field]
            if not updates:
                return self.success(msg='无更新内容')
            affected = self.shop_repo.update_shop(shop_id, updates)
            if affected > 0:
                return self.success(msg='修改成功')
            return self.error('修改失败')
        except Exception as e:
            self.logger.error("修改门店失败: %s", e)
            return self.error('修改失败')

    def delete_shop(self, shop_id: int) -> Dict[str, Any]:
        """软删除门店"""
        try:
            affected = self.shop_repo.soft_delete_shop(shop_id)
            if affected > 0:
                return self.success(msg='删除成功')
            return self.error('删除失败')
        except Exception as e:
            self.logger.error("删除门店失败: %s", e)
            return self.error('删除失败')

    # ============ 统计 ============

    def get_statistics(self) -> Dict[str, Any]:
        """管理端综合统计"""
        try:
            scope = "deleted=0"
            app_stats = self.stats_repo.count_applications_by_status_group(scope)
            order_stats = self.stats_repo.count_orders_by_status_group(scope)
            today_apps = self.stats_repo.count_today_applications(scope)
            today_orders = self.stats_repo.count_today_orders(scope)

            # 今日收入需单独计算
            today_income = self.stats_repo.sum_today_income(scope)

            return self.success({
                'application_stats': app_stats,
                'order_stats': order_stats,
                'today': {
                    'applications': today_apps,
                    'orders': today_orders,
                    'income': today_income
                }
            })
        except Exception as e:
            self.logger.error("获取管理端统计失败: %s", e)
            return self.error('获取统计失败')

    # ============ 用户管理 ============

    def list_members(self, keyword: str = None,
                     page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """查询用户列表"""
        try:
            result = self.member_repo.find_members_with_filter(
                keyword=keyword, page=page, page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error("查询用户列表失败: %s", e)
            return self.error('查询失败')
