"""
V32.0 库存预警服务模块

功能:
- 库存阈值配置
- 低库存告警通知
- 库存不足自动处理
- 补货提醒

使用方式:
    from inventory_alert_service import inventory_alert_service

    # 检查商品库存
    inventory_alert_service.check_product_stock(product_id)

    # 批量检查所有商品
    inventory_alert_service.check_all_products(ec_id)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from . import db
from .service_base import BaseService
from .notification import send_notification

logger = logging.getLogger(__name__)


class InventoryAlertService(BaseService):
    """库存预警服务"""

    SERVICE_NAME = 'InventoryAlertService'

    # 默认阈值
    DEFAULT_LOW_STOCK_THRESHOLD = 10
    DEFAULT_CRITICAL_STOCK_THRESHOLD = 5

    # 检查批次大小
    BATCH_SIZE = 100

    def __init__(self):
        super().__init__()

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        base = super().health_check()
        try:
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_products LIMIT 1")
            base['db_status'] = 'connected'
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base

    # ============ 库存检查 ============

    def check_product_stock(self, product_id: int, ec_id: int = None) -> Dict[str, Any]:
        """
        检查单个商品库存状态

        Returns:
            {
                'success': True,
                'status': 'normal'|'low'|'critical'|'out_of_stock',
                'stock': 5,
                'threshold': 10,
                'need_alert': True
            }
        """
        try:
            sql = """
                SELECT id, name, stock,
                       COALESCE(stock_threshold, %s) as threshold
                FROM business_products
                WHERE id = %s AND deleted = 0
            """
            params = [self.DEFAULT_LOW_STOCK_THRESHOLD, product_id]

            if ec_id:
                sql += " AND ec_id = %s"
                params.append(ec_id)

            product = db.get_one(sql, params)

            if not product:
                return {'success': False, 'msg': '商品不存在'}

            stock = product.get('stock', 0)
            threshold = product.get('threshold', self.DEFAULT_LOW_STOCK_THRESHOLD)

            # 判断库存状态
            status = 'normal'
            need_alert = False

            if stock == 0:
                status = 'out_of_stock'
                need_alert = True
            elif stock <= self.DEFAULT_CRITICAL_STOCK_THRESHOLD:
                status = 'critical'
                need_alert = True
            elif stock <= threshold:
                status = 'low'
                need_alert = True

            return {
                'success': True,
                'product_id': product_id,
                'product_name': product.get('name'),
                'status': status,
                'stock': stock,
                'threshold': threshold,
                'need_alert': need_alert
            }

        except Exception as e:
            logger.error(f"[InventoryAlert] 检查库存失败: {e}")
            return {'success': False, 'msg': str(e)}

    def check_all_products(self, ec_id: int, project_id: int = None) -> Dict[str, Any]:
        """
        批量检查所有商品库存

        Returns:
            {
                'success': True,
                'total': 100,
                'normal_count': 80,
                'low_count': 15,
                'critical_count': 3,
                'out_of_stock_count': 2,
                'alerts': [...]
            }
        """
        try:
            conditions = ["p.deleted = 0", "p.ec_id = %s"]
            params = [ec_id]

            if project_id:
                conditions.append("p.project_id = %s")
                params.append(project_id)

            where = " AND ".join(conditions)

            # 查询低库存商品
            sql = f"""
                SELECT p.id, p.name, p.stock, p.ec_id, p.project_id,
                       COALESCE(p.stock_threshold, %s) as threshold,
                       c.name as category_name
                FROM business_products p
                LEFT JOIN business_product_categories c ON p.category_id = c.id
                WHERE {where}
                AND p.stock <= COALESCE(p.stock_threshold, %s)
                AND p.status = 'active'
                ORDER BY p.stock ASC
                LIMIT %s
            """
            params.extend([self.DEFAULT_LOW_STOCK_THRESHOLD, self.DEFAULT_LOW_STOCK_THRESHOLD, self.BATCH_SIZE])

            products = db.get_all(sql, params) or []

            # 分类统计
            stats = {
                'normal_count': 0,
                'low_count': 0,
                'critical_count': 0,
                'out_of_stock_count': 0
            }

            alerts = []

            for product in products:
                stock = product.get('stock', 0)
                threshold = product.get('threshold', self.DEFAULT_LOW_STOCK_THRESHOLD)

                if stock == 0:
                    stats['out_of_stock_count'] += 1
                    alert_level = 'critical'
                elif stock <= self.DEFAULT_CRITICAL_STOCK_THRESHOLD:
                    stats['critical_count'] += 1
                    alert_level = 'critical'
                elif stock <= threshold:
                    stats['low_count'] += 1
                    alert_level = 'warning'
                else:
                    stats['normal_count'] += 1
                    continue

                alerts.append({
                    'product_id': product['id'],
                    'product_name': product['name'],
                    'category_name': product.get('category_name'),
                    'stock': stock,
                    'threshold': threshold,
                    'alert_level': alert_level,
                    'shortage': threshold - stock
                })

            # 发送预警通知
            if alerts:
                self._send_alert_notifications(alerts, ec_id, project_id)

            logger.info(f"[InventoryAlert] 库存检查完成: 低库存{len(alerts)}个")

            return {
                'success': True,
                'total': len(products) + stats['normal_count'],
                'alerts': alerts,
                **stats
            }

        except Exception as e:
            logger.error(f"[InventoryAlert] 批量检查失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ 库存阈值配置 ============

    def set_product_threshold(self, product_id: int, threshold: int,
                            ec_id: int = None) -> Dict[str, Any]:
        """设置商品库存阈值"""
        try:
            sql = "UPDATE business_products SET stock_threshold = %s WHERE id = %s"
            params = [threshold, product_id]

            if ec_id:
                sql += " AND ec_id = %s"
                params.append(ec_id)

            affected = db.execute(sql, params)

            if affected == 0:
                return {'success': False, 'msg': '商品不存在'}

            logger.info(f"[InventoryAlert] 设置阈值: product_id={product_id}, threshold={threshold}")

            return {'success': True, 'msg': '阈值设置成功'}

        except Exception as e:
            logger.error(f"[InventoryAlert] 设置阈值失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_threshold_config(self, ec_id: int) -> Dict[str, Any]:
        """获取阈值配置"""
        try:
            sql = """
                SELECT
                    COALESCE(AVG(stock_threshold), %s) as avg_threshold,
                    MIN(stock_threshold) as min_threshold,
                    MAX(stock_threshold) as max_threshold,
                    COUNT(DISTINCT stock_threshold) as distinct_count
                FROM business_products
                WHERE ec_id = %s AND deleted = 0
            """
            result = db.get_one(sql, [self.DEFAULT_LOW_STOCK_THRESHOLD, ec_id])

            return {
                'success': True,
                'default_threshold': self.DEFAULT_LOW_STOCK_THRESHOLD,
                'critical_threshold': self.DEFAULT_CRITICAL_STOCK_THRESHOLD,
                'avg_threshold': float(result.get('avg_threshold', 0)) if result else self.DEFAULT_LOW_STOCK_THRESHOLD,
                'min_threshold': result.get('min_threshold') if result else None,
                'max_threshold': result.get('max_threshold') if result else None
            }

        except Exception as e:
            logger.error(f"[InventoryAlert] 获取阈值配置失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ 自动处理 ============

    def auto_offline_out_of_stock(self, ec_id: int = None) -> Dict[str, Any]:
        """
        自动下架无库存商品

        Args:
            ec_id: 企业ID(可选)

        Returns:
            {'success': True, 'offlined_count': 5}
        """
        try:
            conditions = ["stock = 0", "status = 'active'", "deleted = 0"]
            params = []

            if ec_id:
                conditions.append("ec_id = %s")
                params.append(ec_id)

            where = " AND ".join(conditions)

            # 先查询要下架的商品
            query_sql = f"SELECT id, name FROM business_products WHERE {where}"
            products = db.get_all(query_sql, params) or []

            if not products:
                return {'success': True, 'offlined_count': 0}

            # 执行下架
            update_sql = f"UPDATE business_products SET status = 'offline' WHERE {where}"
            affected = db.execute(update_sql, params)

            logger.info(f"[InventoryAlert] 自动下架无库存商品: {len(products)}个")

            return {
                'success': True,
                'offlined_count': affected,
                'products': [{'id': p['id'], 'name': p['name']} for p in products]
            }

        except Exception as e:
            logger.error(f"[InventoryAlert] 自动下架失败: {e}")
            return {'success': False, 'msg': str(e)}

    def auto_reshelve(self, product_id: int, ec_id: int = None) -> Dict[str, Any]:
        """
        自动重新上架有库存商品

        Args:
            product_id: 商品ID
            ec_id: 企业ID

        Returns:
            {'success': True, 'reshelved': True}
        """
        try:
            # 查询商品当前库存
            sql = "SELECT stock, status FROM business_products WHERE id = %s"
            params = [product_id]

            if ec_id:
                sql += " AND ec_id = %s"
                params.append(ec_id)

            product = db.get_one(sql, params)

            if not product:
                return {'success': False, 'msg': '商品不存在'}

            # 如果有库存且当前是offline状态，则上架
            if product.get('stock', 0) > 0 and product.get('status') == 'offline':
                update_sql = "UPDATE business_products SET status = 'active' WHERE id = %s"
                db.execute(update_sql, [product_id])

                logger.info(f"[InventoryAlert] 自动上架商品: product_id={product_id}")

                return {'success': True, 'reshelved': True, 'msg': '商品已重新上架'}

            return {'success': True, 'reshelved': False, 'msg': '无需处理'}

        except Exception as e:
            logger.error(f"[InventoryAlert] 自动上架失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ 通知 ============

    def _send_alert_notifications(self, alerts: List[Dict], ec_id: int,
                                 project_id: int = None):
        """发送预警通知"""
        if not alerts:
            return

        try:
            # 按严重程度分组
            critical = [a for a in alerts if a['alert_level'] == 'critical']
            warning = [a for a in alerts if a['alert_level'] == 'warning']

            # 构建通知内容
            if critical:
                content = f"紧急！以下{len(critical)}个商品库存严重不足:\n"
                for a in critical[:5]:  # 最多显示5个
                    content += f"- {a['product_name']}: 剩余{a['stock']}件\n"
                if len(critical) > 5:
                    content += f"...还有{len(critical)-5}个\n"

                # 查找管理员发送通知
                self._notify_admins(ec_id, project_id,
                                   title='⚠️库存紧急预警',
                                   content=content)

            if warning:
                content = f"以下{len(warning)}个商品库存偏低:\n"
                for a in warning[:5]:
                    content += f"- {a['product_name']}: 剩余{a['stock']}件\n"

                self._notify_admins(ec_id, project_id,
                                   title='📦库存预警提醒',
                                   content=content)

        except Exception as e:
            logger.error(f"[InventoryAlert] 发送预警通知失败: {e}")

    def _notify_admins(self, ec_id: int, project_id: int,
                      title: str, content: str):
        """通知管理员"""
        try:
            # 查询企业管理员
            sql = """
                SELECT DISTINCT user_id
                FROM business_staff
                WHERE ec_id = %s AND role = 'admin'
            """
            params = [ec_id]

            if project_id:
                sql += " AND project_id = %s"
                params.append(project_id)

            admins = db.get_all(sql, params) or []

            for admin in admins:
                send_notification(
                    user_id=admin['user_id'],
                    title=title,
                    content=content,
                    type='inventory_alert',
                    ec_id=ec_id,
                    project_id=project_id
                )

        except Exception as e:
            logger.error(f"[InventoryAlert] 通知管理员失败: {e}")

    # ============ 库存预警记录 ============

    def get_alert_history(self, ec_id: int, start_date: str = None,
                         end_date: str = None, page: int = 1,
                         page_size: int = 20) -> Dict[str, Any]:
        """获取预警历史"""
        try:
            conditions = ["ec_id = %s"]
            params = [ec_id]

            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date)

            where = " AND ".join(conditions)

            # 统计
            count_sql = f"SELECT COUNT(*) as total FROM business_inventory_alerts WHERE {where}"
            count_result = db.get_one(count_sql, params)
            total = count_result.get('total', 0) if count_result else 0

            # 分页查询
            offset = (page - 1) * page_size
            sql = f"""
                SELECT * FROM business_inventory_alerts
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])

            alerts = db.get_all(sql, params) or []

            return {
                'success': True,
                'alerts': alerts,
                'total': total,
                'page': page,
                'page_size': page_size
            }

        except Exception as e:
            logger.error(f"[InventoryAlert] 获取预警历史失败: {e}")
            return {'success': False, 'msg': str(e)}

    def save_alert_record(self, product_id: int, alert_type: str,
                        stock_before: int, stock_after: int,
                        ec_id: int, project_id: int = None) -> Dict[str, Any]:
        """保存预警记录"""
        try:
            sql = """
                INSERT INTO business_inventory_alerts (
                    product_id, alert_type, stock_before, stock_after,
                    ec_id, project_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            db.execute(sql, [product_id, alert_type, stock_before,
                            stock_after, ec_id, project_id])
            return {'success': True}

        except Exception as e:
            # 表可能不存在，静默失败
            logger.debug(f"[InventoryAlert] 保存记录失败: {e}")
            return {'success': False, 'msg': str(e)}


# 单例实例
inventory_alert_service = InventoryAlertService()
