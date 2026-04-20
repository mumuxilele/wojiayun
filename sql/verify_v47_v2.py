#!/usr/bin/env python3
"""验证V47.0迁移结果 - V2"""
import pymysql

DB_CONFIG = {
    'host': '47.98.238.209',
    'port': 3306,
    'user': 'root',
    'password': 'Wojiacloud$2023',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

TABLES = [
    'business_applications', 'business_orders', 'business_reviews', 
    'business_members', 'business_feedback', 'business_products',
    'business_coupons', 'business_user_coupons', 'business_approve_nodes',
    'business_application_attachments', 'business_application_reminds',
    'visit_records', 'chat_messages', 'chat_sessions', 'auth_accounts'
]

conn = pymysql.connect(**DB_CONFIG)
cursor = conn.cursor()

print("V47.0 迁移验证结果 V2")
print("=" * 60)

success = 0
for table in TABLES:
    cursor.execute("""
        SELECT kcu.COLUMN_NAME, kcu.CONSTRAINT_NAME 
        FROM information_schema.TABLE_CONSTRAINTS tc
        JOIN information_schema.KEY_COLUMN_USAGE kcu 
        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE tc.TABLE_SCHEMA = DATABASE()
        AND tc.TABLE_NAME = %s
        AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
    """, (table,))
    
    pk_columns = cursor.fetchall()
    
    if pk_columns:
        pk_col = pk_columns[0][0]
        if pk_col == 'fid':
            print(f"✅ {table}: 主键是 fid")
            success += 1
        else:
            print(f"⚠️  {table}: 主键是 {pk_col}")
    else:
        print(f"❌ {table}: 无主键")

print("=" * 60)
print(f"验证完成: {success}/{len(TABLES)} 个表主键正确")

cursor.close()
conn.close()
