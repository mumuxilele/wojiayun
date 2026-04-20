#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)
cur = conn.cursor()
cur.execute('SELECT * FROM business_application_types WHERE type_code="overtime"')
row = cur.fetchone()
if row:
    cols = [d[0] for d in cur.description]
    for col, val in zip(cols, row):
        print(f'{col}: {val}')
else:
    print('overtime 不存在')
conn.close()
