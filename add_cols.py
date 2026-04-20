#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)

# 需要添加的列 (不带 IF NOT EXISTS)
columns_to_add = [
    ("business_members", "valid_until", "DATETIME DEFAULT NULL"),
    ("business_members", "status", "VARCHAR(20) DEFAULT 'active'"),
    ("business_members", "level_id", "INT DEFAULT NULL"),
    ("business_members", "level_name", "VARCHAR(100) DEFAULT ''"),
    ("business_members", "points", "INT DEFAULT 0"),
    ("business_members", "total_spend", "DECIMAL(12,2) DEFAULT 0"),
    ("business_members", "expire_at", "DATETIME DEFAULT NULL"),
    ("business_member_levels", "is_default", "TINYINT DEFAULT 0"),
]

with conn.cursor() as cur:
    for table, col, dtype in columns_to_add:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {dtype}")
            print(f'ADDED: {table}.{col}')
        except pymysql.err.OperationalError as e:
            if 'Duplicate column' in str(e):
                print(f'EXISTS: {table}.{col}')
            else:
                print(f'ERR {table}.{col}: {e}')
conn.commit()
conn.close()
print('Done')
