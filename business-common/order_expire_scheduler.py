#!/usr/bin/env python3
"""
订单超时自动取消定时任务调度器 V34.0
集成到任务队列服务，每5分钟执行一次

功能：
  1. 通过任务队列调度订单超时自动取消
  2. 支持多租户隔离
  3. 记录执行日志和审计

使用方式：
  python order_expire_scheduler.py
  
建议部署：
  - 独立进程常驻运行
  - 或通过 supervisor/systemd 管理
  - 每5分钟调度一次
"""
import sys
import os
import time
import logging
import threading
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/order_expire_scheduler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db, config
from business_common.task_queue_service import TaskQueueService, TaskPriority

# ============ 配置 ============
INTERVAL_SECONDS = 300  # 5分钟
ORDER_EXPIRE_MINUTES = 30  # 订单超时分钟数
PRE_EXPIRE_REMIND_MINUTES = 5  # 超时前提醒窗口（分钟）
BATCH_SIZE = 100  # 每批处理量



class OrderExpireScheduler:
    """订单超时自动取消调度器"""

    def __init__(self):
        self.task_service = TaskQueueService()
        self.running = False
        self.thread = None

    def _get_ec_projects(self):
        """获取所有租户项目"""
        try:
            rows = db.get_all("""
                SELECT DISTINCT ec_id, project_id
                FROM business_orders
                WHERE deleted=0 AND order_status='pending' AND pay_status='unpaid'
            """) or []
            return rows
        except Exception as e:
            logger.error(f"获取租户列表失败: {e}")
            return []

    def _create_expire_task(self, ec_id: int, project_id: int) -> dict:
        """
        创建订单超时取消任务

        Args:
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 创建结果
        """
        expire_time = datetime.now() - timedelta(minutes=ORDER_EXPIRE_MINUTES)

        task_data = {
            'task_action': 'cancel_expired_orders',
            'expire_before': expire_time.strftime('%Y-%m-%d %H:%M:%S'),
            'expire_minutes': ORDER_EXPIRE_MINUTES,
            'ec_id': ec_id,
            'project_id': project_id,
            'batch_size': BATCH_SIZE
        }

        # 注册任务处理器
        self.task_service.register_handler('cancel_expired_orders', self._handle_expire_task)

        return self.task_service.create_task(
            task_type='cancel_expired_orders',
            task_data=task_data,
            priority=TaskPriority.NORMAL,
            ec_id=ec_id,
            project_id=project_id,
            created_by='system_scheduler'
        )

    def _create_reminder_task(self, ec_id: int, project_id: int) -> dict:
        """创建订单超时前提醒任务"""
        remind_after = datetime.now()
        remind_before = remind_after + timedelta(minutes=PRE_EXPIRE_REMIND_MINUTES)

        task_data = {
            'task_action': 'remind_expiring_orders',
            'remind_after': remind_after.strftime('%Y-%m-%d %H:%M:%S'),
            'remind_before': remind_before.strftime('%Y-%m-%d %H:%M:%S'),
            'remind_minutes': PRE_EXPIRE_REMIND_MINUTES,
            'ec_id': ec_id,
            'project_id': project_id,
            'batch_size': BATCH_SIZE
        }

        self.task_service.register_handler('remind_expiring_orders', self._handle_reminder_task)

        return self.task_service.create_task(
            task_type='remind_expiring_orders',
            task_data=task_data,
            priority=TaskPriority.HIGH,
            ec_id=ec_id,
            project_id=project_id,
            created_by='system_scheduler'
        )

    def _handle_reminder_task(self, task_data: dict) -> dict:
        """处理订单超时前提醒任务"""
        remind_after = task_data.get('remind_after')
        remind_before = task_data.get('remind_before')
        batch_size = task_data.get('batch_size', BATCH_SIZE)

        logger.info(f"开始执行订单超时前提醒，窗口: {remind_after} ~ {remind_before}")

        try:
            remind_orders = db.get_all("""
                SELECT id, order_no, user_id, ec_id, project_id,
                       COALESCE(expire_time, DATE_ADD(created_at, INTERVAL %s MINUTE)) AS expire_time
                FROM business_orders
                WHERE order_status='pending' AND pay_status='unpaid' AND deleted=0
                  AND COALESCE(expire_time, DATE_ADD(created_at, INTERVAL %s MINUTE)) > %s
                  AND COALESCE(expire_time, DATE_ADD(created_at, INTERVAL %s MINUTE)) <= %s
                ORDER BY expire_time ASC
                LIMIT %s
            """, [ORDER_EXPIRE_MINUTES, ORDER_EXPIRE_MINUTES, remind_after,
                    ORDER_EXPIRE_MINUTES, remind_before, batch_size]) or []

            if not remind_orders:
                logger.info("暂无需要提醒的待支付订单")
                return {'success': True, 'reminded': 0, 'total': 0}

            task_ec_id = task_data.get('ec_id')
            task_project_id = task_data.get('project_id')
            reminded_count = 0

            for order in remind_orders:
                if task_ec_id and order.get('ec_id') != task_ec_id:
                    continue
                if task_project_id and order.get('project_id') != task_project_id:
                    continue

                order_id = order['id']
                existing = db.get_one("""
                    SELECT id FROM business_notifications
                    WHERE user_id=%s AND ref_id=%s AND ref_type='order_expire_reminder'
                    LIMIT 1
                """, [order.get('user_id'), str(order_id)])
                if existing:
                    continue

                try:
                    self._send_pre_expire_reminder(
                        order_id=order_id,
                        user_id=order.get('user_id'),
                        order_no=order.get('order_no', ''),
                        expire_time=order.get('expire_time'),
                        ec_id=order.get('ec_id'),
                        project_id=order.get('project_id')
                    )
                    reminded_count += 1
                except Exception as e:
                    logger.error(f"发送订单提醒失败: order_id={order_id}, error={e}")
                    continue

            logger.info(f"本次提醒完成，共提醒 {reminded_count}/{len(remind_orders)} 个订单")
            return {
                'success': True,
                'reminded': reminded_count,
                'total': len(remind_orders)
            }

        except Exception as e:
            logger.error(f"执行订单提醒失败: {e}")
            return {'success': False, 'msg': str(e)}

    def _handle_expire_task(self, task_data: dict) -> dict:
        """处理订单超时取消任务"""
        expire_before = task_data.get('expire_before')
        batch_size = task_data.get('batch_size', BATCH_SIZE)

        logger.info(f"开始执行订单超时取消，截止时间: {expire_before}")

        try:
            expired_orders = db.get_all("""
                SELECT id, order_no, user_id, ec_id, project_id, actual_amount
                FROM business_orders
                WHERE order_status='pending' AND pay_status='unpaid' AND deleted=0
                AND COALESCE(expire_time, DATE_ADD(created_at, INTERVAL %s MINUTE)) < %s
                LIMIT %s
            """, [ORDER_EXPIRE_MINUTES, expire_before, batch_size]) or []

            if not expired_orders:
                logger.info("暂无需要取消的超时订单")
                return {'success': True, 'cancelled': 0, 'total': 0}

            task_ec_id = task_data.get('ec_id')
            task_project_id = task_data.get('project_id')

            cancelled_count = 0
            for order in expired_orders:
                if task_ec_id and order.get('ec_id') != task_ec_id:
                    continue
                if task_project_id and order.get('project_id') != task_project_id:
                    continue

                order_id = order['id']
                order_no = order.get('order_no', '')
                user_id = order.get('user_id')
                ec_id = order.get('ec_id')
                project_id = order.get('project_id')

                conn = None
                try:
                    conn = db.get_db()
                    with conn.cursor() as cursor:
                        affected = cursor.execute("""
                            UPDATE business_orders
                            SET order_status='cancelled', updated_at=NOW(),
                                cancel_reason='订单超时自动取消'
                            WHERE id=%s AND order_status='pending' AND pay_status='unpaid'
                        """, [order_id])
                    conn.commit()

                    if affected > 0:
                        self._rollback_stock(order_id)
                        self._send_notification(user_id, order_no, ec_id, project_id)
                        self._log_audit(order_id, order_no, user_id, ec_id, project_id)
                        cancelled_count += 1
                        logger.info(f"订单已取消: order_no={order_no}")
                except Exception as e:
                    if conn:
                        conn.rollback()
                    logger.error(f"取消订单失败: order_id={order_id}, error={e}")
                    continue
                finally:
                    if conn:
                        conn.close()

            logger.info(f"本次执行完成，共取消 {cancelled_count}/{len(expired_orders)} 个超时订单")
            return {
                'success': True,
                'cancelled': cancelled_count,
                'total': len(expired_orders)
            }

        except Exception as e:
            logger.error(f"执行订单超时取消失败: {e}")
            return {'success': False, 'msg': str(e)}


    def _rollback_stock(self, order_id: int):
        """回滚订单占用的库存"""
        try:
            items = db.get_all("""
                SELECT product_id, sku_id, quantity
                FROM business_order_items
                WHERE order_id=%s
            """, [order_id]) or []

            for item in items:
                product_id = item.get('product_id')
                sku_id = item.get('sku_id')
                qty = item.get('quantity', 0)

                if not product_id or qty <= 0:
                    continue

                # 回滚主商品库存
                db.execute("""
                    UPDATE business_products
                    SET stock = stock + %s,
                        sales_count = GREATEST(0, sales_count - %s)
                    WHERE id = %s
                """, [qty, qty, product_id])

                # 回滚SKU库存
                if sku_id:
                    db.execute("""
                        UPDATE business_product_skus
                        SET stock = stock + %s
                        WHERE id = %s
                    """, [qty, sku_id])

        except Exception as e:
            logger.warning(f"库存回滚失败: order_id={order_id}, error={e}")

    def _send_pre_expire_reminder(self, order_id: int, user_id: int, order_no: str,
                                 expire_time=None, ec_id: int = None, project_id: int = None):
        """发送订单超时前提醒"""
        try:
            expire_text = ''
            if expire_time:
                if hasattr(expire_time, 'strftime'):
                    expire_text = expire_time.strftime('%H:%M')
                else:
                    expire_text = str(expire_time)[11:16]
            suffix = f'，预计 {expire_text} 自动取消' if expire_text else '，请尽快完成支付'
            from business_common.notification import send_notification
            send_notification(
                user_id=user_id,
                title='订单即将超时',
                content=f'您的订单 {order_no} 将在 {PRE_EXPIRE_REMIND_MINUTES} 分钟内自动取消{suffix}。',
                notify_type='order',
                ref_id=str(order_id),
                ref_type='order_expire_reminder',
                ec_id=ec_id,
                project_id=project_id
            )
        except Exception as e:
            logger.warning(f"发送订单超时前提醒失败: order_id={order_id}, e={e}")

    def _send_notification(self, user_id: int, order_no: str,
                          ec_id: int = None, project_id: int = None):
        """发送订单取消通知"""

        try:
            db.execute("""
                INSERT INTO business_notifications
                (user_id, title, content, notify_type, ref_id, ref_type, ec_id, project_id)
                VALUES (%s, %s, %s, 'order', %s, 'order', %s, %s)
            """, [
                user_id,
                '订单已自动取消',
                f'您的订单 {order_no} 因超过 {ORDER_EXPIRE_MINUTES} 分钟未支付，已被系统自动取消。',
                order_no,
                ec_id,
                project_id
            ])
        except Exception as e:
            logger.warning(f"发送通知失败: user_id={user_id}, e={e}")

    def _log_audit(self, order_id: int, order_no: str, user_id: int,
                   ec_id: int = None, project_id: int = None):
        """记录审计日志"""
        try:
            import json
            db.execute("""
                INSERT INTO business_audit_log
                (user_id, user_name, action, details, ip, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [
                'system',
                '自动任务',
                'cancel_expired_order',
                json.dumps({
                    'order_id': order_id,
                    'order_no': order_no,
                    'expire_minutes': ORDER_EXPIRE_MINUTES
                }),
                '127.0.0.1',
                ec_id,
                project_id
            ])
        except Exception as e:
            logger.warning(f"审计日志记录失败: order_id={order_id}, e={e}")

    def _schedule_once(self):
        """执行一次调度"""
        try:
            logger.info(f"=== 订单提醒/取消调度开始 ===")

            self.task_service.register_handler(
                'remind_expiring_orders',
                self._handle_reminder_task
            )
            self.task_service.register_handler(
                'cancel_expired_orders',
                self._handle_expire_task
            )

            ec_projects = self._get_ec_projects()
            if not ec_projects:
                remind_now = datetime.now()
                remind_result = self._handle_reminder_task({
                    'task_action': 'remind_expiring_orders',
                    'remind_after': remind_now.strftime('%Y-%m-%d %H:%M:%S'),
                    'remind_before': (remind_now + timedelta(minutes=PRE_EXPIRE_REMIND_MINUTES)).strftime('%Y-%m-%d %H:%M:%S'),
                    'remind_minutes': PRE_EXPIRE_REMIND_MINUTES,
                    'batch_size': BATCH_SIZE
                })
                expire_result = self._handle_expire_task({
                    'task_action': 'cancel_expired_orders',
                    'expire_before': (datetime.now() - timedelta(minutes=ORDER_EXPIRE_MINUTES)).strftime('%Y-%m-%d %H:%M:%S'),
                    'expire_minutes': ORDER_EXPIRE_MINUTES,
                    'batch_size': BATCH_SIZE
                })
                logger.info(f"全局提醒执行结果: {remind_result}")
                logger.info(f"全局取消执行结果: {expire_result}")
            else:
                for ep in ec_projects:
                    remind_result = self._create_reminder_task(ep.get('ec_id'), ep.get('project_id'))
                    expire_result = self._create_expire_task(ep.get('ec_id'), ep.get('project_id'))
                    logger.info(f"租户提醒任务创建: ec_id={ep.get('ec_id')}, result={remind_result}")
                    logger.info(f"租户取消任务创建: ec_id={ep.get('ec_id')}, result={expire_result}")

            logger.info(f"=== 订单提醒/取消调度完成 ===")

        except Exception as e:
            logger.error(f"调度执行失败: {e}")


    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行中")
            return

        self.running = True
        logger.info(f"订单超时取消调度器已启动，间隔: {INTERVAL_SECONDS}秒")

        def run_loop():
            while self.running:
                self._schedule_once()
                # 分段等待，便于优雅停止
                for _ in range(INTERVAL_SECONDS):
                    if not self.running:
                        break
                    time.sleep(1)

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("订单超时取消调度器已停止")


# ============ 主入口 ============
if __name__ == '__main__':
    scheduler = OrderExpireScheduler()

    try:
        # 执行一次
        scheduler._schedule_once()
        logger.info("调度执行完成")

        # 如果需要常驻运行，取消注释下面这行
        # scheduler.start()

        # 阻止主线程退出（常驻模式）
        # while scheduler.running:
        #     time.sleep(1)

    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止...")
        scheduler.stop()
    except Exception as e:
        logger.error(f"调度器异常退出: {e}")
        scheduler.stop()
