"""
V36.0 数据库迁移脚本

本迁移为 V36.0 体验闭环增强提供数据库能力：
1. 新增 business_user_settings 表，持久化通知偏好与推送渠道开关
2. 为 business_orders 表补充 expire_time 字段，支撑订单倒计时与超时自动取消体验

用法:
    python migrate_v36.py --check
    python migrate_v36.py --execute
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

MIGRATION_NAME = 'v36_user_settings_and_order_expire'


def create_migrations_table():
    """创建迁移记录表"""
    db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_migration_name (migration_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)


def migration_record_exists() -> bool:
    """检查迁移记录是否存在"""
    try:
        row = db.get_one(
            "SELECT migration_name FROM schema_migrations WHERE migration_name=%s LIMIT 1",
            [MIGRATION_NAME]
        )
        return bool(row)
    except Exception:
        return False


def record_migration():
    """记录迁移执行"""
    try:
        db.execute(
            "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
            [MIGRATION_NAME]
        )
    except Exception as e:
        logger.warning(f"记录迁移失败: {e}")


def table_exists(table_name: str) -> bool:
    try:
        row = db.get_one("SHOW TABLES LIKE %s", [table_name])
        return bool(row)
    except Exception:
        return False


def column_exists(table_name: str, column_name: str) -> bool:
    try:
        row = db.get_one(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s",
            [table_name, column_name]
        )
        return bool(row)
    except Exception:
        return False


def check_migration_needed() -> bool:
    """检查是否需要迁移"""
    need_user_settings = not table_exists('business_user_settings')
    need_expire_time = not column_exists('business_orders', 'expire_time')
    return need_user_settings or need_expire_time


def create_user_settings_table():
    """创建用户设置表"""
    db.execute("""
        CREATE TABLE IF NOT EXISTS business_user_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
            ec_id VARCHAR(50) NOT NULL DEFAULT '' COMMENT '企业ID',
            project_id VARCHAR(50) NOT NULL DEFAULT '' COMMENT '项目ID',
            notif_order TINYINT(1) NOT NULL DEFAULT 1 COMMENT '订单通知开关',
            notif_coupon TINYINT(1) NOT NULL DEFAULT 1 COMMENT '优惠券通知开关',
            notif_system TINYINT(1) NOT NULL DEFAULT 1 COMMENT '系统通知开关',
            channel_in_app TINYINT(1) NOT NULL DEFAULT 1 COMMENT '站内信开关',
            channel_wechat TINYINT(1) NOT NULL DEFAULT 0 COMMENT '微信推送开关',
            channel_sms TINYINT(1) NOT NULL DEFAULT 0 COMMENT '短信推送开关',
            channel_email TINYINT(1) NOT NULL DEFAULT 0 COMMENT '邮件推送开关',
            wechat_openid VARCHAR(128) DEFAULT '' COMMENT '微信OpenID',
            email VARCHAR(128) DEFAULT '' COMMENT '邮箱地址',
            deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_scope (user_id, ec_id, project_id),
            KEY idx_user_id (user_id),
            KEY idx_scope (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户通知偏好设置表'
    """)
    logger.info('✓ business_user_settings 表已就绪')


def add_order_expire_time_column():
    """为订单表补充 expire_time 字段"""
    if column_exists('business_orders', 'expire_time'):
        logger.info('✓ business_orders.expire_time 已存在，跳过')
        return

    db.execute("""
        ALTER TABLE business_orders
        ADD COLUMN expire_time DATETIME NULL COMMENT '订单支付截止时间' AFTER created_at
    """)
    logger.info('✓ 已新增 business_orders.expire_time 字段')

    try:
        db.execute("""
            UPDATE business_orders
            SET expire_time = DATE_ADD(created_at, INTERVAL 30 MINUTE)
            WHERE expire_time IS NULL AND order_status='pending' AND pay_status='unpaid'
        """)
        logger.info('✓ 已为历史待支付订单回填 expire_time')
    except Exception as e:
        logger.warning(f'历史数据回填失败，可后续重试: {e}')


def migrate():
    """执行迁移"""
    logger.info('=' * 60)
    logger.info('开始执行 V36.0 数据库迁移')
    logger.info('=' * 60)

    create_migrations_table()

    if migration_record_exists() and not check_migration_needed():
        logger.info('V36.0 迁移已执行且结构完整，跳过')
        return

    create_user_settings_table()
    add_order_expire_time_column()
    record_migration()

    logger.info('=' * 60)
    logger.info('✓ V36.0 数据库迁移完成')
    logger.info('=' * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='V36.0 数据库迁移')
    parser.add_argument('--check', action='store_true', help='检查是否需要迁移')
    parser.add_argument('--execute', action='store_true', help='执行迁移')
    args = parser.parse_args()

    if args.check:
        if check_migration_needed():
            print('需要进行 V36.0 迁移')
        else:
            print('V36.0 迁移已完成或无需迁移')
        return

    if args.execute or len(sys.argv) == 1:
        migrate()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
