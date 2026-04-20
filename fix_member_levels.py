#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)

columns = [
    ("business_member_levels", "level_name", "VARCHAR(100) DEFAULT ''"),
]

with conn.cursor() as cur:
    for table, col, dtype in columns:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {dtype}")
            print(f'ADDED: {table}.{col}')
        except pymysql.err.OperationalError as e:
            if 'Duplicate column' in str(e):
                print(f'EXISTS: {table}.{col}')
            else:
                print(f'ERR: {e}')
conn.commit()
conn.close()
print('Done')
