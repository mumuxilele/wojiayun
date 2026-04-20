#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)

# 需要添加的列
alter_statements = [
    "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS valid_until DATETIME DEFAULT NULL",
    "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'",
    "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS level_id INT DEFAULT NULL",
    "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS level_name VARCHAR(100) DEFAULT ''",
    "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS points INT DEFAULT 0",
    "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS total_spend DECIMAL(12,2) DEFAULT 0",
    "ALTER TABLE business_members ADD COLUMN IF NOT EXISTS expire_at DATETIME DEFAULT NULL",
    "ALTER TABLE business_member_levels ADD COLUMN IF NOT EXISTS is_default TINYINT DEFAULT 0",
]

with conn.cursor() as cur:
    for sql in alter_statements:
        try:
            cur.execute(sql)
            print(f'OK: {sql[:60]}...')
        except Exception as e:
            if 'Duplicate column' in str(e):
                print(f'SKIP (exists): {sql[:60]}...')
            else:
                print(f'ERR: {e}')
conn.commit()
conn.close()
print('Done')
