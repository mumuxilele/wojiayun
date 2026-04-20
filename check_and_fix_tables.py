#!/usr/bin/env python3
"""
检查和修复数据库表结构
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business_common import db

def check_table_columns(table_name):
    """检查表的字段"""
    try:
        columns = db.get_all(f"SHOW COLUMNS FROM {table_name}")
        return [col['Field'] for col in columns or []]
    except Exception as e:
        print(f"  获取表结构失败: {e}")
        return []

def fix_favorites_table():
    """修复收藏表"""
    print("\n[1/4] 检查 business_favorites 表...")
    columns = check_table_columns('business_favorites')
    
    if not columns:
        print("  表不存在，需要创建表")
        try:
            db.execute("""
                CREATE TABLE IF NOT EXISTS business_favorites (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
                    user_name VARCHAR(100) DEFAULT '' COMMENT '用户名',
                    target_type ENUM('venue', 'shop', 'product') NOT NULL COMMENT '收藏对象类型',
                    target_id INT NOT NULL COMMENT '收藏对象ID',
                    target_name VARCHAR(200) DEFAULT '' COMMENT '收藏对象名称（冗余）',
                    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
                    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE KEY uk_user_target (user_id, target_type, target_id),
                    KEY idx_user_id (user_id),
                    KEY idx_target (target_type, target_id),
                    KEY idx_ec_project (ec_id, project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户收藏表'
            """)
            print("  ✓ 表创建成功")
        except Exception as e:
            print(f"  ✗ 表创建失败: {e}")
        return
    
    print(f"  现有字段: {columns}")
    
    # 检查 target_name 字段
    if 'target_name' not in columns:
        print("  添加 target_name 字段...")
        try:
            db.execute("""
                ALTER TABLE business_favorites 
                ADD COLUMN target_name VARCHAR(200) DEFAULT '' COMMENT '收藏对象名称（冗余）'
            """)
            print("  ✓ target_name 字段添加成功")
        except Exception as e:
            print(f"  ✗ 添加失败: {e}")
    else:
        print("  ✓ target_name 字段已存在")

def fix_cart_table():
    """修复购物车表"""
    print("\n[2/4] 检查 business_cart 表...")
    columns = check_table_columns('business_cart')
    
    if not columns:
        print("  表不存在，需要创建表")
        try:
            db.execute("""
                CREATE TABLE IF NOT EXISTS business_cart (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    fid VARCHAR(32) UNIQUE COMMENT 'FID主键',
                    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
                    product_id INT NOT NULL COMMENT '商品ID',
                    sku_id INT DEFAULT NULL COMMENT 'SKU ID',
                    quantity INT NOT NULL DEFAULT 1 COMMENT '数量',
                    selected TINYINT DEFAULT 1 COMMENT '是否选中',
                    deleted TINYINT DEFAULT 0 COMMENT '是否删除',
                    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
                    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                    session_id VARCHAR(64) DEFAULT NULL COMMENT '游客会话ID',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    
                    KEY idx_user_id (user_id),
                    KEY idx_product (product_id),
                    KEY idx_sku (sku_id),
                    KEY idx_ec_project (ec_id, project_id),
                    KEY idx_session (session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购物车表'
            """)
            print("  ✓ 表创建成功")
        except Exception as e:
            print(f"  ✗ 表创建失败: {e}")
        return
    
    print(f"  表存在，字段数: {len(columns)}")
    print(f"  字段: {columns}")

def fix_product_skus_table():
    """修复商品SKU表"""
    print("\n[3/4] 检查 business_product_skus 表...")
    columns = check_table_columns('business_product_skus')
    
    if not columns:
        print("  表不存在，需要创建表")
        try:
            db.execute("""
                CREATE TABLE IF NOT EXISTS business_product_skus (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    fid VARCHAR(32) UNIQUE COMMENT 'FID主键',
                    product_id INT NOT NULL COMMENT '商品ID',
                    sku_code VARCHAR(100) NOT NULL COMMENT 'SKU编码',
                    sku_name VARCHAR(200) DEFAULT '' COMMENT 'SKU名称',
                    specs JSON COMMENT '规格属性JSON',
                    price DECIMAL(10,2) NOT NULL COMMENT '售价',
                    original_price DECIMAL(10,2) DEFAULT NULL COMMENT '原价',
                    stock INT NOT NULL DEFAULT 0 COMMENT '库存',
                    status VARCHAR(20) DEFAULT 'active' COMMENT '状态',
                    deleted TINYINT DEFAULT 0 COMMENT '是否删除',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    
                    KEY idx_product (product_id),
                    KEY idx_sku_code (sku_code),
                    KEY idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品SKU表'
            """)
            print("  ✓ 表创建成功")
        except Exception as e:
            print(f"  ✗ 表创建失败: {e}")
        return
    
    print(f"  表存在，字段数: {len(columns)}")

def fix_coupons_tables():
    """修复优惠券表"""
    print("\n[4/4] 检查优惠券相关表...")
    
    # 检查 business_coupons 表
    columns = check_table_columns('business_coupons')
    if not columns:
        print("  business_coupons 表不存在")
    else:
        print(f"  business_coupons 表存在，字段数: {len(columns)}")
    
    # 检查 business_user_coupons 表
    columns = check_table_columns('business_user_coupons')
    if not columns:
        print("  business_user_coupons 表不存在")
    else:
        print(f"  business_user_coupons 表存在，字段数: {len(columns)}")

if __name__ == '__main__':
    print("=" * 60)
    print("数据库表结构检查和修复工具")
    print("=" * 60)
    
    fix_favorites_table()
    fix_cart_table()
    fix_product_skus_table()
    fix_coupons_tables()
    
    print("\n" + "=" * 60)
    print("检查和修复完成")
    print("=" * 60)
