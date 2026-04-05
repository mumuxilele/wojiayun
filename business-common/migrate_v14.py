#!/usr/bin/env python3
"""
V14.0 数据库迁移脚本
幂等设计：支持安全重试

新增内容:
1. 商品分类表 business_product_categories
2. 商品表新增 low_stock_notified 字段（库存预警标记）
3. 商品表新增 product_code 字段（商品编码）
4. 员工操作日志表新增 performance_score 字段（绩效评分）

运行方式:
    python migrate_v14.py
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
        db.get_one(f"SELECT {column} FROM {table} LIMIT 1")
        return True
    except Exception:
        return False


def check_table_exists(table):
    """检查表是否存在"""
    try:
        db.get_one(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except Exception:
        return False


def check_index_exists(index_name):
    """检查索引是否存在"""
    try:
        result = db.get_one(
            "SELECT COUNT(*) as cnt FROM information_schema.STATISTICS WHERE INDEX_NAME=%s",
            [index_name]
        )
        return result and result.get('cnt', 0) > 0
    except Exception:
        return False


def migrate():
    """执行V14.0迁移"""
    migrations_applied = []

    # ========== 1. 创建商品分类表 ==========
    logger.info("检查商品分类表...")
    if not check_table_exists('business_product_categories'):
        logger.info("  创建表 business_product_categories...")
        db.execute("""
            CREATE TABLE business_product_categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category_name VARCHAR(100) NOT NULL COMMENT '分类名称',
                parent_id INT DEFAULT 0 COMMENT '父分类ID，0为顶级',
                icon VARCHAR(500) DEFAULT '' COMMENT '分类图标URL',
                sort_order INT DEFAULT 0 COMMENT '排序（越小越靠前）',
                status TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
                ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
                project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_parent (parent_id),
                INDEX idx_ec_project (ec_id, project_id),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表'
        """)
        migrations_applied.append('创建商品分类表 business_product_categories')
        logger.info("  商品分类表创建成功")
    else:
        logger.info("  商品分类表已存在，跳过")

    # ========== 2. 商品表新增字段 ==========
    logger.info("检查商品表 business_products 新增字段...")

    if not check_column_exists('business_products', 'low_stock_notified'):
        logger.info("  新增字段 low_stock_notified...")
        db.execute("""
            ALTER TABLE business_products
            ADD COLUMN low_stock_notified TINYINT DEFAULT 0 COMMENT '低库存是否已通知 0未通知 1已通知'
        """)
        migrations_applied.append('business_products.low_stock_notified')
        logger.info("  low_stock_notified 字段添加成功")
    else:
        logger.info("  low_stock_notified 字段已存在，跳过")

    if not check_column_exists('business_products', 'product_code'):
        logger.info("  新增字段 product_code...")
        db.execute("""
            ALTER TABLE business_products
            ADD COLUMN product_code VARCHAR(50) DEFAULT NULL COMMENT '商品编码（唯一）'
        """)
        db.execute("CREATE UNIQUE INDEX idx_product_code ON business_products(product_code) WHERE product_code IS NOT NULL")
        migrations_applied.append('business_products.product_code')
        logger.info("  product_code 字段添加成功")
    else:
        logger.info("  product_code 字段已存在，跳过")

    # ========== 3. 员工操作日志表新增绩效字段 ==========
    logger.info("检查员工操作日志表...")
    if check_table_exists('business_staff_operation_logs'):
        if not check_column_exists('business_staff_operation_logs', 'performance_score'):
            logger.info("  新增字段 performance_score...")
            db.execute("""
                ALTER TABLE business_staff_operation_logs
                ADD COLUMN performance_score DECIMAL(5,2) DEFAULT NULL COMMENT '绩效评分（1-5）'
            """)
            migrations_applied.append('business_staff_operation_logs.performance_score')
            logger.info("  performance_score 字段添加成功")
        else:
            logger.info("  performance_score 字段已存在，跳过")
    else:
        logger.info("  员工操作日志表不存在，跳过")

    # ========== 4. 新增索引优化 ==========
    logger.info("检查索引优化...")

    indexes = [
        ('idx_products_ec_project_status', 'business_products', 'ALTER TABLE business_products ADD INDEX idx_products_ec_project_status (ec_id, project_id, status)'),
        ('idx_products_stock', 'business_products', 'ALTER TABLE business_products ADD INDEX idx_products_stock (stock, status)'),
        ('idx_products_category', 'business_products', 'ALTER TABLE business_products ADD INDEX idx_products_category (category, ec_id)'),
        ('idx_orders_created_status', 'business_orders', 'ALTER TABLE business_orders ADD INDEX idx_orders_created_status (DATE(created_at), order_status)'),
        ('idx_apps_created_status', 'business_applications', 'ALTER TABLE business_applications ADD INDEX idx_apps_created_status (DATE(created_at), status)'),
    ]

    for idx_name, table, sql in indexes:
        if not check_index_exists(idx_name):
            try:
                db.execute(sql)
                migrations_applied.append(f'索引 {idx_name}')
                logger.info(f"  索引 {idx_name} 创建成功")
            except Exception as e:
                logger.warning(f"  索引 {idx_name} 创建失败: {e}")
        else:
            logger.info(f"  索引 {idx_name} 已存在，跳过")

    # ========== 5. 插入默认分类 ==========
    logger.info("检查默认商品分类...")
    if check_table_exists('business_product_categories'):
        try:
            count = db.get_total("SELECT COUNT(*) FROM business_product_categories WHERE parent_id=0")
            if count == 0:
                default_categories = [
                    ('生鲜果蔬', 1), ('粮油副食', 2), ('日用百货', 3),
                    ('家居家电', 4), ('服装鞋帽', 5), ('美妆个护', 6),
                    ('食品饮料', 7), ('其他', 99)
                ]
                for name, sort_order in default_categories:
                    db.execute(
                        "INSERT INTO business_product_categories (category_name, parent_id, sort_order, status) VALUES (%s, 0, %s, 1)",
                        [name, sort_order]
                    )
                migrations_applied.append('插入默认商品分类')
                logger.info(f"  已插入 {len(default_categories)} 个默认分类")
            else:
                logger.info("  默认分类已存在，跳过")
        except Exception as e:
            logger.warning(f"  默认分类插入失败: {e}")

    # ========== 汇总 ==========
    logger.info("=" * 60)
    if migrations_applied:
        logger.info(f"V14.0迁移完成，共执行 {len(migrations_applied)} 项:")
        for i, m in enumerate(migrations_applied, 1):
            logger.info(f"  {i}. {m}")
    else:
        logger.info("V14.0迁移完成，所有变更已存在，无需更新")
    logger.info("=" * 60)

    return migrations_applied


if __name__ == '__main__':
    migrate()
