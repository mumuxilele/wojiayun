"""
V32.0 订单服务模块 → V43.0安全修复
提供统一的订单业务逻辑封装

功能清单:
- 订单创建 (支持普通订单/拼团订单)
- 订单查询 (多条件筛选)
- 订单状态流转
- 订单取消与退款
- 超时订单自动处理
- 订单统计与分析

V43.0安全修复:
- order_by参数白名单验证（防止SQL注入）

依赖:
- payment_service: 支付服务
- inventory_service: 库存服务 (待实现)
- notification_service: 通知服务
"""

import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from . import db
from .service_base import BaseService, CRUDService
from .order_status import OrderStatus, OrderStatusTransition, OrderStatusValidator

logger = logging.getLogger(__name__)

# V43.0新增：ORDER BY白名单验证，防止SQL注入
ALLOWED_ORDER_FIELDS = {
    'created_at', 'updated_at', 'actual_amount', 'order_status', 
    'pay_status', 'id', 'order_no', 'total_amount', 'pay_time'
}
ALLOWED_ORDER_DIRS = {'ASC', 'DESC', 'asc', 'desc'}


def _validate_order_by(order_by: str) -> str:
    """
    V43.0安全修复：验证并规范化order_by参数
    防止SQL注入攻击，只允许预定义的安全字段和方向组合
    """
    if not order_by:
        return 'created_at DESC'
    
    # 移除所有SQL关键字和注释
    dangerous_patterns = [
        r'(?i)\b(union|select|insert|update|delete|drop|exec|execute|script)\b',
        r'--', r'/\*', r'\*/', r';', r'@', r'0x',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, order_by):
            logger.warning(f"SQL注入攻击尝试被拦截: {order_by}")
            return 'created_at DESC'
    
    # 解析字段和方向
    parts = [p.strip() for p in order_by.split()]
    field = parts[0] if parts else 'created_at'
    direction = parts[1].upper() if len(parts) > 1 else 'DESC'
    
    # 白名单验证
    if field not in ALLOWED_ORDER_FIELDS:
        logger.warning(f"order_by字段不在白名单中: {field}, 使用默认值")
        field = 'created_at'
    
    if direction not in ALLOWED_ORDER_DIRS:
        direction = 'DESC'
    
    return f"{field} {direction}"

# V35.0新增：库存锁配置
STOCK_LOCK_TIMEOUT = 5  # 库存锁超时时间（秒）
MAX_RETRY_ATTEMPTS = 3  # 库存扣减最大重试次数


class OrderService(BaseService):
    """订单服务"""

    SERVICE_NAME = 'OrderService'

    # 订单超时配置 (分钟)
    ORDER_EXPIRE_MINUTES = 30

    # 批量处理配置
    BATCH_SIZE = 100

    # 状态流转映射
    STATUS_TRANSITIONS = {
        'pending': ['paid', 'cancelled', 'expired'],
        'paid': ['processing', 'refunding', 'refunded'],
        'processing': ['completed', 'refunding'],
        'completed': ['refunding'],  # 售后退款
        'refunding': ['refunded', 'paid'],  # 拒绝退款退回
        'cancelled': [],
        'expired': [],
        'refunded': [],
    }

    def __init__(self):
        super().__init__()
        self.validator = OrderStatusValidator()

    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        # 添加订单相关健康指标
        try:
            # 检查数据库连接
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_orders LIMIT 1")
            base['db_status'] = 'connected'
            base['order_count'] = result.get('cnt', 0) if result else 0
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base

    # ============ 订单创建 ============

    def create_order(self, user_id: int, items: List[Dict],
                    ec_id: int, project_id: int,
                    address_id: Optional[int] = None,
                    remark: str = '',
                    order_type: str = 'normal',
                    **kwargs) -> Dict[str, Any]:
        """
        创建订单

        Args:
            user_id: 用户ID
            items: 商品明细 [{"product_id": 1, "sku_id": 1, "quantity": 2, "price": 99.9}]
            ec_id: 企业ID
            project_id: 项目ID
            address_id: 收货地址ID
            remark: 订单备注
            order_type: 订单类型 (normal/groupbuy)
            **kwargs: 其他参数 (coupon_id等)

        Returns:
            Dict: {"success": True, "order_no": "xxx", "total_amount": 199.8}
        """
        try:
            # 1. 计算订单金额
            total_amount = 0
            product_details = []

            for item in items:
                product_id = item.get('product_id')
                sku_id = item.get('sku_id')
                quantity = item.get('quantity', 1)

                # 查询商品信息
                product_sql = """
                    SELECT p.*, ps.price as sku_price, ps.stock as sku_stock, ps.sku_code
                    FROM business_products p
                    LEFT JOIN business_product_skus ps ON ps.product_id = p.id
                    WHERE p.id = %s AND p.ec_id = %s AND p.project_id = %s
                    AND p.status = 'active' AND p.deleted = 0
                """
                params = [product_id, ec_id, project_id]

                if sku_id:
                    product_sql += " AND ps.id = %s"
                    params.append(sku_id)

                product = db.get_one(product_sql, params)

                if not product:
                    return {'success': False, 'msg': f'商品不存在: {product_id}'}

                if product.get('sku_stock', 0) < quantity:
                    return {'success': False, 'msg': f'商品库存不足: {product["name"]}'}

                item_amount = float(product.get('sku_price', product.get('price', 0))) * quantity
                total_amount += item_amount

                product_details.append({
                    'product_id': product_id,
                    'sku_id': sku_id or None,
                    'product_name': product['name'],
                    'sku_info': product.get('sku_code'),
                    'quantity': quantity,
                    'price': float(product.get('sku_price', product.get('price', 0))),
                    'amount': item_amount,
                })

            # 2. 应用优惠券
            coupon_id = kwargs.get('coupon_id')
            discount_amount = 0
            if coupon_id:
                discount_result = self._apply_coupon(user_id, coupon_id, total_amount)
                if discount_result['success']:
                    discount_amount = discount_result['discount']
                    total_amount = total_amount - discount_amount

            # 3. 生成订单号
            order_no = self._generate_order_no()

            # 4. 保存订单主表
            now = datetime.now()
            expire_time = now + timedelta(minutes=self.ORDER_EXPIRE_MINUTES)

            order_sql = """
                INSERT INTO business_orders (
                    order_no, order_type, user_id, ec_id, project_id,
                    total_amount, discount_amount, actual_amount,
                    address_id, remark, order_status, pay_status,
                    created_at, updated_at, expire_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            order_params = [
                order_no, order_type, user_id, ec_id, project_id,
                total_amount + discount_amount, discount_amount, total_amount,
                address_id, remark, 'pending', 'unpaid',
                now, now, expire_time
            ]

            db.execute(order_sql, order_params)

            # 获取订单ID
            order_result = db.get_one("SELECT LAST_INSERT_ID() as id")
            order_id = order_result['id'] if order_result else 0

            # 5. 保存订单明细
            for detail in product_details:
                detail_sql = """
                    INSERT INTO business_order_details (
                        order_id, product_id, sku_id, product_name,
                        sku_info, quantity, price, amount
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                detail_params = [
                    order_id, detail['product_id'], detail['sku_id'],
                    detail['product_name'], detail['sku_info'],
                    detail['quantity'], detail['price'], detail['amount']
                ]
                db.execute(detail_sql, detail_params)

                # 6. 锁定库存 - V35.0使用悲观锁
                try:
                    if detail['sku_id']:
                        self._lock_stock_with_retry(detail['sku_id'], detail['quantity'])
                    else:
                        self._lock_stock_with_retry(detail['product_id'], detail['quantity'], is_product=True)
                except Exception as e:
                    # 库存锁定失败，回滚已锁定的库存
                    for prev_detail in product_details[:product_details.index(detail)]:
                        if prev_detail['sku_id']:
                            self._unlock_stock(prev_detail['sku_id'], prev_detail['quantity'])
                        else:
                            self._unlock_stock(prev_detail['product_id'], prev_detail['quantity'], is_product=True)
                    return {'success': False, 'msg': f'商品库存不足: {detail["product_name"]}'}

            # 7. 扣减优惠券
            if coupon_id:
                self._use_coupon(user_id, coupon_id)

            logger.info(f"[OrderService] 创建订单成功: {order_no}, 金额: {total_amount}")

            return {
                'success': True,
                'order_id': order_id,
                'order_no': order_no,
                'total_amount': total_amount,
                'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S'),
                'msg': '订单创建成功'
            }

        except Exception as e:
            logger.error(f"[OrderService] 创建订单失败: {e}")
            return {'success': False, 'msg': f'订单创建失败: {str(e)}'}

    def _apply_coupon(self, user_id: int, coupon_id: int, order_amount: float) -> Dict[str, Any]:
        """应用优惠券"""
        coupon_sql = """
            SELECT * FROM business_user_coupons
            WHERE id = %s AND user_id = %s AND status = 'unused'
            AND valid_from <= NOW() AND valid_until >= NOW()
        """
        coupon = db.get_one(coupon_sql, [coupon_id, user_id])

        if not coupon:
            return {'success': False, 'msg': '优惠券不可用'}

        min_amount = float(coupon.get('min_amount', 0))
        discount_amount = float(coupon.get('discount_amount', 0))

        if order_amount < min_amount:
            return {'success': False, 'msg': f'订单金额未达优惠券使用条件(满{min_amount}元)'}

        return {'success': True, 'discount': discount_amount, 'coupon': coupon}

    def _use_coupon(self, user_id: int, coupon_id: int):
        """使用优惠券"""
        sql = """
            UPDATE business_user_coupons
            SET status = 'used', used_at = NOW()
            WHERE id = %s AND user_id = %s
        """
        db.execute(sql, [coupon_id, user_id])

    # ============ V35.0 库存并发优化 ============

    def _lock_stock(self, sku_id: int, quantity: int, is_product: bool = False):
        """锁定库存 - V35.0使用悲观锁"""
        if is_product:
            sql = """
                UPDATE business_products
                SET stock = stock - %s
                WHERE id = %s AND stock >= %s
            """
        else:
            sql = """
                UPDATE business_product_skus
                SET stock = stock - %s
                WHERE id = %s AND stock >= %s
            """
        db.execute(sql, [quantity, sku_id, quantity])

    def _lock_stock_with_pessimistic_lock(self, sku_id: int, quantity: int,
                                         is_product: bool = False) -> bool:
        """
        使用悲观锁扣减库存 - V35.0
        
        通过 SELECT ... FOR UPDATE 获取行锁，确保并发安全
        
        Args:
            sku_id: SKU ID或商品ID
            quantity: 扣减数量
            is_product: 是否是商品级别（否则是SKU级别）
        
        Returns:
            bool: 是否成功
        
        Raises:
            ValueError: 库存不足或商品不存在
        """
        conn = db.get_db()
        cursor = conn.cursor()
        
        try:
            conn.begin()
            
            table = 'business_product_skus' if not is_product else 'business_products'
            id_field = 'id'
            
            # FOR UPDATE获取行锁
            cursor.execute(
                f"SELECT stock FROM {table} WHERE {id_field} = %s FOR UPDATE",
                [sku_id]
            )
            
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"商品不存在: {sku_id}")
            
            current_stock = result['stock']
            if current_stock < quantity:
                raise ValueError(f"库存不足: 当前{current_stock}, 需要{quantity}")
            
            # 扣减库存
            cursor.execute(
                f"UPDATE {table} SET stock = stock - %s WHERE {id_field} = %s",
                [quantity, sku_id]
            )
            
            conn.commit()
            
            logger.info(f"[OrderService] 库存锁定成功: {table}.{id_field}={sku_id}, quantity={quantity}")
            return True
            
        except ValueError:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"[OrderService] 库存锁定失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _lock_stock_with_retry(self, sku_id: int, quantity: int,
                               is_product: bool = False) -> bool:
        """
        带重试的库存扣减 - V35.0
        
        Args:
            sku_id: SKU ID或商品ID
            quantity: 扣减数量
            is_product: 是否是商品级别
        
        Returns:
            bool: 是否成功
        """
        last_error = None
        
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                return self._lock_stock_with_pessimistic_lock(sku_id, quantity, is_product)
            except ValueError as e:
                # 库存不足等业务异常，不重试
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"[OrderService] 库存锁定失败(第{attempt}次): {e}")
                
                if attempt < MAX_RETRY_ATTEMPTS:
                    # 指数退避
                    import time
                    time.sleep(0.1 * (2 ** attempt))
        
        raise last_error or Exception("库存锁定失败")

    def _unlock_stock(self, sku_id: int, quantity: int, is_product: bool = False):
        """
        回滚库存 - V35.0新增
        
        Args:
            sku_id: SKU ID或商品ID
            quantity: 回滚数量
            is_product: 是否是商品级别
        """
        conn = db.get_db()
        cursor = conn.cursor()
        
        try:
            conn.begin()
            
            table = 'business_product_skus' if not is_product else 'business_products'
            
            cursor.execute(
                f"UPDATE {table} SET stock = stock + %s WHERE {table}.id = %s",
                [quantity, sku_id]
            )
            
            conn.commit()
            logger.info(f"[OrderService] 库存回滚成功: {table}.id={sku_id}, quantity={quantity}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[OrderService] 库存回滚失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _generate_order_no(self) -> str:
        """生成订单号"""
        import time
        import random
        prefix = 'ORD'
        timestamp = time.strftime('%Y%m%d%H%M%S')
        random_suffix = str(random.randint(1000, 9999))
        return f"{prefix}{timestamp}{random_suffix}"

    # ============ 订单查询 ============

    def get_order(self, order_id: int = None, order_no: str = None,
                 user_id: int = None, ec_id: int = None) -> Optional[Dict]:
        """查询单个订单"""
        conditions = []
        params = []

        if order_id:
            conditions.append("id = %s")
            params.append(order_id)
        if order_no:
            conditions.append("order_no = %s")
            params.append(order_no)
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        if ec_id:
            conditions.append("ec_id = %s")
            params.append(ec_id)

        if not conditions:
            return None

        where = " AND ".join(conditions)
        sql = f"SELECT * FROM business_orders WHERE {where} LIMIT 1"

        order = db.get_one(sql, params)
        if order:
            order['details'] = self._get_order_details(order['id'])
            order['status_text'] = OrderStatus(order['order_status']).label
        return order

    def get_orders(self, user_id: int = None, ec_id: int = None,
                   status: str = None, page: int = 1, page_size: int = 20,
                   order_by: str = 'created_at DESC') -> Dict[str, Any]:
        """查询订单列表"""
        # V43.0安全修复：验证order_by参数防止SQL注入
        safe_order_by = _validate_order_by(order_by)
        
        conditions = []
        params = []

        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        if ec_id:
            conditions.append("ec_id = %s")
            params.append(ec_id)
        if status:
            conditions.append("order_status = %s")
            params.append(status)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        # 统计总数
        count_sql = f"SELECT COUNT(*) as total FROM business_orders{where}"
        count_result = db.get_one(count_sql, params)
        total = count_result.get('total', 0) if count_result else 0

        # 分页查询
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT * FROM business_orders{where}
            ORDER BY {safe_order_by}
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        orders = db.get_all(query_sql, params) or []

        # 补充状态文本
        for order in orders:
            order['status_text'] = OrderStatus(order['order_status']).label
            order['details'] = self._get_order_details(order['id'])

        return {
            'orders': orders,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size
        }

    def _get_order_details(self, order_id: int) -> List[Dict]:
        """获取订单明细"""
        sql = "SELECT * FROM business_order_details WHERE order_id = %s"
        return db.get_all(sql, [order_id]) or []

    # ============ 订单状态操作 ============

    def cancel_order(self, order_id: int, user_id: int,
                    reason: str = '') -> Dict[str, Any]:
        """取消订单"""
        order = self.get_order(order_id=order_id)

        if not order:
            return {'success': False, 'msg': '订单不存在'}

        if order['user_id'] != user_id:
            return {'success': False, 'msg': '无权操作此订单'}

        if order['order_status'] not in ['pending']:
            return {'success': False, 'msg': f'当前状态不允许取消: {order["order_status"]}'}

        return self._do_cancel_order(order, reason)

    def cancel_expired_orders(self) -> Dict[str, Any]:
        """取消超时未支付订单"""
        now = datetime.now()
        expired_time = now - timedelta(minutes=self.ORDER_EXPIRE_MINUTES)

        sql = """
            SELECT * FROM business_orders
            WHERE order_status = 'pending' AND pay_status = 'unpaid'
            AND created_at < %s
            LIMIT %s
        """

        expired_orders = db.get_all(sql, [expired_time, self.BATCH_SIZE]) or []

        cancelled_count = 0
        for order in expired_orders:
            result = self._do_cancel_order(order, '订单超时自动取消')
            if result['success']:
                cancelled_count += 1

        logger.info(f"[OrderService] 取消超时订单: {cancelled_count}/{len(expired_orders)}")

        return {
            'success': True,
            'total_expired': len(expired_orders),
            'cancelled': cancelled_count
        }

    def _do_cancel_order(self, order: Dict, reason: str) -> Dict[str, Any]:
        """执行取消订单"""
        conn = db.get_db()
        cursor = conn.cursor()

        try:
            conn.begin()

            # 1. 更新订单状态
            cursor.execute("""
                UPDATE business_orders
                SET order_status = 'cancelled', updated_at = NOW(),
                    cancel_reason = %s
                WHERE id = %s
            """, [reason, order['id']])

            # 2. 回滚库存
            details = self._get_order_details(order['id'])
            for detail in details:
                if detail['sku_id']:
                    cursor.execute("""
                        UPDATE business_product_skus
                        SET stock = stock + %s
                        WHERE id = %s
                    """, [detail['quantity'], detail['sku_id']])
                else:
                    cursor.execute("""
                        UPDATE business_products
                        SET stock = stock + %s
                        WHERE id = %s
                    """, [detail['quantity'], detail['product_id']])

            # 3. 恢复优惠券
            if order.get('coupon_id'):
                cursor.execute("""
                    UPDATE business_user_coupons
                    SET status = 'unused', used_at = NULL
                    WHERE id = %s
                """, [order['coupon_id']])

            conn.commit()

            # 4. 发送通知
            self._send_cancel_notification(order, reason)

            logger.info(f"[OrderService] 取消订单成功: {order['order_no']}")

            return {'success': True, 'msg': '订单取消成功'}

        except Exception as e:
            conn.rollback()
            logger.error(f"[OrderService] 取消订单失败: {e}")
            return {'success': False, 'msg': f'取消失败: {str(e)}'}
        finally:
            cursor.close()
            conn.close()

    def _send_cancel_notification(self, order: Dict, reason: str):
        """发送取消通知"""
        try:
            from .notification import send_notification
            send_notification(
                user_id=order['user_id'],
                title='订单已取消',
                content=f'您的订单 {order["order_no"]} 已取消，原因: {reason}',
                type='order_cancel',
                ec_id=order['ec_id'],
                project_id=order['project_id']
            )
        except Exception as e:
            logger.error(f"[OrderService] 发送通知失败: {e}")

    def update_order_status(self, order_id: int, new_status: str,
                          operator_id: int = None, remark: str = '') -> Dict[str, Any]:
        """更新订单状态"""
        order = self.get_order(order_id=order_id)

        if not order:
            return {'success': False, 'msg': '订单不存在'}

        # 验证状态流转
        if not self.validator.can_transition(order['order_status'], new_status):
            return {'success': False, 'msg': f'不允许的状态流转: {order["order_status"]} -> {new_status}'}

        old_status = order['order_status']

        sql = """
            UPDATE business_orders
            SET order_status = %s, updated_at = NOW()
            WHERE id = %s
        """
        db.execute(sql, [new_status, order_id])

        # 记录状态变更
        self._log_status_change(order_id, old_status, new_status, operator_id, remark)

        logger.info(f"[OrderService] 订单状态变更: {order['order_no']} {old_status} -> {new_status}")

        return {'success': True, 'msg': '状态更新成功'}

    def _log_status_change(self, order_id: int, old_status: str, new_status: str,
                          operator_id: int, remark: str):
        """记录状态变更日志"""
        sql = """
            INSERT INTO business_order_status_logs (order_id, old_status, new_status,
                                                   operator_id, remark, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """
        try:
            db.execute(sql, [order_id, old_status, new_status, operator_id, remark])
        except Exception as e:
            logger.error(f"[OrderService] 记录状态变更失败: {e}")

    # ============ 订单统计 ============

    def get_order_stats(self, ec_id: int, project_id: int = None,
                       start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """获取订单统计数据"""
        conditions = ["ec_id = %s"]
        params = [ec_id]

        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)

        if start_date:
            conditions.append("created_at >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("created_at <= %s")
            params.append(end_date)

        where = " AND ".join(conditions)

        # 总订单数
        total_sql = f"SELECT COUNT(*) as cnt, SUM(actual_amount) as amount FROM business_orders WHERE {where}"
        total_result = db.get_one(total_sql, params)

        # 各状态订单数
        status_sql = f"""
            SELECT order_status, COUNT(*) as cnt, SUM(actual_amount) as amount
            FROM business_orders WHERE {where}
            GROUP BY order_status
        """
        status_stats = db.get_all(status_sql, params) or []

        # 转换为字典
        status_dict = {s['order_status']: s for s in status_stats}

        return {
            'total_count': total_result.get('cnt', 0) if total_result else 0,
            'total_amount': float(total_result.get('amount', 0) or 0),
            'pending_count': status_dict.get('pending', {}).get('cnt', 0),
            'paid_count': status_dict.get('paid', {}).get('cnt', 0),
            'completed_count': status_dict.get('completed', {}).get('cnt', 0),
            'cancelled_count': status_dict.get('cancelled', {}).get('cnt', 0),
            'refunded_count': status_dict.get('refunded', {}).get('cnt', 0),
        }

    def get_user_order_summary(self, user_id: int) -> Dict[str, Any]:
        """获取用户订单摘要"""
        sql = """
            SELECT
                COUNT(*) as total_orders,
                SUM(CASE WHEN order_status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                SUM(CASE WHEN order_status IN ('pending', 'paid', 'processing') THEN 1 ELSE 0 END) as active_orders,
                SUM(CASE WHEN order_status = 'completed' THEN actual_amount ELSE 0 END) as total_spent
            FROM business_orders
            WHERE user_id = %s
        """
        result = db.get_one(sql, [user_id])

        return {
            'total_orders': result.get('total_orders', 0) if result else 0,
            'completed_orders': result.get('completed_orders', 0) if result else 0,
            'active_orders': result.get('active_orders', 0) if result else 0,
            'total_spent': float(result.get('total_spent', 0) or 0),
        }


# 单例实例
order_service = OrderService()
