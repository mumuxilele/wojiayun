#!/usr/bin/env python3
"""创建 t_bdc_application 表"""
import pymysql

conn = pymysql.connect(
    host='47.98.238.209',
    user='root',
    password='Wojiacloud$2023',
    database='visit_system'
)
cursor = conn.cursor()
sql = open('/www/wwwroot/wojiayun/sql/application_table.sql').read()
for stmt in sql.split(';'):
    stmt = stmt.strip()
    if stmt and not stmt.startswith('--'):
        cursor.execute(stmt)
conn.commit()
cursor.close()
conn.close()
print('Table created successfully')
