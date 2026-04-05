"""
管理端运营分析服务 V26.0

目标：
1. 为管理端首页/运营看板提供真实业务数据，替换模拟数据
2. 沉淀复杂统计查询，缓解 business-admin/app.py 继续膨胀
3. 输出产品经理可直接使用的经营洞察、转化漏斗与风险预警
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

from . import db

logger = logging.getLogger(__name__)


class AdminAnalyticsService:
    """管理端运营分析服务"""

    def _append_scope_filters(self, clauses: List[str], params: List, ec_id=None, project_id=None, alias: str = "") -> Tuple[List[str], List]:
        prefix = f"{alias}." if alias else ""
        if ec_id not in (None, ""):
            clauses.append(f"{prefix}ec_id=%s")
            params.append(ec_id)
        if project_id not in (None, ""):
            clauses.append(f"{prefix}project_id=%s")
            params.append(project_id)
        return clauses, params

    def _safe_get_one(self, sql: str, params=None) -> Dict:
        try:
            return db.get_one(sql, params or []) or {}
        except Exception as exc:
            logger.warning("analytics get_one failed: %s", exc)
            return {}

    def _safe_get_all(self, sql: str, params=None) -> List[Dict]:
        try:
            return db.get_all(sql, params or []) or []
        except Exception as exc:
            logger.warning("analytics get_all failed: %s", exc)
            return []

    def _safe_get_total(self, sql: str, params=None) -> int:
        try:
            return int(db.get_total(sql, params or []) or 0)
        except Exception as exc:
            logger.warning("analytics get_total failed: %s", exc)
            return 0

    def _safe_float(self, value, digits: int = 2) -> float:
        try:
            return round(float(value or 0), digits)
        except Exception:
            return 0.0

    def _calc_change_rate(self, current: float, previous: float) -> float:
        current = float(current or 0)
        previous = float(previous or 0)
        if previous <= 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)

    def _calc_ratio(self, numerator: float, denominator: float) -> float:
        numerator = float(numerator or 0)
        denominator = float(denominator or 0)
        if denominator <= 0:
            return 0.0
        return round((numerator / denominator) * 100, 2)


    def _get_period_bounds(self, days: int) -> Dict[str, datetime]:
        days = max(1, min(int(days or 30), 90))
        today = date.today()
        current_start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time())
        current_end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        previous_start = current_start - timedelta(days=days)
        previous_end = current_start
        return {
            "days": days,
            "current_start": current_start,
            "current_end": current_end,
            "previous_start": previous_start,
            "previous_end": previous_end,
        }

    def get_trend(self, days: int = 30, ec_id=None, project_id=None) -> Dict:
        bounds = self._get_period_bounds(days)
        clauses = ["deleted=0", "created_at >= %s", "created_at < %s"]
        params = [bounds["current_start"], bounds["current_end"]]
        clauses, params = self._append_scope_filters(clauses, params, ec_id, project_id)
        where_sql = " AND ".join(clauses)

        rows = self._safe_get_all(
            f"""
            SELECT DATE(created_at) as d,
                   COUNT(*) as order_count,
                   COALESCE(SUM(CASE WHEN pay_status='paid' THEN actual_amount ELSE 0 END), 0) as total_amount
            FROM business_orders
            WHERE {where_sql}
            GROUP BY DATE(created_at)
            ORDER BY d ASC
            """,
            params,
        )

        day_map = {}
        for row in rows:
            key = str(row.get("d")) if row.get("d") else ""
            if not key:
                continue
            day_map[key] = {
                "order_count": int(row.get("order_count") or 0),
                "total_amount": self._safe_float(row.get("total_amount")),
            }

        dates = []
        orders = []
        income = []
        trend = []
        for i in range(bounds["days"]):
            current_day = bounds["current_start"] + timedelta(days=i)
            key = current_day.strftime("%Y-%m-%d")
            metric = day_map.get(key, {"order_count": 0, "total_amount": 0.0})
            dates.append(key)
            orders.append(metric["order_count"])
            income.append(metric["total_amount"])
            trend.append({
                "date": key,
                "order_count": metric["order_count"],
                "total_amount": metric["total_amount"],
            })

        return {
            "days": bounds["days"],
            "dates": dates,
            "orders": orders,
            "income": income,
            "trend": trend,
        }

    def get_top_products(self, ec_id=None, project_id=None, days: int = 30, limit: int = 10) -> List[Dict]:
        bounds = self._get_period_bounds(days)
        limit = max(1, min(int(limit or 10), 20))
        clauses = ["o.deleted=0", "o.pay_status='paid'", "o.created_at >= %s", "o.created_at < %s"]
        params = [bounds["current_start"], bounds["current_end"]]
        clauses, params = self._append_scope_filters(clauses, params, ec_id, project_id, alias="o")
        where_sql = " AND ".join(clauses)

        rows = self._safe_get_all(
            f"""
            SELECT oi.product_id,
                   MAX(oi.product_name) as product_name,
                   SUM(oi.quantity) as sales_count,
                   COUNT(DISTINCT o.id) as order_count,
                   COALESCE(SUM(oi.subtotal), 0) as total_amount
            FROM business_order_items oi
            INNER JOIN business_orders o ON o.id = oi.order_id
            WHERE {where_sql}
            GROUP BY oi.product_id
            ORDER BY total_amount DESC, sales_count DESC
            LIMIT %s
            """,
            params + [limit],
        )

        result = []
        for row in rows:
            result.append({
                "product_id": row.get("product_id"),
                "product_name": row.get("product_name") or "未命名商品",
                "name": row.get("product_name") or "未命名商品",
                "sales_count": int(row.get("sales_count") or 0),
                "sales": int(row.get("sales_count") or 0),
                "order_count": int(row.get("order_count") or 0),
                "total_amount": self._safe_float(row.get("total_amount")),
            })
        return result

    def get_top_shops(self, ec_id=None, project_id=None, days: int = 30, limit: int = 10) -> List[Dict]:
        bounds = self._get_period_bounds(days)
        limit = max(1, min(int(limit or 10), 20))
        clauses = ["s.deleted=0"]
        params: List = []
        clauses, params = self._append_scope_filters(clauses, params, ec_id, project_id, alias="s")
        where_sql = " AND ".join(clauses)

        rows = self._safe_get_all(
            f"""
            SELECT s.id,
                   s.shop_name,
                   COALESCE(SUM(CASE WHEN o.pay_status='paid' THEN oi.subtotal ELSE 0 END), 0) as total_amount,
                   COALESCE(SUM(CASE WHEN o.pay_status='paid' THEN oi.quantity ELSE 0 END), 0) as total_quantity,
                   COUNT(DISTINCT CASE WHEN o.pay_status='paid' THEN o.id END) as order_count
            FROM business_shops s
            LEFT JOIN business_products p ON p.shop_id = s.id AND p.deleted=0
            LEFT JOIN business_order_items oi ON oi.product_id = p.id
            LEFT JOIN business_orders o ON o.id = oi.order_id
                AND o.deleted=0
                AND o.created_at >= %s
                AND o.created_at < %s
            WHERE {where_sql}
            GROUP BY s.id, s.shop_name
            HAVING total_amount > 0
            ORDER BY total_amount DESC, total_quantity DESC
            LIMIT %s
            """,
            [bounds["current_start"], bounds["current_end"]] + params + [limit],
        )

        result = []
        for row in rows:
            result.append({
                "shop_id": row.get("id"),
                "shop_name": row.get("shop_name") or "未命名门店",
                "total_amount": self._safe_float(row.get("total_amount")),
                "order_count": int(row.get("order_count") or 0),
                "total_quantity": int(row.get("total_quantity") or 0),
            })
        return result

    def get_alerts(self, ec_id=None, project_id=None) -> List[Dict]:
        base_where = ["deleted=0"]
        base_params: List = []
        base_where, base_params = self._append_scope_filters(base_where, base_params, ec_id, project_id)
        scoped_sql = " AND ".join(base_where)

        low_stock = self._safe_get_total(
            f"SELECT COUNT(*) FROM business_products WHERE {scoped_sql} AND stock >= 0 AND stock <= 5"
            , base_params,
        )
        overdue_apps = self._safe_get_total(
            f"SELECT COUNT(*) FROM business_applications WHERE {scoped_sql} AND status IN ('pending', 'processing') AND created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)",
            base_params,
        )
        refund_pending = self._safe_get_total(
            f"SELECT COUNT(*) FROM business_orders WHERE {scoped_sql} AND (refund_status IN ('pending', 'requested') OR order_status='refunding')",
            base_params,
        )
        waiting_ship = self._safe_get_total(
            f"SELECT COUNT(*) FROM business_orders WHERE {scoped_sql} AND pay_status='paid' AND order_status='paid' AND created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)",
            base_params,
        )

        alerts: List[Dict] = []
        if overdue_apps > 0:
            alerts.append({
                "level": "high" if overdue_apps >= 10 else "medium",
                "title": "超时申请待处理",
                "count": overdue_apps,
                "description": "存在超过24小时仍未完成处理的申请单，建议优先清理。",
            })
        if refund_pending > 0:
            alerts.append({
                "level": "high" if refund_pending >= 5 else "medium",
                "title": "退款工单积压",
                "count": refund_pending,
                "description": "退款申请尚未闭环，可能影响用户满意度与资金对账。",
            })
        if waiting_ship > 0:
            alerts.append({
                "level": "medium",
                "title": "已支付未发货订单",
                "count": waiting_ship,
                "description": "存在超过24小时未发货的已支付订单，建议安排履约排查。",
            })
        if low_stock > 0:
            alerts.append({
                "level": "low" if low_stock < 10 else "medium",
                "title": "库存预警商品",
                "count": low_stock,
                "description": "库存低于安全阈值的商品需要补货或下架，避免前端售卖体验下降。",
            })
        if not alerts:
            alerts.append({
                "level": "success",
                "title": "当前无显著经营风险",
                "count": 0,
                "description": "订单履约、退款处理与库存状态整体平稳。",
            })
        return alerts

    def get_overview(self, days: int = 30, ec_id=None, project_id=None) -> Dict:
        bounds = self._get_period_bounds(days)

        order_where = ["deleted=0"]
        order_params: List = []
        order_where, order_params = self._append_scope_filters(order_where, order_params, ec_id, project_id)
        order_scope_sql = " AND ".join(order_where)

        current_orders = self._safe_get_one(
            f"""
            SELECT COUNT(*) as total_orders,
                   COUNT(DISTINCT CASE WHEN pay_status='paid' THEN user_id END) as pay_users,
                   COALESCE(SUM(CASE WHEN pay_status='paid' THEN actual_amount ELSE 0 END), 0) as total_income,
                   COALESCE(SUM(CASE WHEN pay_status='paid' AND order_type='product' THEN actual_amount ELSE 0 END), 0) as order_income,
                   COALESCE(SUM(CASE WHEN pay_status='paid' AND order_type='booking' THEN actual_amount ELSE 0 END), 0) as booking_income,
                   COALESCE(SUM(CASE WHEN pay_status='paid' AND order_type='seckill' THEN actual_amount ELSE 0 END), 0) as seckill_income,
                   COALESCE(SUM(CASE WHEN pay_status='paid' AND order_type='group_buy' THEN actual_amount ELSE 0 END), 0) as group_buy_income
            FROM business_orders
            WHERE {order_scope_sql} AND created_at >= %s AND created_at < %s
            """,
            order_params + [bounds["current_start"], bounds["current_end"]],
        )
        previous_orders = self._safe_get_one(
            f"""
            SELECT COUNT(*) as total_orders,
                   COALESCE(SUM(CASE WHEN pay_status='paid' THEN actual_amount ELSE 0 END), 0) as total_income
            FROM business_orders
            WHERE {order_scope_sql} AND created_at >= %s AND created_at < %s
            """,
            order_params + [bounds["previous_start"], bounds["previous_end"]],
        )

        member_where = ["deleted=0"]
        member_params: List = []
        member_where, member_params = self._append_scope_filters(member_where, member_params, ec_id, project_id)
        member_scope_sql = " AND ".join(member_where)
        current_members = self._safe_get_total(
            f"SELECT COUNT(*) FROM business_members WHERE {member_scope_sql} AND created_at >= %s AND created_at < %s",
            member_params + [bounds["current_start"], bounds["current_end"]],
        )
        previous_members = self._safe_get_total(
            f"SELECT COUNT(*) FROM business_members WHERE {member_scope_sql} AND created_at >= %s AND created_at < %s",
            member_params + [bounds["previous_start"], bounds["previous_end"]],
        )

        review_where = ["deleted=0"]
        review_params: List = []
        review_where, review_params = self._append_scope_filters(review_where, review_params, ec_id, project_id)
        review_scope_sql = " AND ".join(review_where)
        rating_row = self._safe_get_one(
            f"SELECT ROUND(COALESCE(AVG(rating), 0), 1) as avg_rating, COUNT(*) as review_count FROM business_reviews WHERE {review_scope_sql} AND created_at >= %s AND created_at < %s",
            review_params + [bounds["current_start"], bounds["current_end"]],
        )

        active_shops = len(self.get_top_shops(ec_id=ec_id, project_id=project_id, days=bounds["days"], limit=100))
        if active_shops == 0:
            shop_where = ["deleted=0", "status='open'"]
            shop_params: List = []
            shop_where, shop_params = self._append_scope_filters(shop_where, shop_params, ec_id, project_id)
            active_shops = self._safe_get_total(
                f"SELECT COUNT(*) FROM business_shops WHERE {' AND '.join(shop_where)}",
                shop_params,
            )

        search_where = ["searched_at >= %s", "searched_at < %s"]
        search_params: List = [bounds["current_start"], bounds["current_end"]]
        search_where, search_params = self._append_scope_filters(search_where, search_params, ec_id, project_id)
        browse_users = self._safe_get_total(
            f"SELECT COUNT(DISTINCT user_id) FROM business_search_history WHERE {' AND '.join(search_where)}",
            search_params,
        )

        cart_where = ["updated_at >= %s", "updated_at < %s"]
        cart_params: List = [bounds["current_start"], bounds["current_end"]]
        cart_where, cart_params = self._append_scope_filters(cart_where, cart_params, ec_id, project_id)
        cart_users = self._safe_get_total(
            f"SELECT COUNT(DISTINCT user_id) FROM business_cart WHERE {' AND '.join(cart_where)}",
            cart_params,
        )

        favorite_where = ["created_at >= %s", "created_at < %s"]
        favorite_params: List = [bounds["current_start"], bounds["current_end"]]
        favorite_where, favorite_params = self._append_scope_filters(favorite_where, favorite_params, ec_id, project_id)
        favorite_users = self._safe_get_total(
            f"SELECT COUNT(DISTINCT user_id) FROM business_favorites WHERE {' AND '.join(favorite_where)}",
            favorite_params,
        )

        visitor_users = self._safe_get_total(
            f"""
            SELECT COUNT(DISTINCT user_id) FROM (
                SELECT user_id FROM business_orders WHERE {order_scope_sql} AND created_at >= %s AND created_at < %s
                UNION ALL
                SELECT user_id FROM business_applications WHERE {' AND '.join(self._append_scope_filters(['deleted=0'], [], ec_id, project_id)[0])} AND created_at >= %s AND created_at < %s
                UNION ALL
                SELECT user_id FROM business_cart WHERE {' AND '.join(cart_where)}
                UNION ALL
                SELECT user_id FROM business_search_history WHERE {' AND '.join(search_where)}
            ) t
            """,
            order_params + [bounds["current_start"], bounds["current_end"]]
            + self._append_scope_filters(['deleted=0'], [], ec_id, project_id)[1] + [bounds["current_start"], bounds["current_end"]]
            + cart_params
            + search_params,
        )
        visitor_users = max(visitor_users, browse_users, cart_users, int(current_orders.get("pay_users") or 0), favorite_users)

        top_products = self.get_top_products(ec_id=ec_id, project_id=project_id, days=bounds["days"], limit=10)
        top_members = self._safe_get_all(
            f"""
            SELECT user_id, MAX(user_name) as user_name,
                   COUNT(*) as order_count,
                   COALESCE(SUM(actual_amount), 0) as total_amount
            FROM business_orders
            WHERE {order_scope_sql} AND pay_status='paid' AND created_at >= %s AND created_at < %s
            GROUP BY user_id
            ORDER BY total_amount DESC, order_count DESC
            LIMIT 10
            """,
            order_params + [bounds["current_start"], bounds["current_end"]],
        )

        pay_users = int(current_orders.get("pay_users") or 0)
        funnel = {
            "visitors": int(visitor_users or 0),
            "browse": int(max(browse_users, favorite_users) or 0),
            "cart": int(cart_users or 0),
            "pay": pay_users,
        }
        funnel["browse_rate"] = self._calc_change_rate(funnel["browse"], funnel["visitors"]) if funnel["visitors"] else 0.0
        funnel["cart_rate"] = self._calc_change_rate(funnel["cart"], funnel["browse"]) if funnel["browse"] else 0.0
        funnel["pay_rate"] = self._calc_change_rate(funnel["pay"], funnel["cart"]) if funnel["cart"] else 0.0

        total_income = self._safe_float(current_orders.get("total_income"))
        total_orders = int(current_orders.get("total_orders") or 0)
        result = {
            "days": bounds["days"],
            "period": {
                "current_start": bounds["current_start"].strftime("%Y-%m-%d"),
                "current_end": (bounds["current_end"] - timedelta(days=1)).strftime("%Y-%m-%d"),
                "previous_start": bounds["previous_start"].strftime("%Y-%m-%d"),
                "previous_end": (bounds["previous_end"] - timedelta(days=1)).strftime("%Y-%m-%d"),
            },
            "totalIncome": total_income,
            "totalOrders": total_orders,
            "newMembers": int(current_members or 0),
            "activeShops": int(active_shops or 0),
            "avgRating": self._safe_float(rating_row.get("avg_rating"), 1),
            "reviewCount": int(rating_row.get("review_count") or 0),
            "incomeChange": self._calc_change_rate(total_income, self._safe_float(previous_orders.get("total_income"))),
            "ordersChange": self._calc_change_rate(total_orders, int(previous_orders.get("total_orders") or 0)),
            "membersChange": self._calc_change_rate(int(current_members or 0), int(previous_members or 0)),
            "orderIncome": self._safe_float(current_orders.get("order_income")),
            "bookingIncome": self._safe_float(current_orders.get("booking_income")),
            "seckillIncome": self._safe_float(current_orders.get("seckill_income")),
            "groupBuyIncome": self._safe_float(current_orders.get("group_buy_income")),
            "visitors": funnel["visitors"],
            "browseUsers": funnel["browse"],
            "cartUsers": funnel["cart"],
            "payUsers": funnel["pay"],
            "funnel": funnel,
            "productRank": top_products,
            "memberRank": [
                {
                    "user_id": row.get("user_id"),
                    "user_name": row.get("user_name") or "匿名用户",
                    "order_count": int(row.get("order_count") or 0),
                    "total_amount": self._safe_float(row.get("total_amount")),
                }
                for row in top_members
            ],
            "alerts": self.get_alerts(ec_id=ec_id, project_id=project_id),
        }
        return result


analytics_service = AdminAnalyticsService()
