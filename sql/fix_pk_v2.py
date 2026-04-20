#!/usr/bin/env python3
"""修复主键为fid - V2（处理AUTO_INCREMENT）"""
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

print("修复主键为fid - V2")
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
        
        # 检查当前主键
        cursor.execute("""
            SELECT kcu.COLUMN_NAME
            FROM information_schema.TABLE_CONSTRAINTS tc
            JOIN information_schema.KEY_COLUMN_USAGE kcu 
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
            WHERE tc.TABLE_SCHEMA = DATABASE()
            AND tc.TABLE_NAME = %s
            AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        """, (table,))
        
        pk_col = cursor.fetchone()
        if pk_col:
            pk_col = pk_col[0]
            if pk_col == 'fid':
                print(f"  ✅ 主键已是fid，跳过")
                continue
            print(f"  📝 当前主键是: {pk_col}")
        
        # 获取表的外键
        cursor.execute("""
            SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """, (table,))
        fks = cursor.fetchall()
        
        # 删除外键
        for fk in fks:
            fk_name = fk[0]
            print(f"  📝 删除外键: {fk_name}")
            try:
                cursor.execute(f"ALTER TABLE `{table}` DROP FOREIGN KEY `{fk_name}`")
            except Exception as e:
                print(f"    ⚠️ {e}")
        
        # 检查id是否自增
        cursor.execute("""
            SELECT EXTRA FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND COLUMN_NAME = 'id'
        """, (table,))
        extra = cursor.fetchone()
        if extra and 'auto_increment' in extra[0].lower():
            print(f"  📝 修改id字段，去掉AUTO_INCREMENT...")
            cursor.execute(f"ALTER TABLE `{table}` MODIFY `id` INT NOT NULL")
        
        # 删除主键
        print(f"  📝 删除原主键...")
        cursor.execute(f"ALTER TABLE `{table}` DROP PRIMARY KEY")
        
        # 添加fid为主键
        print(f"  📝 添加fid为主键...")
        cursor.execute(f"ALTER TABLE `{table}` ADD PRIMARY KEY (`fid`)")
        
        # 添加id唯一索引（如果不存在）
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = %s
            AND INDEX_NAME = 'uk_id'
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
