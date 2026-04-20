#!/usr/bin/env python3
import pymysql
conn = pymysql.connect(
    host='47.98.238.209',
    user='root',
    password='Wojiacloud$2023',
    database='visit_system'
)
cursor = conn.cursor()
cursor.execute("SHOW TABLES")
tables = cursor.fetchall()
for t in tables:
    print(t[0])
cursor.close()
conn.close()
