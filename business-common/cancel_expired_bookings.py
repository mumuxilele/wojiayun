#!/usr/bin/env python3
"""
预约超时自动取消定时任务
功能：自动取消超过指定时间未支付的预约
配置：
  - 默认超时时间：30分钟（可配置）
  - 执行频率：建议每5分钟执行一次
使用方式：
  python cancel_expired_bookings.py

建议通过 crontab 或系统定时任务执行：
  */5 * * * * cd /path/to/wojiayun && python cancel_expired_bookings.py >> logs/cancel_expired.log 2>&1
"""
import sys
import os
import logging
import json
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cancel_expired_bookings.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import config, db

# 配置
EXPIRY_MINUTES = 30  # 预约后超过此时间未支付则自动取消（分钟）


def log_to_audit(booking_id, venue_name, book_date, start_time, ec_id=None, project_id=None):
    """记录审计日志到数据库"""
    try:
        db.execute(
            """INSERT INTO business_audit_log 
               (user_id, user_name, action, details, ip, ec_id, project_id) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            ['system', '自动任务', 'cancel_expired_booking',
             json.dumps({
                 'booking_id': booking_id,
                 'venue_name': venue_name,
                 'book_date': str(book_date),
                 'start_time': str(start_time),
                 'reason': f'超过{EXPIRY_MINUTES}分钟未支付'
             }, ensure_ascii=False),
             '127.0.0.1', ec_id, project_id]
        )
    except Exception as e:
        logger.warning(f"写入审计日志失败: {e}")


def cancel_expired_bookings():
    """取消超时未支付的预约"""
    try:
        # 计算截止时间
        expiry_time = datetime.now() - timedelta(minutes=EXPIRY_MINUTES)

        # 查询超时未支付的预约
        # 状态为 pending 且 pay_status 为 unpaid 且创建时间超过指定分钟数
        expired_bookings = db.get_all(
            """SELECT vb.id, vb.venue_id, vb.user_id, vb.book_date, vb.start_time,
                      vb.ec_id, vb.project_id,
                      v.venue_name
               FROM business_venue_bookings vb
               LEFT JOIN business_venues v ON vb.venue_id = v.id
               WHERE vb.status = 'pending'
                 AND vb.pay_status = 'unpaid'
                 AND vb.deleted = 0
                 AND vb.created_at < %s""",
            [expiry_time]
        )

        if not expired_bookings:
            logger.info(f"没有超时未支付的预约（超时时间：{EXPIRY_MINUTES}分钟）")
            return 0

        count = 0
        for booking in expired_bookings:
            booking_id = booking['id']
            venue_name = booking.get('venue_name', '未知场地')
            book_date = booking['book_date']
            start_time = booking['start_time']
            ec_id = booking.get('ec_id')
            project_id = booking.get('project_id')

            try:
                # 更新状态为已取消
                db.execute(
                    """UPDATE business_venue_bookings
                       SET status='cancelled', updated_at=NOW()
                       WHERE id=%s AND status='pending' AND pay_status='unpaid'""",
                    [booking_id]
                )
                count += 1
                logger.info(f"已自动取消超时预约 #{booking_id} | 场地：{venue_name} | "
                           f"日期：{book_date} | 时段：{start_time}")
                
                # 写入审计日志
                log_to_audit(booking_id, venue_name, book_date, start_time, ec_id, project_id)
                
            except Exception as e:
                logger.error(f"取消预约 #{booking_id} 失败: {e}")

        logger.info(f"本次共取消 {count} 个超时预约")
        return count

    except Exception as e:
        logger.error(f"执行取消超时预约任务失败: {e}")
        return 0


def get_pending_stats():
    """获取待处理预约统计（用于监控）"""
    try:
        total = db.get_total(
            "SELECT COUNT(*) FROM business_venue_bookings WHERE status='pending' AND deleted=0"
        )
        unpaid = db.get_total(
            "SELECT COUNT(*) FROM business_venue_bookings WHERE status='pending' AND pay_status='unpaid' AND deleted=0"
        )
        logger.info(f"当前待处理预约统计：总计 {total} | 待支付 {unpaid}")
        return {'total': total, 'unpaid': unpaid}
    except Exception as e:
        logger.error(f"获取预约统计失败: {e}")
        return None


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info(f"开始执行预约超时取消任务 | 超时时间：{EXPIRY_MINUTES}分钟")
    logger.info("=" * 50)

    # 先显示统计信息
    get_pending_stats()

    # 执行取消任务
    cancelled = cancel_expired_bookings()

    logger.info("=" * 50)
    logger.info(f"任务执行完成 | 取消数量：{cancelled}")
    logger.info("=" * 50)
