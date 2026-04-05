#!/usr/bin/env python3
"""
V7.0 数据库迁移脚本
新增功能:
1. business_cart - 购物车表
2. business_order_items - 订单明细表
3. business_notices - 公告表
4. business_products 增加 stock 库存字段
5. business_orders 增加 items_snapshot 字段
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

# 1. 购物车表
CREATE_CART_SQL = """
CREATE TABLE IF NOT EXISTS business_cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    product_id INT NOT NULL COMMENT '商品ID',
    quantity INT DEFAULT 1 COMMENT '数量',
    selected TINYINT DEFAULT 1 COMMENT '是否选中 0-否 1-是',
    ec_id VARCHAR(64) COMMENT '企业ID',
    project_id VARCHAR(64) COMMENT '项目ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_product (product_id),
    UNIQUE KEY uk_user_product (user_id, product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购物车表'
"""

# 2. 订单明细表
CREATE_ORDER_ITEMS_SQL = """
CREATE TABLE IF NOT EXISTS business_order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL COMMENT '订单ID',
    product_id INT COMMENT '商品ID',
    product_name VARCHAR(255) NOT NULL COMMENT '商品名称(快照)',
    price DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '单价(快照)',
    quantity INT NOT NULL DEFAULT 1 COMMENT '数量',
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '小计',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order (order_id),
    INDEX idx_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细表'
"""

# 3. 公告表
CREATE_NOTICES_SQL = """
CREATE TABLE IF NOT EXISTS business_notices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL COMMENT '公告标题',
    content TEXT COMMENT '公告内容',
    notice_type VARCHAR(20) DEFAULT 'general' COMMENT '类型: general-普通/activity-活动/urgent-紧急',
    importance INT DEFAULT 0 COMMENT '重要程度 0-普通 1-重要 2-紧急',
    status VARCHAR(20) DEFAULT 'published' COMMENT 'published-已发布/draft-草稿',
    start_date DATE COMMENT '生效日期',
    end_date DATE COMMENT '失效日期',
    ec_id VARCHAR(64) COMMENT '企业ID',
    project_id VARCHAR(64) COMMENT '项目ID',
    created_by VARCHAR(64) COMMENT '创建人ID',
    created_by_name VARCHAR(100) COMMENT '创建人名称',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status, deleted),
    INDEX idx_ec (ec_id, project_id),
    INDEX idx_date (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='公告表'
"""

# 4. 商品表增加库存字段
ALTER_PRODUCTS_SQL = """
ALTER TABLE business_products
ADD COLUMN IF NOT EXISTS stock INT DEFAULT -1 COMMENT '库存 -1表示不限库存' AFTER price,
ADD COLUMN IF NOT EXISTS unit VARCHAR(20) DEFAULT '' COMMENT '单位(件/个/份)' AFTER stock,
ADD COLUMN IF NOT EXISTS sales_count INT DEFAULT 0 COMMENT '销售数量' AFTER unit
"""

# 5. 订单表增加 items_snapshot 字段
ALTER_ORDERS_SQL = """
ALTER TABLE business_orders
ADD COLUMN IF NOT EXISTS items_snapshot TEXT COMMENT '下单时商品快照JSON' AFTER remark,
ADD COLUMN IF NOT EXISTS delivery_address VARCHAR(500) COMMENT '配送地址' AFTER items_snapshot
"""

# 6. 场馆表增加评分缓存字段
ALTER_VENUES_SQL = """
ALTER TABLE business_venues
ADD COLUMN IF NOT EXISTS avg_rating DECIMAL(3,1) DEFAULT 0 COMMENT '平均评分缓存' AFTER capacity,
ADD COLUMN IF NOT EXISTS review_count INT DEFAULT 0 COMMENT '评价数量缓存' AFTER avg_rating
"""

# 7. 门店表增加评分缓存字段
ALTER_SHOPS_SQL = """
ALTER TABLE business_shops
ADD COLUMN IF NOT EXISTS avg_rating DECIMAL(3,1) DEFAULT 0 COMMENT '平均评分缓存' AFTER phone,
ADD COLUMN IF NOT EXISTS review_count INT DEFAULT 0 COMMENT '评价数量缓存' AFTER avg_rating,
ADD COLUMN IF NOT EXISTS images TEXT COMMENT '门店图片JSON数组' AFTER review_count
"""


def migrate():
    """执行V7.0迁移"""
    results = []
    errors = []

    tasks = [
        ("购物车表(business_cart)", CREATE_CART_SQL),
        ("订单明细表(business_order_items)", CREATE_ORDER_ITEMS_SQL),
        ("公告表(business_notices)", CREATE_NOTICES_SQL),
        ("商品表增加库存字段", ALTER_PRODUCTS_SQL),
        ("订单表增加快照字段", ALTER_ORDERS_SQL),
        ("场馆表增加评分缓存", ALTER_VENUES_SQL),
        ("门店表增加评分缓存", ALTER_SHOPS_SQL),
    ]

    for name, sql in tasks:
        try:
            db.execute(sql)
            print(f"✅ {name} 成功")
            results.append(name)
        except Exception as e:
            err_msg = str(e)
            # 字段已存在是正常的
            if "Duplicate column" in err_msg or "already exists" in err_msg.lower():
                print(f"ℹ️  {name}: 字段/表已存在，跳过")
                results.append(name + "(已存在)")
            else:
                print(f"⚠️  {name}: {err_msg}")
                errors.append(f"{name}: {err_msg}")

    print(f"\n🎉 V7.0迁移完成! 共完成 {len(results)} 项")
    if errors:
        print(f"⚠️  以下 {len(errors)} 项出现警告:")
        for e in errors:
            print(f"   - {e}")
    return results


if __name__ == '__main__':
    migrate()
