"""
订单增强服务 V32.0
功能:
  - 订单修改（收货地址、电话）
  - 部分退款（按商品/数量）
  - 订单备注/留言
  - 订单取消（带原因）
  - 订单超时自动处理
"""
import logging
from datetime import datetime, timedelta
from . import db
from .cache_service import cache_delete

logger = logging.getLogger(__name__)


class OrderEnhanceService:
    """订单增强服务"""

    # 订单可修改的字段
    EDITABLE_FIELDS = ['receiver_name', 'receiver_phone', 'receiver_address', 'delivery_note']
    # 订单修改的时限（支付后多少小时内可修改）
    EDITABLE_AFTER_PAY_HOURS = 24
    # 部分退款状态限制
    PARTIAL_REFUND_ORDER_STATUS = ['paid', 'shipped']
    # 部分退款时限（发货后多少天内可申请）
    PARTIAL_REFUND_DAYS_AFTER_SHIP = 7

    @classmethod
    def update_order(cls, order_id, user_id, update_data, ec_id=None, project_id=None):
        """
        修改订单（收货信息等）

        Args:
            order_id: 订单ID
            user_id: 用户ID
            update_data: dict, 要更新的字段
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: {'success': bool, 'msg': str}
        """
        try:
            # 获取订单
            sql = "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0"
            params = [order_id, user_id]
            if ec_id:
                sql += " AND ec_id=%s"
                params.append(ec_id)
            if project_id:
                sql += " AND project_id=%s"
                params.append(project_id)

            order = db.get_one(sql, params)
            if not order:
                return {'success': False, 'msg': '订单不存在'}

            # 检查订单状态：待支付/已支付/已发货状态下可修改
            editable_status = ['pending', 'paid', 'shipped']
            order_status = order.get('order_status', 'pending')
            if order_status not in editable_status:
                return {'success': False, 'msg': f'当前订单状态「{order_status}」不允许修改'}

            # 检查是否已超过修改时限（已支付后N小时内可修改）
            if order_status in ('shipped',):
                pay_time = order.get('paid_at') or order.get('created_at')
                if pay_time:
                    hours_passed = (datetime.now() - pay_time).total_seconds() / 3600
                    if hours_passed > cls.EDITABLE_AFTER_PAY_HOURS:
                        return {'success': False, 'msg': f'订单支付超过{cls.EDITABLE_AFTER_PAY_HOURS}小时，不允许再修改'}

            # 过滤并验证字段
            allowed_updates = {}
            for field in cls.EDITABLE_FIELDS:
                if field in update_data:
                    value = str(update_data[field]).strip() if update_data[field] else None
                    if value is None or value == '':
                        continue

                    # 字段长度校验
                    if field == 'receiver_name' and len(value) > 50:
                        return {'success': False, 'msg': '收货人姓名不能超过50字符'}
                    if field == 'receiver_phone' and len(value) > 20:
                        return {'success': False, 'msg': '联系电话不能超过20字符'}
                    if field == 'receiver_address' and len(value) > 200:
                        return {'success': False, 'msg': '收货地址不能超过200字符'}
                    if field == 'delivery_note' and len(value) > 100:
                        return {'success': False, 'msg': '配送备注不能超过100字符'}

                    allowed_updates[field] = value

            if not allowed_updates:
                return {'success': False, 'msg': '没有可更新的字段'}

            # 构建更新SQL
            set_clause = ', '.join([f"{k}=%s" for k in allowed_updates.keys()])
            set_clause += ', updated_at=NOW()'
            update_params = list(allowed_updates.values()) + [order_id]

            db.execute(f"UPDATE business_orders SET {set_clause} WHERE id=%s", update_params)

            # 记录修改日志
            try:
                from business_common.audit_log import audit_log
                audit_log.log_action(
                    user_id=user_id,
                    action='update_order',
                    details=f'修改订单{order_id}字段: {list(allowed_updates.keys())}',
                    ec_id=ec_id,
                    project_id=project_id
                )
            except:
                pass

            return {'success': True, 'msg': '订单信息已更新', 'updated_fields': list(allowed_updates.keys())}

        except Exception as e:
            logger.error(f"修改订单失败: order_id={order_id}, error={e}")
            return {'success': False, 'msg': '修改失败，请稍后重试'}

    @classmethod
    def partial_refund(cls, order_id, user_id, refund_items, reason='', ec_id=None, project_id=None):
        """
        部分退款（按商品/数量）

        Args:
            order_id: 订单ID
            user_id: 用户ID
            refund_items: list, [{'product_id': xxx, 'sku_id': xxx, 'quantity': 2}, ...]
            reason: 退款原因
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: {'success': bool, 'msg': str, 'refund_amount': float}
        """
        if not refund_items:
            return {'success': False, 'msg': '请选择要退款的商品', 'refund_amount': 0}

        try:
            # 获取订单
            sql = "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0"
            params = [order_id, user_id]
            if ec_id:
                sql += " AND ec_id=%s"
                params.append(ec_id)
            if project_id:
                sql += " AND project_id=%s"
                params.append(project_id)

            order = db.get_one(sql, params)
            if not order:
                return {'success': False, 'msg': '订单不存在', 'refund_amount': 0}

            # 检查订单状态
            order_status = order.get('order_status')
            if order_status not in cls.PARTIAL_REFUND_ORDER_STATUS:
                return {'success': False, 'msg': f'当前状态「{order_status}」不支持部分退款', 'refund_amount': 0}

            # 检查退款时限（发货后N天内）
            if order_status == 'shipped':
                ship_time = order.get('shipped_at') or order.get('updated_at')
                if ship_time:
                    days_passed = (datetime.now() - ship_time).days
                    if days_passed > cls.PARTIAL_REFUND_DAYS_AFTER_SHIP:
                        return {'success': False, 'msg': f'发货超过{cls.PARTIAL_REFUND_DAYS_AFTER_SHIP}天，不支持部分退款', 'refund_amount': 0}

            # 检查是否已有退款申请
            if order.get('refund_status') in ('pending', 'approved'):
                return {'success': False, 'msg': '已有退款申请在处理中', 'refund_amount': 0}

            # 获取订单商品
            order_items = db.get_all(
                "SELECT * FROM business_order_items WHERE order_id=%s",
                [order_id]
            )

            # 计算可退款金额
            refund_amount = 0.0
            valid_items = []
            invalid_items = []

            for refund_item in refund_items:
                product_id = refund_item.get('product_id')
                sku_id = refund_item.get('sku_id')
                quantity = int(refund_item.get('quantity', 0))

                if quantity <= 0:
                    invalid_items.append(f'商品{product_id}数量必须大于0')
                    continue

                # 查找订单中的对应商品
                matched = None
                for item in order_items:
                    if str(item['product_id']) == str(product_id):
                        if (sku_id and str(item.get('sku_id') or '') == str(sku_id)) or (not sku_id):
                            matched = item
                            break

                if not matched:
                    invalid_items.append(f'商品{product_id}不在订单中')
                    continue

                # 检查退款数量
                already_refunded = db.get_total(
                    "SELECT COALESCE(SUM(quantity), 0) FROM business_partial_refunds WHERE order_id=%s AND product_id=%s AND status='approved'",
                    [order_id, product_id]
                )
                max_refund_qty = matched['quantity'] - already_refunded
                if quantity > max_refund_qty:
                    invalid_items.append(f'商品{product_id}最多可退{max_refund_qty}件')
                    continue

                # 计算退款金额（按比例）
                item_refund = float(matched['price']) * quantity
                refund_amount += item_refund
                valid_items.append({
                    'product_id': product_id,
                    'sku_id': sku_id,
                    'quantity': quantity,
                    'refund_amount': item_refund
                })

            if invalid_items:
                return {'success': False, 'msg': '; '.join(invalid_items), 'refund_amount': 0}

            if not valid_items:
                return {'success': False, 'msg': '没有有效的退款商品', 'refund_amount': 0}

            # 创建部分退款记录
            refund_no = f'PR{datetime.now().strftime("%Y%m%d%H%M%S")}'
            refund_json = json.dumps(valid_items)

            db.execute("""
                INSERT INTO business_partial_refunds
                (refund_no, order_id, user_id, items, refund_amount, reason, status, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s)
            """, [refund_no, order_id, user_id, refund_json, refund_amount, reason, ec_id, project_id])

            # 更新订单退款状态
            db.execute(
                "UPDATE business_orders SET refund_status='pending', refund_reason=%s, refund_requested_at=NOW(), updated_at=NOW() WHERE id=%s",
                [f'部分退款申请({reason})', order_id]
            )

            # 发送通知
            try:
                from business_common.notification import send_notification
                send_notification(
                    user_id='staff',
                    title='新的部分退款申请',
                    content=f'用户申请部分退款，订单号：{order.get("order_no")}，金额：¥{refund_amount:.2f}',
                    notify_type='refund',
                    ec_id=ec_id,
                    project_id=project_id
                )
            except:
                pass

            return {
                'success': True,
                'msg': f'部分退款申请已提交，预计退款¥{refund_amount:.2f}',
                'refund_amount': round(refund_amount, 2),
                'refund_no': refund_no
            }

        except Exception as e:
            logger.error(f"部分退款申请失败: order_id={order_id}, error={e}")
            return {'success': False, 'msg': '申请失败，请稍后重试', 'refund_amount': 0}

    @classmethod
    def add_order_note(cls, order_id, user_id, note_type, content, ec_id=None, project_id=None):
        """
        添加订单备注/留言

        Args:
            order_id: 订单ID
            user_id: 用户ID
            note_type: 留言类型 (user_question/staff_reply/system_notice)
            content: 留言内容

        Returns:
            dict: {'success': bool, 'msg': str}
        """
        if not content or len(content.strip()) == 0:
            return {'success': False, 'msg': '留言内容不能为空'}
        if len(content) > 500:
            return {'success': False, 'msg': '留言内容不能超过500字'}

        try:
            # 验证订单归属
            order = db.get_one(
                "SELECT id, order_no FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
                [order_id, user_id]
            )
            if not order:
                return {'success': False, 'msg': '订单不存在'}

            # 记录留言
            note_no = f'NOTE{datetime.now().strftime("%Y%m%d%H%M%S")}'
            db.execute("""
                INSERT INTO business_order_notes
                (note_no, order_id, user_id, note_type, content, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [note_no, order_id, user_id, note_type, content.strip(), ec_id, project_id])

            return {'success': True, 'msg': '留言已提交', 'note_no': note_no}

        except Exception as e:
            logger.error(f"添加订单留言失败: order_id={order_id}, error={e}")
            return {'success': False, 'msg': '提交失败'}

    @classmethod
    def get_order_notes(cls, order_id, user_id, ec_id=None, project_id=None):
        """获取订单留言列表"""
        try:
            # 验证订单归属
            order = db.get_one(
                "SELECT id FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
                [order_id, user_id]
            )
            if not order:
                return {'success': False, 'msg': '订单不存在', 'notes': []}

            notes = db.get_all("""
                SELECT id, note_type, content, created_at
                FROM business_order_notes
                WHERE order_id=%s AND deleted=0
                ORDER BY created_at DESC
            """, [order_id])

            return {'success': True, 'notes': notes or []}

        except Exception as e:
            logger.error(f"获取订单留言失败: order_id={order_id}, error={e}")
            return {'success': True, 'notes': []}

    @classmethod
    def cancel_with_reason(cls, order_id, user_id, reason, ec_id=None, project_id=None):
        """
        取消订单（带原因）

        Args:
            order_id: 订单ID
            user_id: 用户ID
            reason: 取消原因
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: {'success': bool, 'msg': str}
        """
        if not reason or len(reason.strip()) == 0:
            return {'success': False, 'msg': '请填写取消原因'}
        if len(reason) > 200:
            return {'success': False, 'msg': '取消原因不能超过200字'}

        try:
            # 获取订单
            order = db.get_one(
                "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
                [order_id, user_id]
            )
            if not order:
                return {'success': False, 'msg': '订单不存在'}

            # 检查订单状态：只有待支付/已支付状态可取消
            order_status = order.get('order_status')
            if order_status not in ('pending', 'paid'):
                return {'success': False, 'msg': f'当前状态「{order_status}」不允许取消'}

            # 如果已支付，需要检查是否可以退款
            refund_amount = 0.0
            if order_status == 'paid' and order.get('pay_status') == 'paid':
                refund_amount = float(order.get('actual_amount', 0))

            # 执行取消
            db.execute("""
                UPDATE business_orders
                SET order_status='cancelled',
                    cancel_reason=%s,
                    cancelled_at=NOW(),
                    updated_at=NOW()
                WHERE id=%s
            """, [reason.strip(), order_id])

            # 回滚库存
            try:
                items = db.get_all(
                    "SELECT product_id, quantity FROM business_order_items WHERE order_id=%s",
                    [order_id]
                )
                for item in (items or []):
                    db.execute(
                        "UPDATE business_products SET stock=stock+%s, sales_count=GREATEST(0, sales_count-%s) WHERE id=%s",
                        [item['quantity'], item['quantity'], item['product_id']]
                    )
            except Exception as e:
                logger.warning(f"取消订单回滚库存失败: {e}")

            # 如果已支付，触发退款
            if refund_amount > 0:
                try:
                    from business_common.payment_service import PaymentService
                    PaymentService.create_refund(
                        order_id=order_id,
                        amount=refund_amount,
                        reason=f'用户取消订单: {reason}',
                        refund_type='cancel',
                        ec_id=ec_id,
                        project_id=project_id
                    )
                except Exception as e:
                    logger.warning(f"取消订单触发退款失败: {e}")

            # 清理缓存
            cache_delete(f'order_{order_id}')
            cache_delete(f'user_orders_{user_id}')

            return {
                'success': True,
                'msg': '订单已取消',
                'will_refund': refund_amount > 0,
                'refund_amount': refund_amount
            }

        except Exception as e:
            logger.error(f"取消订单失败: order_id={order_id}, error={e}")
            return {'success': False, 'msg': '取消失败，请稍后重试'}

    @classmethod
    def get_order_detail_enhanced(cls, order_id, user_id, ec_id=None, project_id=None):
        """
        获取订单详情增强版（包含物流、发票等信息）

        Returns:
            dict: 订单详情
        """
        try:
            # 基本订单信息
            sql = """
                SELECT o.*,
                       s.shop_name, s.address as shop_address, s.phone as shop_phone
                FROM business_orders o
                LEFT JOIN business_shops s ON o.shop_id=s.id
                WHERE o.id=%s AND o.user_id=%s AND o.deleted=0
            """
            params = [order_id, user_id]
            if ec_id:
                sql += " AND o.ec_id=%s"
                params.append(ec_id)
            if project_id:
                sql += " AND o.project_id=%s"
                params.append(project_id)

            order = db.get_one(sql, params)
            if not order:
                return None

            # 订单商品列表
            items = db.get_all("""
                SELECT oi.*,
                       p.product_name, p.images as product_images
                FROM business_order_items oi
                LEFT JOIN business_products p ON oi.product_id=p.id
                WHERE oi.order_id=%s
            """, [order_id])

            order['items'] = items or []

            # 物流信息
            if order.get('tracking_number'):
                try:
                    from business_common.logistics_service import LogisticsService
                    logistics = LogisticsService()
                    logistics_info = logistics.get_logistics(order.get('tracking_number'))
                    order['logistics_info'] = logistics_info
                except:
                    order['logistics_info'] = None

            # 部分退款记录
            partial_refunds = db.get_all("""
                SELECT id, refund_no, items, refund_amount, reason, status, created_at
                FROM business_partial_refunds
                WHERE order_id=%s AND deleted=0
                ORDER BY created_at DESC
            """, [order_id])
            order['partial_refunds'] = partial_refunds or []

            # 订单留言
            notes = db.get_all("""
                SELECT id, note_type, content, created_at
                FROM business_order_notes
                WHERE order_id=%s AND deleted=0
                ORDER BY created_at DESC
            """, [order_id])
            order['notes'] = notes or []

            return order

        except Exception as e:
            logger.error(f"获取增强订单详情失败: order_id={order_id}, error={e}")
            return None


# 便捷实例
order_enhance = OrderEnhanceService()
