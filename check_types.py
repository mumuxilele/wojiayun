#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)
cur = conn.cursor()
cur.execute('SELECT type_code, type_name, form_schema FROM business_application_types')
print('=== 申请类型列表 ===')
for row in cur.fetchall():
    schema = row[2][:40] + '...' if row[2] and len(row[2]) > 40 else (row[2] or 'NULL')
    print(f'{row[0]:20s} | {row[1]:12s} | schema={schema}')

# 检查overtime是否存在
cur.execute("SELECT COUNT(*) FROM business_application_types WHERE type_code='overtime'")
if cur.fetchone()[0] == 0:
    print('\n>>> overtime 不存在，插入...')
    cur.execute("""INSERT INTO business_application_types 
        (type_code, type_name, icon, category, description, require_attachment, max_attachment, is_active, sort_order) 
        VALUES ('overtime', '加班申请', '⏰', 'work', '加班申请与审批', 0, 9, 1, 10)""")
    conn.commit()
    print('>>> overtime 已插入')
else:
    print('\n>>> overtime 已存在')

conn.close()
