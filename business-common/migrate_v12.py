#!/usr/bin/env python3
"""
V12.0 数据库迁移脚本
幂等设计：支持安全重试

新增内容:
1. 会员表增加会员标签和来源渠道字段
2. 订单表增加退款处理人字段
3. 员工操作日志表增加操作结果字段

运行方式:
    python migrate_v12.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def check_column_exists(table, column):
    """检查字段是否存在"""
    try:
        result = db.get_one(f"SELECT {column} FROM {table} LIMIT 1")
        return True
    except:
        return False


def check_table_exists(table):
    """检查表是否存在"""
    try:
        db.get_one(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except:
        return False


def migrate():
    """执行V12.0迁移"""
    migrations_applied = []

    # ========== 1. 会员表增加字段 ==========
    logger.info("检查会员表 business_members 新增字段...")

    if not check_column_exists('business_members', 'member_tags'):
        try:
            db.execute("""
                ALTER TABLE business_members
                ADD COLUMN member_tags VARCHAR(255) DEFAULT '' COMMENT '会员标签，逗号分隔'
            """)
            logger.info("✓ 新增字段 member_tags (会员标签)")
            migrations_applied.append("business_members.member_tags")
        except Exception as e:
            if 'Duplicate' in str(e) or '已存在' in str(e):
                logger.info("- 字段 member_tags 已存在，跳过")
            else:
                logger.warning(f"! 新增 member_tags 失败: {e}")
    else:
        logger.info("- 字段 member_tags 已存在，跳过")

    if not check_column_exists('business_members', 'source_channel'):
        try:
            db.execute("""
                ALTER TABLE business_members
                ADD COLUMN source_channel VARCHAR(50) DEFAULT '' COMMENT '来源渠道：h5/app/miniapp/admin'
            """)
            logger.info("✓ 新增字段 source_channel (来源渠道)")
            migrations_applied.append("business_members.source_channel")
        except Exception as e:
            if 'Duplicate' in str(e) or '已存在' in str(e):
                logger.info("- 字段 source_channel 已存在，跳过")
            else:
                logger.warning(f"! 新增 source_channel 失败: {e}")
    else:
        logger.info("- 字段 source_channel 已存在，跳过")

    if not check_column_exists('business_members', 'last_login_at'):
        try:
            db.execute("""
                ALTER TABLE business_members
                ADD COLUMN last_login_at DATETIME DEFAULT NULL COMMENT '最后登录时间'
            """)
            logger.info("✓ 新增字段 last_login_at (最后登录时间)")
            migrations_applied.append("business_members.last_login_at")
        except Exception as e:
            if 'Duplicate' in str(e) or '已存在' in str(e):
                logger.info("- 字段 last_login_at 已存在，跳过")
            else:
                logger.warning(f"! 新增 last_login_at 失败: {e}")
    else:
        logger.info("- 字段 last_login_at 已存在，跳过")

    # ========== 2. 订单表增加退款处理人字段 ==========
    logger.info("检查订单表 business_orders 新增字段...")

    if not check_column_exists('business_orders', 'refund_operator_id'):
        try:
            db.execute("""
                ALTER TABLE business_orders
                ADD COLUMN refund_operator_id VARCHAR(64) DEFAULT NULL COMMENT '退款处理人员工ID'
            """)
            logger.info("✓ 新增字段 refund_operator_id (退款处理人ID)")
            migrations_applied.append("business_orders.refund_operator_id")
        except Exception as e:
            if 'Duplicate' in str(e) or '已存在' in str(e):
                logger.info("- 字段 refund_operator_id 已存在，跳过")
            else:
                logger.warning(f"! 新增 refund_operator_id 失败: {e}")
    else:
        logger.info("- 字段 refund_operator_id 已存在，跳过")

    if not check_column_exists('business_orders', 'refund_operator_name'):
        try:
            db.execute("""
                ALTER TABLE business_orders
                ADD COLUMN refund_operator_name VARCHAR(100) DEFAULT NULL COMMENT '退款处理人姓名'
            """)
            logger.info("✓ 新增字段 refund_operator_name (退款处理人姓名)")
            migrations_applied.append("business_orders.refund_operator_name")
        except Exception as e:
            if 'Duplicate' in str(e) or '已存在' in str(e):
                logger.info("- 字段 refund_operator_name 已存在，跳过")
            else:
                logger.warning(f"! 新增 refund_operator_name 失败: {e}")
    else:
        logger.info("- 字段 refund_operator_name 已存在，跳过")

    # ========== 3. 员工操作日志表增加操作结果字段 ==========
    logger.info("检查员工操作日志表 business_staff_operation_logs 新增字段...")

    if check_table_exists('business_staff_operation_logs'):
        if not check_column_exists('business_staff_operation_logs', 'operation_result'):
            try:
                db.execute("""
                    ALTER TABLE business_staff_operation_logs
                    ADD COLUMN operation_result VARCHAR(50) DEFAULT NULL COMMENT '操作结果：success/failed'
                """)
                logger.info("✓ 新增字段 operation_result (操作结果)")
                migrations_applied.append("business_staff_operation_logs.operation_result")
            except Exception as e:
                if 'Duplicate' in str(e) or '已存在' in str(e):
                    logger.info("- 字段 operation_result 已存在，跳过")
                else:
                    logger.warning(f"! 新增 operation_result 失败: {e}")
        else:
            logger.info("- 字段 operation_result 已存在，跳过")

        if not check_column_exists('business_staff_operation_logs', 'error_message'):
            try:
                db.execute("""
                    ALTER TABLE business_staff_operation_logs
                    ADD COLUMN error_message TEXT DEFAULT NULL COMMENT '错误信息'
                """)
                logger.info("✓ 新增字段 error_message (错误信息)")
                migrations_applied.append("business_staff_operation_logs.error_message")
            except Exception as e:
                if 'Duplicate' in str(e) or '已存在' in str(e):
                    logger.info("- 字段 error_message 已存在，跳过")
                else:
                    logger.warning(f"! 新增 error_message 失败: {e}")
        else:
            logger.info("- 字段 error_message 已存在，跳过")
    else:
        logger.info("- 表 business_staff_operation_logs 不存在，跳过字段检查")

    # ========== 4. 商品SKU表增加库存预警字段 ==========
    logger.info("检查商品SKU表 business_product_skus 新增字段...")

    if check_table_exists('business_product_skus'):
        if not check_column_exists('business_product_skus', 'low_stock_threshold'):
            try:
                db.execute("""
                    ALTER TABLE business_product_skus
                    ADD COLUMN low_stock_threshold INT DEFAULT 10 COMMENT '库存预警阈值'
                """)
                logger.info("✓ 新增字段 low_stock_threshold (库存预警阈值)")
                migrations_applied.append("business_product_skus.low_stock_threshold")
            except Exception as e:
                if 'Duplicate' in str(e) or '已存在' in str(e):
                    logger.info("- 字段 low_stock_threshold 已存在，跳过")
                else:
                    logger.warning(f"! 新增 low_stock_threshold 失败: {e}")
        else:
            logger.info("- 字段 low_stock_threshold 已存在，跳过")

        if not check_column_exists('business_product_skus', 'is_low_stock_alert'):
            try:
                db.execute("""
                    ALTER TABLE business_product_skus
                    ADD COLUMN is_low_stock_alert TINYINT(1) DEFAULT 0 COMMENT '是否已发送低库存预警'
                """)
                logger.info("✓ 新增字段 is_low_stock_alert (低库存预警标志)")
                migrations_applied.append("business_product_skus.is_low_stock_alert")
            except Exception as e:
                if 'Duplicate' in str(e) or '已存在' in str(e):
                    logger.info("- 字段 is_low_stock_alert 已存在，跳过")
                else:
                    logger.warning(f"! 新增 is_low_stock_alert 失败: {e}")
        else:
            logger.info("- 字段 is_low_stock_alert 已存在，跳过")
    else:
        logger.info("- 表 business_product_skus 不存在，跳过字段检查")

    # ========== 5. 会员积分日志表增加过期相关字段 ==========
    logger.info("检查积分日志表 business_points_log 新增字段...")

    if check_table_exists('business_points_log'):
        if not check_column_exists('business_points_log', 'expired_at'):
            try:
                db.execute("""
                    ALTER TABLE business_points_log
                    ADD COLUMN expired_at DATETIME DEFAULT NULL COMMENT '积分过期时间'
                """)
                logger.info("✓ 新增字段 expired_at (积分过期时间)")
                migrations_applied.append("business_points_log.expired_at")
            except Exception as e:
                if 'Duplicate' in str(e) or '已存在' in str(e):
                    logger.info("- 字段 expired_at 已存在，跳过")
                else:
                    logger.warning(f"! 新增 expired_at 失败: {e}")
        else:
            logger.info("- 字段 expired_at 已存在，跳过")

        if not check_column_exists('business_points_log', 'source_order_no'):
            try:
                db.execute("""
                    ALTER TABLE business_points_log
                    ADD COLUMN source_order_no VARCHAR(64) DEFAULT NULL COMMENT '来源订单号'
                """)
                logger.info("✓ 新增字段 source_order_no (来源订单号)")
                migrations_applied.append("business_points_log.source_order_no")
            except Exception as e:
                if 'Duplicate' in str(e) or '已存在' in str(e):
                    logger.info("- 字段 source_order_no 已存在，跳过")
                else:
                    logger.warning(f"! 新增 source_order_no 失败: {e}")
        else:
            logger.info("- 字段 source_order_no 已存在，跳过")
    else:
        logger.info("- 表 business_points_log 不存在，跳过字段检查")

    # ========== 6. 创建库存预警视图（如果不存在）==========
    logger.info("检查库存预警视图...")

    try:
        # 尝试查询视图
        db.get_all("SELECT 1 FROM business_low_stock_view LIMIT 1")
        logger.info("- 视图 business_low_stock_view 已存在，跳过")
    except:
        try:
            db.execute("""
                CREATE OR REPLACE VIEW business_low_stock_view AS
                SELECT
                    p.id as product_id,
                    p.name as product_name,
                    p.category as category,
                    s.id as sku_id,
                    s.name as sku_name,
                    s.stock as current_stock,
                    COALESCE(s.low_stock_threshold, 10) as threshold,
                    p.ec_id,
                    p.project_id
                FROM business_products p
                INNER JOIN business_product_skus s ON p.id = s.product_id
                WHERE p.deleted = 0 AND s.stock <= COALESCE(s.low_stock_threshold, 10)
                ORDER BY s.stock ASC
            """)
            logger.info("✓ 创建视图 business_low_stock_view (库存预警视图)")
            migrations_applied.append("business_low_stock_view")
        except Exception as e:
            logger.warning(f"! 创建库存预警视图失败: {e}")

    # ========== 7. 创建会员活跃度统计视图 ==========
    logger.info("检查会员活跃度视图...")

    try:
        db.get_all("SELECT 1 FROM business_member_activity_view LIMIT 1")
        logger.info("- 视图 business_member_activity_view 已存在，跳过")
    except:
        try:
            db.execute("""
                CREATE OR REPLACE VIEW business_member_activity_view AS
                SELECT
                    m.user_id,
                    m.user_name,
                    m.phone,
                    m.member_level,
                    m.points,
                    m.total_points,
                    m.balance,
                    m.ec_id,
                    m.project_id,
                    COALESCE(cl.checkin_count, 0) as total_checkins,
                    COALESCE(cl.last_checkin, '') as last_checkin_date,
                    COALESCE(o.order_count, 0) as order_count,
                    COALESCE(o.total_amount, 0) as total_amount,
                    m.created_at as member_since,
                    m.last_login_at
                FROM business_members m
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as checkin_count, MAX(checkin_date) as last_checkin
                    FROM business_checkin_logs GROUP BY user_id
                ) cl ON m.user_id = cl.user_id
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as order_count, SUM(actual_amount) as total_amount
                    FROM business_orders WHERE order_status IN ('paid', 'completed') GROUP BY user_id
                ) o ON m.user_id = o.user_id
                WHERE m.deleted = 0
            """)
            logger.info("✓ 创建视图 business_member_activity_view (会员活跃度视图)")
            migrations_applied.append("business_member_activity_view")
        except Exception as e:
            logger.warning(f"! 创建会员活跃度视图失败: {e}")

    # ========== 汇总 ==========
    logger.info("=" * 50)
    if migrations_applied:
        logger.info(f"V12.0 迁移完成！共应用 {len(migrations_applied)} 项变更:")
        for item in migrations_applied:
            logger.info(f"  • {item}")
    else:
        logger.info("V12.0 迁移检查完成，无需变更（或所有字段已存在）")
    logger.info("=" * 50)

    return migrations_applied


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("社区商业服务系统 - V12.0 数据库迁移")
    print("=" * 50 + "\n")

    try:
        migrate()
        print("\n✅ 迁移脚本执行成功！")
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        sys.exit(1)
