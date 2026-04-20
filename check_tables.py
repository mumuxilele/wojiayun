#!/usr/bin/env python3
"""
检查表结构
"""
import pymysql
import os

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

def check_table(table_name):
    print(f"\n[{table_name}] 表结构:")
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = cur.fetchall()
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']}")
        conn.close()
    except Exception as e:
        print(f"  错误: {e}")

print("=" * 60)
print("检查数据库表结构")
print("=" * 60)

check_table("business_cart")
check_table("business_coupons")
check_table("business_user_coupons")
check_table("business_products")
