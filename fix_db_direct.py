#!/usr/bin/env python3
"""
数据库表结构修复脚本 - 直接使用 pymysql
"""
import pymysql
import sys
import os

# 数据库配置
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'Wojiacloud$2023')
DB_NAME = 'visit_system'

def get_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def run_sql_safe(sql, description=""):
    """执行SQL语句，忽略已存在的错误"""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        conn.close()
        print(f"  ✓ {description}")
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if 'already exists' in error_msg or 'duplicate' in error_msg:
            print(f"  ⚠ {description} - 字段/表已存在")
        elif 'doesn\'t exist' in error_msg or "doesn't exist" in error_msg:
            print(f"  ⚠ {description} - 表不存在")
        else:
            print(f"  ✗ {description} - {e}")
        return False

def fix_favorites_table():
    """修复收藏表"""
    print("\n[1/6] 修复 business_favorites 表...")
    
    run_sql_safe(
        "ALTER TABLE business_favorites ADD COLUMN IF NOT EXISTS target_name VARCHAR(200) DEFAULT '' COMMENT '收藏对象名称'",
        "添加 target_name 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_favorites ADD COLUMN IF NOT EXISTS ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID'",
        "添加 ec_id 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_favorites ADD COLUMN IF NOT EXISTS project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID'",
        "添加 project_id 字段"
    )

def fix_cart_table():
    """修复购物车表"""
    print("\n[2/6] 修复 business_cart 表...")
    
    run_sql_safe(
        "ALTER TABLE business_cart ADD COLUMN IF NOT EXISTS deleted TINYINT DEFAULT 0 COMMENT '是否删除'",
        "添加 deleted 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_cart ADD COLUMN IF NOT EXISTS selected TINYINT DEFAULT 1 COMMENT '是否选中'",
        "添加 selected 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_cart ADD COLUMN IF NOT EXISTS fid VARCHAR(32) UNIQUE COMMENT 'FID主键'",
        "添加 fid 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_cart ADD COLUMN IF NOT EXISTS ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID'",
        "添加 ec_id 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_cart ADD COLUMN IF NOT EXISTS project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID'",
        "添加 project_id 字段"
    )

def fix_product_skus_table():
    """修复商品SKU表"""
    print("\n[3/6] 修复 business_product_skus 表...")
    
    run_sql_safe(
        """CREATE TABLE IF NOT EXISTS business_product_skus (
            id INT AUTO_INCREMENT PRIMARY KEY,
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品SKU表'""",
        "创建 business_product_skus 表"
    )

def fix_members_table():
    """修复会员表字段"""
    print("\n[4/6] 修复 business_members 表...")
    
    run_sql_safe(
        "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID'",
        "添加 ec_id 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID'",
        "添加 project_id 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS deleted TINYINT DEFAULT 0 COMMENT '是否删除'",
        "添加 deleted 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS member_level VARCHAR(20) DEFAULT 'bronze' COMMENT '会员等级'",
        "添加 member_level 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS points INT DEFAULT 0 COMMENT '积分'",
        "添加 points 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS total_points INT DEFAULT 0 COMMENT '总积分'",
        "添加 total_points 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS member_name VARCHAR(100) DEFAULT '' COMMENT '会员名称'",
        "添加 member_name 字段"
    )

def fix_coupons_tables():
    """修复优惠券表"""
    print("\n[5/6] 修复优惠券相关表...")
    
    run_sql_safe(
        """CREATE TABLE IF NOT EXISTS business_coupons (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(32) UNIQUE COMMENT 'FID主键',
            coupon_code VARCHAR(64) UNIQUE COMMENT '优惠券编码',
            coupon_name VARCHAR(200) NOT NULL COMMENT '优惠券名称',
            coupon_type VARCHAR(50) DEFAULT 'amount' COMMENT '类型',
            discount_value DECIMAL(10,2) NOT NULL COMMENT '优惠金额或折扣率',
            min_amount DECIMAL(10,2) DEFAULT 0 COMMENT '最低使用金额',
            max_discount DECIMAL(10,2) DEFAULT NULL COMMENT '最大优惠金额',
            total_count INT DEFAULT -1 COMMENT '总数量',
            used_count INT DEFAULT 0 COMMENT '已使用数量',
            valid_from DATE DEFAULT NULL COMMENT '开始日期',
            valid_until DATE DEFAULT NULL COMMENT '结束日期',
            status VARCHAR(20) DEFAULT 'active' COMMENT '状态',
            deleted TINYINT DEFAULT 0 COMMENT '是否删除',
            ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
            project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_status (status),
            KEY idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券表'""",
        "创建 business_coupons 表"
    )
    
    run_sql_safe(
        """CREATE TABLE IF NOT EXISTS business_user_coupons (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(32) UNIQUE COMMENT 'FID主键',
            user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
            coupon_id INT NOT NULL COMMENT '优惠券ID',
            coupon_code VARCHAR(64) COMMENT '优惠券编码',
            status VARCHAR(20) DEFAULT 'unused' COMMENT '状态',
            used_at DATETIME DEFAULT NULL COMMENT '使用时间',
            order_id INT DEFAULT NULL COMMENT '使用订单ID',
            ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
            project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_user_id (user_id),
            KEY idx_coupon_id (coupon_id),
            KEY idx_status (status),
            KEY idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户优惠券表'""",
        "创建 business_user_coupons 表"
    )

def fix_shops_table():
    """修复门店表"""
    print("\n[6/6] 修复 business_shops 表...")
    
    run_sql_safe(
        "ALTER TABLE business_shops ADD COLUMN IF NOT EXISTS ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID'",
        "添加 ec_id 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_shops ADD COLUMN IF NOT EXISTS project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID'",
        "添加 project_id 字段"
    )
    
    run_sql_safe(
        "ALTER TABLE business_shops ADD COLUMN IF NOT EXISTS deleted TINYINT DEFAULT 0 COMMENT '是否删除'",
        "添加 deleted 字段"
    )

if __name__ == '__main__':
    print("=" * 60)
    print("数据库表结构修复脚本")
    print("=" * 60)
    
    fix_favorites_table()
    fix_cart_table()
    fix_product_skus_table()
    fix_members_table()
    fix_coupons_tables()
    fix_shops_table()
    
    print("\n" + "=" * 60)
    print("所有修复操作执行完成")
    print("=" * 60)
