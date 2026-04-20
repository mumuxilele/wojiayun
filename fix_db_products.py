#!/usr/bin/env python3
"""
修复商品表字段
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
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
    )

def check_column_exists(table_name, column_name):
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
            result = cur.fetchone()
        conn.close()
        return result is not None
    except:
        return False

def add_column(table_name, column_def, description):
    column_name = column_def.split()[0]
    if check_column_exists(table_name, column_name):
        print(f"  ⚠ {description} - 字段已存在")
        return True
    
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
        conn.commit()
        conn.close()
        print(f"  ✓ {description}")
        return True
    except Exception as e:
        print(f"  ✗ {description} - {e}")
        return False

print("=" * 60)
print("修复商品表和门店表")
print("=" * 60)

# 修复 products 表
print("\n[1/2] 修复 business_products 表...")
add_column("business_products", "shop_id INT DEFAULT NULL COMMENT '门店ID'", "添加 shop_id 字段")
add_column("business_products", "status VARCHAR(20) DEFAULT 'active' COMMENT '状态'", "添加 status 字段")
add_column("business_products", "sales_count INT DEFAULT 0 COMMENT '销量'", "添加 sales_count 字段")
add_column("business_products", "view_count INT DEFAULT 0 COMMENT '浏览量'", "添加 view_count 字段")
add_column("business_products", "sort_order INT DEFAULT 0 COMMENT '排序'", "添加 sort_order 字段")
add_column("business_products", "original_price DECIMAL(10,2) DEFAULT NULL COMMENT '原价'", "添加 original_price 字段")

# 修复 shops 表
print("\n[2/2] 修复 business_shops 表...")
add_column("business_shops", "shop_name VARCHAR(200) DEFAULT '' COMMENT '门店名称'", "添加 shop_name 字段")
add_column("business_shops", "address VARCHAR(500) DEFAULT '' COMMENT '地址'", "添加 address 字段")
add_column("business_shops", "phone VARCHAR(50) DEFAULT '' COMMENT '电话'", "添加 phone 字段")

print("\n" + "=" * 60)
print("修复完成")
print("=" * 60)
