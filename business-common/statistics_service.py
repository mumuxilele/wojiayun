"""
StatisticsService - 统计数据服务
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StatisticsService:
    """统计数据服务 - 统一处理所有统计相关查询"""
    
    def __init__(self):
        from business_common import db
        self.db = db
    
    # === Dashboard 统计 ===
    
    def admin_statistics(self, ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """管理端统计数据"""
        today = datetime.now().strftime('%Y-%m-%d')
        month_start = datetime.now().strftime('%Y-%m-01')
        
        # 用户统计
        total_users = self.db.get_total(
            "SELECT COUNT(*) FROM business_members WHERE deleted=0"
        )
        new_users_today = self.db.get_total(
            f"SELECT COUNT(*) FROM business_members WHERE DATE(created_at)='{today}' AND deleted=0"
        )
        
        # 订单统计
        total_orders = self.db.get_total(
            "SELECT COUNT(*) FROM business_orders WHERE deleted=0"
        )
        pending_orders = self.db.get_total(
            "SELECT COUNT(*) FROM business_orders WHERE order_status='pending' AND deleted=0"
        )
        today_orders = self.db.get_total(
            f"SELECT COUNT(*) FROM business_orders WHERE DATE(created_at)='{today}' AND deleted=0"
        )
        today_revenue = self.db.get_one(
            f"SELECT COALESCE(SUM(actual_amount),0) as total FROM business_orders "
            f"WHERE DATE(created_at)='{today}' AND pay_status='paid' AND deleted=0"
        )
        
        # 申请统计
        pending_applications = self.db.get_total(
            "SELECT COUNT(*) FROM business_applications WHERE status='pending' AND deleted=0"
        )
        
        # 商品统计
        total_products = self.db.get_total(
            "SELECT COUNT(*) FROM business_products WHERE deleted=0"
        )
        active_products = self.db.get_total(
            "SELECT COUNT(*) FROM business_products WHERE status='active' AND deleted=0"
        )
        
        return {
            'users': {'total': total_users, 'new_today': new_users_today},
            'orders': {
                'total': total_orders, 'pending': pending_orders,
                'today': today_orders, 'today_revenue': float(today_revenue.get('total', 0) if today_revenue else 0)
            },
            'applications': {'pending': pending_applications},
            'products': {'total': total_products, 'active': active_products}
        }
    
    def staff_dashboard_stats(self, user_id: str, ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """员工端仪表盘统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 待处理任务
        pending_applications = self.db.get_total(
            "SELECT COUNT(*) FROM business_applications WHERE status='pending' AND deleted=0"
        )
        pending_orders = self.db.get_total(
            "SELECT COUNT(*) FROM business_orders WHERE order_status='paid' AND deleted=0"
        )
        pending_refunds = self.db.get_total(
            "SELECT COUNT(*) FROM business_orders WHERE refund_status='pending' AND deleted=0"
        )
        
        # 今日数据
        today_applications = self.db.get_total(
            f"SELECT COUNT(*) FROM business_applications WHERE DATE(created_at)='{today}' AND deleted=0"
        )
        today_orders = self.db.get_total(
            f"SELECT COUNT(*) FROM business_orders WHERE DATE(created_at)='{today}' AND deleted=0"
        )
        
        # 已处理数量
        my_approved = self.db.get_total(
            f"SELECT COUNT(*) FROM business_applications WHERE approver_id='{user_id}' AND status='approved' AND deleted=0"
        )
        
        return {
            'pending': {
                'applications': pending_applications,
                'orders': pending_orders,
                'refunds': pending_refunds,
                'total': pending_applications + pending_orders + pending_refunds
            },
            'today': {
                'applications': today_applications,
                'orders': today_orders
            },
            'my_stats': {
                'approved': my_approved
            }
        }
    
    def get_staff_stats(self, ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """员工端统计"""
        return self.staff_dashboard_stats('', ec_id, project_id)
    
    def get_staff_statistics(self, ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """员工端统计（别名）"""
        return self.staff_dashboard_stats('', ec_id, project_id)
    
    # === 专项统计 ===
    
    def admin_user_profile(self, user_id: str) -> Dict[str, Any]:
        """用户详情统计"""
        # 基本信息
        user = self.db.get_one(
            "SELECT * FROM business_members WHERE user_id=%s",
            [user_id]
        )
        if not user:
            return {'success': False, 'msg': '用户不存在'}
        
        # 订单统计
        orders = self.db.get_one(
            "SELECT COUNT(*) as count, COALESCE(SUM(actual_amount),0) as total "
            "FROM business_orders WHERE user_id=%s AND pay_status='paid' AND deleted=0",
            [user_id]
        )
        
        # 申请统计
        applications = self.db.get_one(
            "SELECT COUNT(*) as count FROM business_applications WHERE user_id=%s AND deleted=0",
            [user_id]
        )
        
        # 积分记录
        points = self.db.get_one(
            "SELECT points, total_points FROM business_members WHERE user_id=%s",
            [user_id]
        )
        
        return {
            'success': True,
            'data': {
                'user': user,
                'orders': orders or {'count': 0, 'total': 0},
                'applications': applications or {'count': 0},
                'points': points or {'points': 0, 'total_points': 0}
            }
        }
    
    def venue_statistics(self, venue_id: int = None) -> Dict[str, Any]:
        """场地统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if venue_id:
            # 单个场地统计
            bookings = self.db.get_total(
                "SELECT COUNT(*) FROM business_venue_bookings WHERE venue_id=%s AND deleted=0",
                [venue_id]
            )
            revenue = self.db.get_one(
                "SELECT COALESCE(SUM(total_price),0) as total FROM business_venue_bookings "
                "WHERE venue_id=%s AND status='paid' AND deleted=0",
                [venue_id]
            )
            return {
                'bookings': bookings,
                'revenue': float(revenue.get('total', 0) if revenue else 0)
            }
        else:
            # 所有场地统计
            total_venues = self.db.get_total(
                "SELECT COUNT(*) FROM business_venues WHERE deleted=0"
            )
            today_bookings = self.db.get_total(
                f"SELECT COUNT(*) FROM business_venue_bookings WHERE DATE(created_at)='{today}' AND deleted=0"
            )
            return {
                'total_venues': total_venues,
                'today_bookings': today_bookings
            }
    
    def admin_points_stats(self, ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """积分统计"""
        total_issued = self.db.get_one(
            "SELECT COALESCE(SUM(points),0) as total FROM business_points_log WHERE points > 0"
        )
        total_used = self.db.get_one(
            "SELECT COALESCE(SUM(ABS(points)),0) as total FROM business_points_log WHERE points < 0"
        )
        total_balance = self.db.get_one(
            "SELECT COALESCE(SUM(points),0) as total FROM business_members WHERE deleted=0"
        )
        
        return {
            'issued': float(total_issued.get('total', 0) if total_issued else 0),
            'used': float(total_used.get('total', 0) if total_used else 0),
            'balance': float(total_balance.get('total', 0) if total_balance else 0)
        }
    
    def staff_pending_refunds(self, ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """待处理退款列表"""
        refunds = self.db.get_all("""
            SELECT o.id, o.order_no, o.user_id, o.actual_amount, o.refund_reason, 
                   o.refund_requested_at, m.user_name, m.phone
            FROM business_orders o
            LEFT JOIN business_members m ON o.user_id=m.user_id
            WHERE o.refund_status='pending' AND o.deleted=0
            ORDER BY o.refund_requested_at ASC
            LIMIT 50
        """) or []
        
        return {'items': refunds, 'total': len(refunds)}
    
    def get_staff_member_activity(self, ec_id: str = None, project_id: str = None, 
                                   days: int = 7) -> Dict[str, Any]:
        """会员活动统计"""
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 活跃用户
        active_users = self.db.get_total(f"""
            SELECT COUNT(DISTINCT user_id) FROM business_orders 
            WHERE DATE(created_at) >= '{date_from}' AND deleted=0
        """)
        
        # 新注册
        new_users = self.db.get_total(f"""
            SELECT COUNT(*) FROM business_members 
            WHERE DATE(created_at) >= '{date_from}' AND deleted=0
        """)
        
        # 订单趋势
        order_trend = self.db.get_all(f"""
            SELECT DATE(created_at) as date, COUNT(*) as count, SUM(actual_amount) as amount
            FROM business_orders 
            WHERE DATE(created_at) >= '{date_from}' AND pay_status='paid' AND deleted=0
            GROUP BY DATE(created_at)
            ORDER BY date
        """) or []
        
        return {
            'active_users': active_users,
            'new_users': new_users,
            'order_trend': order_trend
        }


# 单例
_stats_service = None

def get_stats_service() -> StatisticsService:
    global _stats_service
    if _stats_service is None:
        _stats_service = StatisticsService()
    return _stats_service
