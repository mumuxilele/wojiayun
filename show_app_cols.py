#!/usr/bin/env python3
import pymysql
conn = pymysql.connect(host='localhost', port=3306, user='root', password='Wojiacloud$2023', database='visit_system', charset='utf8mb4')
cur = conn.cursor()
cur.execute('SHOW COLUMNS FROM business_applications')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')
conn.close()
