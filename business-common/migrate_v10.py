#!/usr/bin/env python3
"""
V10.0 数据库迁移脚本
新增/修改：
- business_products 表新增 original_price, sort_order 字段
- business_cart 表确保存在（购物车）
- 无需新增表，主要是字段补全与索引优化
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from business_common import config, db

def safe_alter(cursor, conn, table, column, definition, desc):
    """安全地添加字段（如果不存在）"""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        conn.commit()
        print(f"  [OK] {desc} 添加成功")
    except Exception as e:
        err = str(e)
        if '1060' in err or 'Duplicate column' in err or 'already exists' in err.lower():
            print(f"  [-] {desc} 已存在，跳过")
        else:
            print(f"  [WARN] {desc} 添加失败: {e}")

def safe_create_index(cursor, conn, table, index_name, columns, desc):
    try:
        cursor.execute(f"CREATE INDEX {index_name} ON {table} ({columns})")
        conn.commit()
        print(f"  [OK] {desc} 索引创建成功")
    except Exception as e:
        err = str(e)
        if '1061' in err or 'Duplicate key name' in err:
            print(f"  [-] {desc} 索引已存在，跳过")
        else:
            print(f"  [WARN] {desc} 索引失败: {e}")

def migrate():
    print("=" * 60)
    print("V10.0 数据库迁移开始")
    print("=" * 60)

    conn = db.get_db()
    cursor = conn.cursor()

    # ========== 1. business_products 字段补全 ==========
    print("\n[1/4] 检查 business_products 字段...")
    safe_alter(cursor, conn, 'business_products', 'original_price', 'DECIMAL(10,2) DEFAULT NULL COMMENT "原价"', 'business_products.original_price')
    safe_alter(cursor, conn, 'business_products', 'sort_order', 'INT DEFAULT 0 COMMENT "排序权重"', 'business_products.sort_order')

    # ========== 2. business_cart 表确保存在 ==========
    print("\n[2/4] 确保 business_cart 表存在...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_cart (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
                product_id BIGINT NOT NULL COMMENT '商品ID',
                sku_id BIGINT DEFAULT NULL COMMENT 'SKU规格ID',
                sku_name VARCHAR(100) DEFAULT NULL COMMENT 'SKU规格名称',
                quantity INT DEFAULT 1 COMMENT '数量',
                selected TINYINT(1) DEFAULT 1 COMMENT '是否选中',
                ec_id VARCHAR(64) DEFAULT NULL,
                project_id VARCHAR(64) DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                KEY idx_user_id (user_id),
                KEY idx_product_id (product_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购物车'
        """)
        conn.commit()
        print("  [OK] business_cart 表确认存在")
    except Exception as e:
        print(f"  [WARN] {e}")

    # ========== 3. business_orders 退款相关字段 ==========
    print("\n[3/4] 检查 business_orders 退款字段...")
    safe_alter(cursor, conn, 'business_orders', 'refund_status', "VARCHAR(20) DEFAULT NULL COMMENT '退款状态'", 'business_orders.refund_status')

    # ========== 4. 性能索引优化 ==========
    print("\n[4/4] 添加性能索引...")
    safe_create_index(cursor, conn, 'business_products', 'idx_products_category', 'category', 'business_products(category)')
    safe_create_index(cursor, conn, 'business_products', 'idx_products_shop_status', 'shop_id, status', 'business_products(shop_id, status)')
    safe_create_index(cursor, conn, 'business_checkin_logs', 'idx_checkin_date_only', 'checkin_date', 'business_checkin_logs(checkin_date)')
    safe_create_index(cursor, conn, 'business_user_coupons', 'idx_coupons_status', 'status, used_at', 'business_user_coupons(status, used_at)')

    print("\n" + "=" * 60)
    print("V10.0 数据库迁移完成")
    print("=" * 60)

    cursor.close()
    conn.close()


if __name__ == '__main__':
    migrate()
