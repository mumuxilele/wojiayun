"""
V32.0 迁移脚本 - 库存预警系统
- 创建库存预警表
- 添加商品低库存阈值字段
"""
import logging
from . import db

logger = logging.getLogger(__name__)


def run():
    """执行迁移"""
    logger.info("开始 V32.0 库存预警系统迁移...")

    # 1. 创建库存预警表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_inventory_alerts (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                alert_no VARCHAR(32) NOT NULL UNIQUE COMMENT '预警编号',
                product_id BIGINT NOT NULL COMMENT '商品ID',
                product_name VARCHAR(200) NOT NULL COMMENT '商品名称',
                current_stock INT NOT NULL DEFAULT 0 COMMENT '当前库存',
                alert_level VARCHAR(20) NOT NULL DEFAULT 'warning' COMMENT '预警等级: critical/warning/notice',
                suggest_replenish INT DEFAULT 0 COMMENT '建议补货量',
                status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '状态: active/resolved',
                resolved_by VARCHAR(64) DEFAULT NULL COMMENT '处理人',
                resolution_note VARCHAR(500) DEFAULT NULL COMMENT '处理备注',
                resolved_at DATETIME DEFAULT NULL COMMENT '处理时间',
                ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
                project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                deleted TINYINT(1) DEFAULT 0 COMMENT '删除标记',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_product (product_id),
                INDEX idx_status (status),
                INDEX idx_level (alert_level),
                INDEX idx_ec_project (ec_id, project_id),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存预警表'
        """)
        logger.info("  ✓ 创建表: business_inventory_alerts")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_inventory_alerts 失败: {e}")

    # 2. 添加商品低库存阈值字段
    try:
        result = db.get_one("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'business_products'
            AND COLUMN_NAME = 'low_stock_threshold'
        """)

        if result and result.get('cnt', 0) == 0:
            db.execute("""
                ALTER TABLE business_products
                ADD COLUMN low_stock_threshold INT DEFAULT 10 COMMENT '低库存预警阈值'
            """)
            logger.info("  ✓ 添加字段: business_products.low_stock_threshold")
        else:
            logger.info("  - 字段已存在: business_products.low_stock_threshold")
    except Exception as e:
        logger.warning(f"  ! 添加字段 business_products.low_stock_threshold 失败: {e}")

    logger.info("V32.0 库存预警系统迁移完成!")


if __name__ == '__main__':
    run()
