#!/usr/bin/env python3
"""修复V47.0主键问题"""
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

print("V47.0 修复主键")
print("=" * 60)

for table in TABLES:
    try:
        print(f"\n📋 处理表: {table}")
        
        # 检查表是否存在
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = %s
        """, (table,))
        if cursor.fetchone()[0] == 0:
            print(f"  ⚠️ 表不存在，跳过")
            continue
        
        # 检查fid是否已是主键
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS tc
            JOIN information_schema.KEY_COLUMN_USAGE kcu 
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE tc.TABLE_SCHEMA = DATABASE()
            AND tc.TABLE_NAME = %s
            AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
            AND kcu.COLUMN_NAME = 'fid'
        """, (table,))
        
        if cursor.fetchone()[0] > 0:
            print(f"  ✅ 已是主键，跳过")
            continue
        
        # 获取外键约束并删除
        cursor.execute("""
            SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """, (table,))
        fks = cursor.fetchall()
        for fk in fks:
            fk_name = fk[0]
            print(f"  📝 删除外键: {fk_name}")
            cursor.execute(f"ALTER TABLE `{table}` DROP FOREIGN KEY `{fk_name}`")
        
        # 删除原主键
        print(f"  📝 删除原主键...")
        cursor.execute(f"ALTER TABLE `{table}` DROP PRIMARY KEY")
        
        # 添加fid为主键
        print(f"  📝 添加fid为主键...")
        cursor.execute(f"ALTER TABLE `{table}` ADD PRIMARY KEY (`fid`)")
        
        # 检查是否有id唯一索引，没有则添加
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND COLUMN_NAME = 'id'
            AND NON_UNIQUE = 0
        """, (table,))
        if cursor.fetchone()[0] == 0:
            print(f"  📝 添加id唯一索引...")
            cursor.execute(f"ALTER TABLE `{table}` ADD UNIQUE INDEX `uk_id` (`id`)")
        
        conn.commit()
        print(f"  ✅ 修复成功")
        
    except Exception as e:
        conn.rollback()
        print(f"  ❌ 修复失败: {e}")

cursor.close()
conn.close()
print("\n" + "=" * 60)
print("修复完成")
