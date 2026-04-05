#!/usr/bin/env python3
"""
V30.0 数据库迁移脚本
- 新增：产品详情页直购 checkout 兼容字段
- 新增：优惠券定向发放记录表
- 新增：staff_reviews 的 is_hidden 字段（内容审核屏蔽支持）
- 补充 business_coupons 的 expire_days / unlimited_stock 字段
- 补充 business_user_coupons 的 expire_at 字段
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db


def check_column_exists(table, column):
    row = db.get_one(
        "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        [table, column]
    )
    return (row.get('cnt') or 0) > 0


def check_table_exists(table):
    row = db.get_one(
        "SELECT COUNT(*) as cnt FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s",
        [table]
    )
    return (row.get('cnt') or 0) > 0


def run_migration():
    print("=== V30.0 数据库迁移开始 ===\n")
    steps = 0

    # 1. business_coupons 补充 expire_days / unlimited_stock
    if not check_column_exists('business_coupons', 'expire_days'):
        db.execute("ALTER TABLE business_coupons ADD COLUMN expire_days INT DEFAULT 30 COMMENT '领取后有效天数'")
        print("[✓] business_coupons 新增 expire_days 字段")
        steps += 1
    else:
        print("[=] business_coupons.expire_days 已存在，跳过")

    if not check_column_exists('business_coupons', 'unlimited_stock'):
        db.execute("ALTER TABLE business_coupons ADD COLUMN unlimited_stock TINYINT(1) DEFAULT 0 COMMENT '是否不限量'")
        print("[✓] business_coupons 新增 unlimited_stock 字段")
        steps += 1
    else:
        print("[=] business_coupons.unlimited_stock 已存在，跳过")

    # 2. business_user_coupons 补充 expire_at 字段
    if not check_column_exists('business_user_coupons', 'expire_at'):
        db.execute("ALTER TABLE business_user_coupons ADD COLUMN expire_at DATETIME NULL COMMENT '到期时间'")
        print("[✓] business_user_coupons 新增 expire_at 字段")
        steps += 1
    else:
        print("[=] business_user_coupons.expire_at 已存在，跳过")

    # 3. business_reviews 补充 is_hidden / hide_reason 字段
    if not check_column_exists('business_reviews', 'is_hidden'):
        db.execute("ALTER TABLE business_reviews ADD COLUMN is_hidden TINYINT(1) DEFAULT 0 COMMENT '是否被屏蔽'")
        print("[✓] business_reviews 新增 is_hidden 字段")
        steps += 1
    else:
        print("[=] business_reviews.is_hidden 已存在，跳过")

    if not check_column_exists('business_reviews', 'hide_reason'):
        db.execute("ALTER TABLE business_reviews ADD COLUMN hide_reason VARCHAR(200) NULL COMMENT '屏蔽原因'")
        print("[✓] business_reviews 新增 hide_reason 字段")
        steps += 1
    else:
        print("[=] business_reviews.hide_reason 已存在，跳过")

    # 4. 优惠券定向发放任务记录表
    if not check_table_exists('business_coupon_issue_tasks'):
        db.execute("""
            CREATE TABLE business_coupon_issue_tasks (
                id           BIGINT AUTO_INCREMENT PRIMARY KEY,
                coupon_id    BIGINT NOT NULL COMMENT '优惠券ID',
                issue_type   VARCHAR(20) NOT NULL DEFAULT 'targeted' COMMENT 'targeted/manual',
                filter_params JSON COMMENT '筛选条件快照',
                target_count INT DEFAULT 0 COMMENT '目标人数',
                success_count INT DEFAULT 0 COMMENT '成功发放人数',
                operator_id  BIGINT COMMENT '操作人ID',
                operator_name VARCHAR(100) COMMENT '操作人名称',
                ec_id        VARCHAR(100),
                project_id   VARCHAR(100),
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_coupon (coupon_id),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券发放任务记录';
        """)
        print("[✓] 创建 business_coupon_issue_tasks 表")
        steps += 1
    else:
        print("[=] business_coupon_issue_tasks 已存在，跳过")

    # 5. business_orders 补充 tracking_no / logistics_company / shipped_at（如果 V22 未迁移）
    for col, definition in [
        ('tracking_no', 'VARCHAR(100) NULL COMMENT "快递单号"'),
        ('logistics_company', 'VARCHAR(50) NULL COMMENT "快递公司"'),
        ('shipped_at', 'DATETIME NULL COMMENT "发货时间"'),
    ]:
        if not check_column_exists('business_orders', col):
            db.execute(f"ALTER TABLE business_orders ADD COLUMN {col} {definition}")
            print(f"[✓] business_orders 新增 {col} 字段")
            steps += 1
        else:
            print(f"[=] business_orders.{col} 已存在，跳过")

    # 6. business_member_achievements 表（如 V27 未建）
    if not check_table_exists('business_member_achievements'):
        db.execute("""
            CREATE TABLE business_member_achievements (
                id               BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id          BIGINT NOT NULL,
                achievement_code VARCHAR(50) NOT NULL,
                achievement_name VARCHAR(100),
                earned_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                ec_id            VARCHAR(100),
                project_id       VARCHAR(100),
                UNIQUE KEY uk_user_achievement (user_id, achievement_code),
                INDEX idx_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户成就徽章';
        """)
        print("[✓] 创建 business_member_achievements 表")
        steps += 1
    else:
        print("[=] business_member_achievements 已存在，跳过")

    # 7. business_recently_viewed 表补充字段
    if not check_table_exists('business_recently_viewed'):
        db.execute("""
            CREATE TABLE business_recently_viewed (
                id            BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id       BIGINT NOT NULL,
                target_type   VARCHAR(20) NOT NULL DEFAULT 'product',
                target_id     BIGINT NOT NULL,
                view_count    INT DEFAULT 1,
                last_view_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                ec_id         VARCHAR(100),
                project_id    VARCHAR(100),
                UNIQUE KEY uk_user_target (user_id, target_type, target_id),
                INDEX idx_user_time (user_id, last_view_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户浏览足迹';
        """)
        print("[✓] 创建 business_recently_viewed 表")
        steps += 1
    else:
        print("[=] business_recently_viewed 已存在，跳过")

    # 8. business_customer_tags / business_customer_tag_users（如 V27 未建）
    if not check_table_exists('business_customer_tags'):
        db.execute("""
            CREATE TABLE business_customer_tags (
                id         BIGINT AUTO_INCREMENT PRIMARY KEY,
                tag_name   VARCHAR(50) NOT NULL,
                tag_color  VARCHAR(20) DEFAULT '#f0f4ff',
                ec_id      VARCHAR(100),
                project_id VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ec (ec_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户标签';
        """)
        print("[✓] 创建 business_customer_tags 表")
        steps += 1
    else:
        print("[=] business_customer_tags 已存在，跳过")

    if not check_table_exists('business_customer_tag_users'):
        db.execute("""
            CREATE TABLE business_customer_tag_users (
                id         BIGINT AUTO_INCREMENT PRIMARY KEY,
                tag_id     BIGINT NOT NULL,
                user_id    BIGINT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_tag_user (tag_id, user_id),
                INDEX idx_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户标签-用户关联';
        """)
        print("[✓] 创建 business_customer_tag_users 表")
        steps += 1
    else:
        print("[=] business_customer_tag_users 已存在，跳过")

    print(f"\n=== V30.0 迁移完成，共执行 {steps} 个变更 ===")
    return steps


if __name__ == '__main__':
    run_migration()
