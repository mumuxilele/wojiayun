"""
员工工作台服务 V44.0

功能:
1. 今日待办汇总 (待处理订单、待处理售后、即将核销预约、库存预警)
2. 今日业务概览 (今日订单数/金额、今日新会员、今日签到)
3. 快捷操作入口配置
4. 员工消息通知未读数
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any

from . import db
from .cache_service import cache_get, cache_set

logger = logging.getLogger(__name__)


class WorkbenchService:
    """员工工作台服务"""

    CACHE_TTL = 60  # 1分钟缓存（数据实时性要求高）

    def get_workbench(self, staff_id: int, ec_id: int, project_id: int) -> Dict[str, Any]:
        """
        获取员工工作台全量数据

        Returns:
            {
                "todo": {待办汇总},
                "today_stats": {今日统计},
                "alerts": [预警列表],
                "quick_actions": [快捷操作],
                "unread_count": 3
            }
        """
        cache_key = f"workbench_{staff_id}_{ec_id}_{project_id}"
        cached = cache_get(cache_key)
        if cached:
            return cached

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        now = datetime.now()
        next_2h = now + timedelta(hours=2)

        result = {
            'todo': self._get_todo_summary(ec_id, project_id, now, next_2h),
            'today_stats': self._get_today_stats(ec_id, project_id, today_start, today_end),
            'alerts': self._get_alerts(ec_id, project_id),
            'quick_actions': self._get_quick_actions(),
            'unread_count': self._get_unread_count(staff_id),
            'generated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        }

        cache_set(cache_key, result, self.CACHE_TTL)
        return result

    def _get_todo_summary(self, ec_id: int, project_id: int, now: datetime, next_2h: datetime) -> Dict:
        """获取待办汇总"""
        todo = {}

        # 待处理订单（已支付待发货）
        try:
            pending_ship = db.get_total("""
                SELECT COUNT(*) FROM business_orders
                WHERE order_status='paid' AND pay_status='paid'
                AND ec_id=%s AND project_id=%s
            """, [ec_id, project_id])
            todo['pending_ship'] = {
                'count': pending_ship,
                'label': '待发货订单',
                'icon': 'el-icon-sell',
                'route': '/orders?status=paid',
                'urgent': pending_ship > 10,
            }
        except Exception:
            todo['pending_ship'] = {'count': 0, 'label': '待发货订单', 'route': '/orders?status=paid', 'urgent': False}

        # 待处理售后
        try:
            pending_aftersales = 0
            # 检查售后表是否存在
            exists = db.get_one("SHOW TABLES LIKE 'business_aftersales'")
            if exists:
                pending_aftersales = db.get_total("""
                    SELECT COUNT(*) FROM business_aftersales
                    WHERE status='pending' AND ec_id=%s AND project_id=%s
                """, [ec_id, project_id])
            todo['pending_aftersales'] = {
                'count': pending_aftersales,
                'label': '待处理售后',
                'icon': 'el-icon-warning',
                'route': '/aftersales?status=pending',
                'urgent': pending_aftersales > 0,
            }
        except Exception:
            todo['pending_aftersales'] = {'count': 0, 'label': '待处理售后', 'route': '/aftersales', 'urgent': False}

        # 即将核销的预约（2小时内）
        try:
            upcoming_bookings = db.get_total("""
                SELECT COUNT(*) FROM business_venue_bookings
                WHERE status='confirmed'
                AND start_time BETWEEN %s AND %s
                AND ec_id=%s AND project_id=%s
            """, [now, next_2h, ec_id, project_id])
            todo['upcoming_bookings'] = {
                'count': upcoming_bookings,
                'label': '2小时内预约',
                'icon': 'el-icon-time',
                'route': '/bookings',
                'urgent': upcoming_bookings > 0,
            }
        except Exception:
            todo['upcoming_bookings'] = {'count': 0, 'label': '即将到期预约', 'route': '/bookings', 'urgent': False}

        # 库存预警商品数
        try:
            low_stock = db.get_total("""
                SELECT COUNT(*) FROM business_products
                WHERE stock <= COALESCE(low_stock_threshold, 10)
                AND stock > 0 AND deleted=0 AND status='active'
                AND ec_id=%s AND project_id=%s
            """, [ec_id, project_id])
            zero_stock = db.get_total("""
                SELECT COUNT(*) FROM business_products
                WHERE stock = 0 AND deleted=0 AND status='active'
                AND ec_id=%s AND project_id=%s
            """, [ec_id, project_id])
            todo['low_stock'] = {
                'count': low_stock,
                'zero_stock': zero_stock,
                'label': '库存预警',
                'icon': 'el-icon-goods',
                'route': '/products?filter=low_stock',
                'urgent': zero_stock > 0,
            }
        except Exception:
            todo['low_stock'] = {'count': 0, 'zero_stock': 0, 'label': '库存预警', 'route': '/products', 'urgent': False}

        # 未回复的用户评价
        try:
            unreplied_reviews = db.get_total("""
                SELECT COUNT(*) FROM business_reviews
                WHERE (reply IS NULL OR reply='') AND deleted=0
                AND ec_id=%s AND project_id=%s
            """, [ec_id, project_id])
            todo['unreplied_reviews'] = {
                'count': unreplied_reviews,
                'label': '待回复评价',
                'icon': 'el-icon-chat-dot-round',
                'route': '/reviews',
                'urgent': False,
            }
        except Exception:
            todo['unreplied_reviews'] = {'count': 0, 'label': '待回复评价', 'route': '/reviews', 'urgent': False}

        # 计算总待办数
        total = sum(v.get('count', 0) for v in todo.values() if isinstance(v, dict))
        todo['total'] = total

        return todo

    def _get_today_stats(self, ec_id: int, project_id: int, today_start: datetime, today_end: datetime) -> Dict:
        """获取今日业务统计"""
        stats = {}

        # 今日订单数与金额
        try:
            order_stat = db.get_one("""
                SELECT COUNT(*) as cnt, COALESCE(SUM(actual_amount), 0) as total_amount
                FROM business_orders
                WHERE created_at >= %s AND created_at < %s
                AND pay_status='paid'
                AND ec_id=%s AND project_id=%s
            """, [today_start, today_end, ec_id, project_id])
            stats['orders'] = {
                'count': order_stat.get('cnt', 0) if order_stat else 0,
                'amount': float(order_stat.get('total_amount', 0) or 0) if order_stat else 0,
            }
        except Exception:
            stats['orders'] = {'count': 0, 'amount': 0.0}

        # 今日新会员数
        try:
            new_members = db.get_total("""
                SELECT COUNT(*) FROM business_members
                WHERE created_at >= %s AND created_at < %s
                AND ec_id=%s AND project_id=%s
            """, [today_start, today_end, ec_id, project_id])
            stats['new_members'] = new_members
        except Exception:
            stats['new_members'] = 0

        # 今日签到数
        try:
            checkins = db.get_total("""
                SELECT COUNT(*) FROM business_checkin_logs
                WHERE checkin_date = %s AND ec_id=%s AND project_id=%s
            """, [today_start.date(), ec_id, project_id])
            stats['checkins'] = checkins
        except Exception:
            stats['checkins'] = 0

        # 今日退款数
        try:
            refunds = db.get_total("""
                SELECT COUNT(*) FROM business_orders
                WHERE refund_status IN ('refunding', 'refunded')
                AND updated_at >= %s AND updated_at < %s
                AND ec_id=%s AND project_id=%s
            """, [today_start, today_end, ec_id, project_id])
            stats['refunds'] = refunds
        except Exception:
            stats['refunds'] = 0

        return stats

    def _get_alerts(self, ec_id: int, project_id: int) -> List[Dict]:
        """获取需要关注的预警信息"""
        alerts = []

        # 超过24小时未处理的订单
        try:
            overdue_threshold = datetime.now() - timedelta(hours=24)
            overdue_orders = db.get_total("""
                SELECT COUNT(*) FROM business_orders
                WHERE order_status='paid' AND pay_status='paid'
                AND created_at <= %s
                AND ec_id=%s AND project_id=%s
            """, [overdue_threshold, ec_id, project_id])
            if overdue_orders > 0:
                alerts.append({
                    'type': 'danger',
                    'icon': 'el-icon-warning-outline',
                    'title': f'{overdue_orders} 单订单超过24小时未发货',
                    'action': '立即处理',
                    'route': '/orders?status=paid&overdue=1',
                })
        except Exception:
            pass

        # 零库存商品
        try:
            zero_stock = db.get_total("""
                SELECT COUNT(*) FROM business_products
                WHERE stock=0 AND deleted=0 AND status='active'
                AND ec_id=%s AND project_id=%s
            """, [ec_id, project_id])
            if zero_stock > 0:
                alerts.append({
                    'type': 'warning',
                    'icon': 'el-icon-goods',
                    'title': f'{zero_stock} 个商品已售罄，建议补货',
                    'action': '查看商品',
                    'route': '/products?filter=zero_stock',
                })
        except Exception:
            pass

        return alerts

    def _get_quick_actions(self) -> List[Dict]:
        """快捷操作入口"""
        return [
            {'label': '扫码核销', 'icon': 'el-icon-scan', 'route': '/scan-verify', 'color': '#00d1a0'},
            {'label': '新建订单', 'icon': 'el-icon-plus', 'route': '/orders/create', 'color': '#409EFF'},
            {'label': '查看预约', 'icon': 'el-icon-date', 'route': '/bookings', 'color': '#E6A23C'},
            {'label': '会员查询', 'icon': 'el-icon-user', 'route': '/members', 'color': '#909399'},
        ]

    def _get_unread_count(self, staff_id: int) -> int:
        """获取员工未读通知数"""
        try:
            count = db.get_total("""
                SELECT COUNT(*) FROM business_notifications
                WHERE user_id=%s AND is_read=0 AND deleted=0
            """, [staff_id])
            return count
        except Exception:
            return 0

    def get_workbench_stats_trend(
        self, ec_id: int, project_id: int, days: int = 7
    ) -> Dict:
        """
        获取最近N天的趋势数据（给工作台迷你图用）
        """
        result = []
        for i in range(days - 1, -1, -1):
            d = date.today() - timedelta(days=i)
            d_start = datetime.combine(d, datetime.min.time())
            d_end = d_start + timedelta(days=1)
            try:
                stat = db.get_one("""
                    SELECT COUNT(*) as cnt, COALESCE(SUM(actual_amount), 0) as amount
                    FROM business_orders
                    WHERE created_at >= %s AND created_at < %s
                    AND pay_status='paid'
                    AND ec_id=%s AND project_id=%s
                """, [d_start, d_end, ec_id, project_id])
                result.append({
                    'date': d.strftime('%m-%d'),
                    'order_count': stat.get('cnt', 0) if stat else 0,
                    'order_amount': float(stat.get('amount', 0) or 0) if stat else 0.0,
                })
            except Exception:
                result.append({'date': d.strftime('%m-%d'), 'order_count': 0, 'order_amount': 0.0})

        return {'days': days, 'trend': result}


# 全局单例
workbench_service = WorkbenchService()
