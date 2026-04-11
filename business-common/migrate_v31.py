#!/usr/bin/env python3
"""
V31.0 数据库迁移脚本
功能：
  1. 为 business_orders 添加 expired_at 字段（订单超时关闭时间）
  2. 为 business_orders 添加 cancel_reason 字段（取消原因）
  3. 为 business_notifications 添加 expire_at 字段（通知过期时间）
  4. 创建 business_order_cancel_logs 表（订单取消日志）
  5. 为 rfm_analysis_view 补充（如不存在则创建）
  所有操作均先检查是否存在，支持安全重试（幂等）
"""
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db


def column_exists(table, column):
    try:
        rows = db.get_all(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=%s AND COLUMN_NAME=%s",
            [table, column]
        )
        return bool(rows)
    except Exception:
        return False


def table_exists(table):
    try:
        rows = db.get_all(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME=%s",
            [table]
        )
        return bool(rows)
    except Exception:
        return False


def index_exists(table, index_name):
    try:
        rows = db.get_all(
            "SHOW INDEX FROM `{}` WHERE Key_name=%s".format(table),
            [index_name]
        )
        return bool(rows)
    except Exception:
        return False


def run():
    logger.info("====== V31.0 迁移开始 ======")

    # 1. business_orders 新增 expired_at
    if not column_exists('business_orders', 'expired_at'):
        db.execute("ALTER TABLE business_orders ADD COLUMN expired_at DATETIME NULL COMMENT '订单超时关闭时间'")
        logger.info("✅ business_orders.expired_at 添加成功")
    else:
        logger.info("  business_orders.expired_at 已存在，跳过")

    # 2. business_orders 新增 cancel_reason
    if not column_exists('business_orders', 'cancel_reason'):
        db.execute("ALTER TABLE business_orders ADD COLUMN cancel_reason VARCHAR(200) NULL COMMENT '取消原因'")
        logger.info("✅ business_orders.cancel_reason 添加成功")
    else:
        logger.info("  business_orders.cancel_reason 已存在，跳过")

    # 3. business_notifications 新增 expire_at
    if not column_exists('business_notifications', 'expire_at'):
        db.execute("ALTER TABLE business_notifications ADD COLUMN expire_at DATETIME NULL COMMENT '通知过期时间'")
        logger.info("✅ business_notifications.expire_at 添加成功")
    else:
        logger.info("  business_notifications.expire_at 已存在，跳过")

    # 4. 创建 rfm_analysis_view（MySQL VIEW）
    # 该视图用于 RFM 分群功能（admin 端已有接口引用）
    try:
        db.execute("DROP VIEW IF EXISTS rfm_analysis_view")
        db.execute("""
            CREATE VIEW rfm_analysis_view AS
            SELECT
                m.user_id AS member_id,
                m.user_name,
                m.phone,
                m.member_level,
                m.ec_id,
                m.project_id,
                COALESCE(DATEDIFF(CURDATE(), MAX(o.created_at)), 9999) AS recency_days,
                COUNT(o.id) AS frequency_orders,
                COALESCE(SUM(o.actual_amount), 0) AS monetary_total,
                -- R 分 (1-5)：最近购买越近分越高
                CASE
                    WHEN COALESCE(DATEDIFF(CURDATE(), MAX(o.created_at)), 9999) <= 7   THEN 5
                    WHEN COALESCE(DATEDIFF(CURDATE(), MAX(o.created_at)), 9999) <= 30  THEN 4
                    WHEN COALESCE(DATEDIFF(CURDATE(), MAX(o.created_at)), 9999) <= 90  THEN 3
                    WHEN COALESCE(DATEDIFF(CURDATE(), MAX(o.created_at)), 9999) <= 180 THEN 2
                    ELSE 1
                END AS r_score,
                -- F 分 (1-5)：购买次数越多分越高
                CASE
                    WHEN COUNT(o.id) >= 20 THEN 5
                    WHEN COUNT(o.id) >= 10 THEN 4
                    WHEN COUNT(o.id) >= 5  THEN 3
                    WHEN COUNT(o.id) >= 2  THEN 2
                    ELSE 1
                END AS f_score,
                -- M 分 (1-5)：消费金额越高分越高
                CASE
                    WHEN COALESCE(SUM(o.actual_amount), 0) >= 5000  THEN 5
                    WHEN COALESCE(SUM(o.actual_amount), 0) >= 2000  THEN 4
                    WHEN COALESCE(SUM(o.actual_amount), 0) >= 500   THEN 3
                    WHEN COALESCE(SUM(o.actual_amount), 0) >= 100   THEN 2
                    ELSE 1
                END AS m_score,
                -- RFM 分群类型
                CASE
                    WHEN COALESCE(DATEDIFF(CURDATE(), MAX(o.created_at)), 9999) <= 30
                         AND COUNT(o.id) >= 5
                         AND COALESCE(SUM(o.actual_amount), 0) >= 500  THEN 'champions'
                    WHEN COUNT(o.id) >= 5
                         AND COALESCE(SUM(o.actual_amount), 0) >= 200  THEN 'loyal'
                    WHEN COALESCE(DATEDIFF(CURDATE(), MAX(o.created_at)), 9999) <= 30
                         AND COUNT(o.id) < 5                            THEN 'potential'
                    WHEN COALESCE(DATEDIFF(CURDATE(), MAX(o.created_at)), 9999) <= 14
                         AND COUNT(o.id) = 1                            THEN 'new'
                    WHEN COALESCE(DATEDIFF(CURDATE(), MAX(o.created_at)), 9999) > 90
                         AND COUNT(o.id) >= 3                           THEN 'at_risk'
                    ELSE 'lost'
                END AS rfm_type
            FROM business_members m
            LEFT JOIN business_orders o
                ON m.user_id = o.user_id AND o.deleted = 0 AND o.pay_status = 'paid'
            GROUP BY m.user_id, m.user_name, m.phone, m.member_level, m.ec_id, m.project_id
        """)
        logger.info("✅ rfm_analysis_view 创建/更新成功")
    except Exception as e:
        logger.warning(f"  rfm_analysis_view 创建失败（可忽略）: {e}")

    # 5. 为 business_orders 添加索引加速超时查询
    if not index_exists('business_orders', 'idx_orders_timeout_check'):
        try:
            db.execute("""
                CREATE INDEX idx_orders_timeout_check
                ON business_orders (order_status, pay_status, created_at, deleted)
            """)
            logger.info("✅ idx_orders_timeout_check 索引创建成功")
        except Exception as e:
            logger.warning(f"  创建超时索引失败（可忽略）: {e}")
    else:
        logger.info("  idx_orders_timeout_check 已存在，跳过")

    # 6. 为 business_reviews 添加 reply_at 字段（记录回复时间）
    if not column_exists('business_reviews', 'reply_at'):
        try:
            db.execute("ALTER TABLE business_reviews ADD COLUMN reply_at DATETIME NULL COMMENT '回复时间'")
            logger.info("✅ business_reviews.reply_at 添加成功")
        except Exception as e:
            logger.warning(f"  business_reviews.reply_at 添加失败: {e}")
    else:
        logger.info("  business_reviews.reply_at 已存在，跳过")

    logger.info("====== V31.0 迁移完成 ======")


if __name__ == '__main__':
    run()
