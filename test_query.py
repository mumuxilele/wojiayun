#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)
cur = conn.cursor()
# 测试和API一样的查询
cur.execute("""SELECT * FROM business_application_types WHERE type_code=%s AND is_active=1""", ['overtime'])
row = cur.fetchone()
if row:
    print('✅ 查询到 overtime:')
    cols = [d[0] for d in cur.description]
    for col, val in zip(cols, row):
        print(f'  {col}: {val}')
else:
    print('❌ 未查到 overtime')

# 测试模糊匹配
cur.execute("""SELECT type_code, type_name, is_active FROM business_application_types WHERE type_code LIKE '%%overtime%%'""")
print('\n模糊查询结果:')
for row in cur.fetchall():
    print(f'  {row}')

conn.close()
