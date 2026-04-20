#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)

with conn.cursor() as cur:
    # 添加缺失的列
    cols = [
        ('level_code', 'VARCHAR(50) DEFAULT NULL'),
        ('discount_rate', 'DECIMAL(5,2) DEFAULT 1.00'),
        ('points_rate', 'DECIMAL(5,2) DEFAULT 1.00'),
        ('privileges', 'TEXT'),
    ]
    for col, dtype in cols:
        try:
            cur.execute(f"ALTER TABLE business_member_levels ADD COLUMN {col} {dtype}")
            print(f'ADDED: {col}')
        except pymysql.err.OperationalError as e:
            if 'Duplicate column' in str(e):
                print(f'EXISTS: {col}')
            else:
                print(f'ERR: {e}')
    
    # 检查是否有 level_code 数据，如果没有插入默认会员等级
    cur.execute("SELECT COUNT(*) FROM business_member_levels")
    if cur.fetchone()[0] == 0:
        cur.execute('''INSERT INTO business_member_levels 
            (name, level_name, level_code, level, min_points, discount_rate, points_rate, is_active, is_default)
            VALUES 
            ('普通会员', '普通会员', 'normal', 1, 0, 1.00, 1.00, 1, 1),
            ('银卡会员', '银卡会员', 'silver', 2, 1000, 0.95, 1.10, 1, 0),
            ('金卡会员', '金卡会员', 'gold', 3, 5000, 0.90, 1.20, 1, 0),
            ('钻石会员', '钻石会员', 'diamond', 4, 10000, 0.85, 1.50, 1, 0)''')
        print('INSERTED default levels')
    
conn.commit()
conn.close()
print('Done')
