"""
V32.0 迁移脚本 - 订单增强
- 添加订单留言表
- 添加部分退款表
- 优化订单表字段
"""
import logging
from . import db

logger = logging.getLogger(__name__)


def run():
    """执行迁移"""
    logger.info("开始 V32.0 订单增强迁移...")

    # 1. 创建订单留言表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_order_notes (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                note_no VARCHAR(32) NOT NULL UNIQUE COMMENT '留言编号',
                order_id BIGINT NOT NULL COMMENT '订单ID',
                user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
                note_type VARCHAR(20) NOT NULL DEFAULT 'user_question' COMMENT '留言类型: user_question/staff_reply/system_notice',
                content TEXT NOT NULL COMMENT '留言内容',
                ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
                project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                deleted TINYINT(1) DEFAULT 0 COMMENT '删除标记',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_order (order_id),
                INDEX idx_user (user_id),
                INDEX idx_type (note_type),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单留言表'
        """)
        logger.info("  ✓ 创建表: business_order_notes")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_order_notes 失败: {e}")

    # 2. 创建部分退款表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_partial_refunds (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                refund_no VARCHAR(32) NOT NULL UNIQUE COMMENT '退款编号',
                order_id BIGINT NOT NULL COMMENT '订单ID',
                user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
                items JSON NOT NULL COMMENT '退款商品列表',
                refund_amount DECIMAL(10,2) NOT NULL COMMENT '退款金额',
                reason VARCHAR(200) DEFAULT NULL COMMENT '退款原因',
                status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/processing/approved/rejected',
                reject_reason VARCHAR(200) DEFAULT NULL COMMENT '拒绝原因',
                ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
                project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                deleted TINYINT(1) DEFAULT 0 COMMENT '删除标记',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME DEFAULT NULL COMMENT '处理时间',
                INDEX idx_order (order_id),
                INDEX idx_user (user_id),
                INDEX idx_status (status),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部分退款记录表'
        """)
        logger.info("  ✓ 创建表: business_partial_refunds")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_partial_refunds 失败: {e}")

    # 3. 添加订单扩展字段
    order_fields = [
        ("delivery_note", "VARCHAR(100) DEFAULT NULL COMMENT '配送备注'"),
        ("cancel_reason", "VARCHAR(200) DEFAULT NULL COMMENT '取消原因'"),
        ("cancelled_at", "DATETIME DEFAULT NULL COMMENT '取消时间'"),
    ]

    for field, field_def in order_fields:
        try:
            result = db.get_one("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'business_orders'
                AND COLUMN_NAME = %s
            """, [field])

            if result and result.get('cnt', 0) == 0:
                db.execute(f"ALTER TABLE business_orders ADD COLUMN {field} {field_def}")
                logger.info(f"  ✓ 添加字段: business_orders.{field}")
            else:
                logger.info(f"  - 字段已存在: business_orders.{field}")
        except Exception as e:
            logger.warning(f"  ! 添加字段 business_orders.{field} 失败: {e}")

    # 4. 添加订单索引
    order_indexes = [
        ("idx_cancel", "cancel_reason, cancelled_at"),
        ("idx_delivery_note", "delivery_note"),
    ]

    for idx_name, idx_cols in order_indexes:
        try:
            result = db.get_one("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'business_orders'
                AND INDEX_NAME = %s
            """, [idx_name])

            if result and result.get('cnt', 0) == 0:
                db.execute(f"ALTER TABLE business_orders ADD INDEX {idx_name} ({idx_cols})")
                logger.info(f"  ✓ 添加索引: {idx_name} ({idx_cols})")
            else:
                logger.info(f"  - 索引已存在: {idx_name}")
        except Exception as e:
            logger.warning(f"  ! 添加索引 {idx_name} 失败: {e}")

    logger.info("V32.0 订单增强迁移完成!")


if __name__ == '__main__':
    run()
