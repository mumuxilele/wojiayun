import pymysql
conn = pymysql.connect(host='47.98.238.209', port=3306, user='root', password='Wojiacloud$2023', database='visit_system', charset='utf8mb4')
cursor = conn.cursor()
cursor.execute('DESCRIBE business_members')
for row in cursor.fetchall():
    print(row)
cursor.close()
conn.close()
