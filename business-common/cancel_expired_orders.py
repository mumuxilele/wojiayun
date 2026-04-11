#!/usr/bin/env python3
"""
订单超时自动关闭定时任务 V31.0
功能：
  1. 自动关闭超过指定时间未支付的商品订单（默认30分钟）
  2. 关闭时回滚库存（防止库存被长期占用）
  3. 发送站内通知告知用户
  4. 记录审计日志

使用方式：
  python cancel_expired_orders.py

建议通过 crontab 每5分钟执行一次：
  */5 * * * * cd /path/to/wojiayun && python business-common/cancel_expired_orders.py >> logs/cancel_expired_orders.log 2>&1
"""
import sys
import os
import logging
import json
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cancel_expired_orders.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import config, db

# 配置
ORDER_EXPIRE_MINUTES = int(os.environ.get('ORDER_EXPIRE_MINUTES', 30))  # 超时分钟数
BATCH_SIZE = 100  # 每批处理量


def rollback_order_stock(order_id):
    """回滚订单占用的库存"""
    try:
        items = db.get_all(
            "SELECT product_id, sku_id, quantity FROM business_order_items WHERE order_id=%s",
            [order_id]
        )
        for item in (items or []):
            product_id = item.get('product_id')
            sku_id = item.get('sku_id')
            qty = item.get('quantity', 0)
            if not product_id or qty <= 0:
                continue
            # 回滚主商品库存
            db.execute(
                "UPDATE business_products SET stock=stock+%s, sales_count=GREATEST(0,sales_count-%s) WHERE id=%s",
                [qty, qty, product_id]
            )
            # 回滚SKU库存（如有）
            if sku_id:
                try:
                    db.execute(
                        "UPDATE business_product_skus SET stock=stock+%s WHERE id=%s",
                        [qty, sku_id]
                    )
                except Exception as e:
                    logger.warning(f"SKU库存回滚失败: sku_id={sku_id}, e={e}")
        return True
    except Exception as e:
        logger.error(f"库存回滚失败: order_id={order_id}, error={e}")
        return False


def send_cancel_notification(user_id, order_no, ec_id=None, project_id=None):
    """发送订单超时取消通知"""
    try:
        db.execute(
            """INSERT INTO business_notifications
               (user_id, title, content, notify_type, ref_id, ref_type, ec_id, project_id)
               VALUES (%s, %s, %s, 'order', %s, 'order', %s, %s)""",
            [
                user_id,
                '订单已自动取消',
                f'您的订单 {order_no} 因超过 {ORDER_EXPIRE_MINUTES} 分钟未支付，已被系统自动取消。如需购买请重新下单。',
                order_no,
                ec_id,
                project_id
            ]
        )
    except Exception as e:
        logger.warning(f"发送取消通知失败: user_id={user_id}, e={e}")


def log_audit(order_id, order_no, user_id, ec_id=None, project_id=None):
    """记录审计日志"""
    try:
        db.execute(
            """INSERT INTO business_audit_log
               (user_id, user_name, action, details, ip, ec_id, project_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            [
                'system',
                '自动任务',
                'cancel_expired_order',
                json.dumps({'order_id': order_id, 'order_no': order_no, 'original_user_id': user_id, 'expire_minutes': ORDER_EXPIRE_MINUTES}),
                '127.0.0.1',
                ec_id,
                project_id
            ]
        )
    except Exception as e:
        logger.warning(f"审计日志记录失败: order_id={order_id}, e={e}")


def cancel_expired_orders():
    """执行订单超时自动关闭"""
    expire_time = datetime.now() - timedelta(minutes=ORDER_EXPIRE_MINUTES)
    expire_str = expire_time.strftime('%Y-%m-%d %H:%M:%S')

    logger.info(f"开始执行订单超时关闭，超时阈值: {expire_str}（{ORDER_EXPIRE_MINUTES}分钟）")

    try:
        # 查询需要关闭的订单（待支付 + 超时）
        expired_orders = db.get_all(
            """SELECT id, order_no, user_id, ec_id, project_id, actual_amount
               FROM business_orders
               WHERE order_status='pending' AND pay_status='unpaid' AND deleted=0
               AND created_at < %s
               LIMIT %s""",
            [expire_str, BATCH_SIZE]
        ) or []

        if not expired_orders:
            logger.info("无需关闭的超时订单")
            return 0

        cancelled_count = 0
        for order in expired_orders:
            order_id = order['id']
            order_no = order.get('order_no', '')
            user_id = order.get('user_id')
            ec_id = order.get('ec_id')
            project_id = order.get('project_id')

            try:
                # 关闭订单
                affected = db.execute(
                    """UPDATE business_orders
                       SET order_status='cancelled', updated_at=NOW()
                       WHERE id=%s AND order_status='pending' AND pay_status='unpaid'""",
                    [order_id]
                )

                if affected and affected > 0:
                    # 回滚库存
                    rollback_order_stock(order_id)
                    # 通知用户
                    if user_id:
                        send_cancel_notification(user_id, order_no, ec_id, project_id)
                    # 审计日志
                    log_audit(order_id, order_no, user_id, ec_id, project_id)
                    cancelled_count += 1
                    logger.info(f"订单已取消: order_id={order_id}, order_no={order_no}")

            except Exception as e:
                logger.error(f"取消订单失败: order_id={order_id}, error={e}")
                continue

        logger.info(f"本次执行完成，共取消 {cancelled_count} 个超时订单")
        return cancelled_count

    except Exception as e:
        logger.error(f"查询超时订单失败: {e}")
        return 0


if __name__ == '__main__':
    cancel_expired_orders()
