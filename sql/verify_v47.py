#!/usr/bin/env python3
"""验证V47.0迁移结果"""
import pymysql

DB_CONFIG = {
    'host': '47.98.238.209',
    'port': 3306,
    'user': 'root',
    'password': 'Wojiacloud$2023',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

TABLES = ['business_orders', 'business_applications', 'business_reviews', 'visit_records']

conn = pymysql.connect(**DB_CONFIG)
cursor = conn.cursor()

print("V47.0 迁移验证结果")
print("=" * 60)

for table in TABLES:
    print(f"\n📋 表: {table}")
    cursor.execute(f"DESCRIBE `{table}`")
    columns = cursor.fetchall()
    
    has_fid = False
    fid_is_pk = False
    
    for col in columns:
        col_name = col[0]
        col_type = col[1]
        col_key = col[3]
        
        if col_name == 'fid':
            has_fid = True
            print(f"  ✅ fid字段存在，类型: {col_type}")
            if col_key == 'PRI':
                fid_is_pk = True
                print(f"  ✅ fid是主键")
            else:
                print(f"  ⚠️ fid不是主键")
    
    if not has_fid:
        print(f"  ❌ fid字段不存在")

cursor.close()
conn.close()
print("\n" + "=" * 60)
print("验证完成")
