#!/usr/bin/env python3
"""验证 t_bdc_application 表"""
import pymysql

conn = pymysql.connect(
    host='47.98.238.209',
    user='root',
    password='Wojiacloud$2023',
    database='visit_system'
)
cursor = conn.cursor()
cursor.execute('DESCRIBE t_bdc_application')
for row in cursor.fetchall():
    print(row)
cursor.close()
conn.close()