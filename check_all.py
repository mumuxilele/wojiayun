#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)
cur = conn.cursor()

# 1. 检查表是否存在
cur.execute("SHOW TABLES LIKE 'business_application_types'")
if cur.fetchone():
    print("✅ business_application_types 表存在")
else:
    print("❌ business_application_types 表不存在!")
    
    # 看看有哪些表
    cur.execute("SHOW TABLES LIKE '%application%'")
    tables = cur.fetchall()
    print("相关的表:", [t[0] for t in tables])
    conn.close()
    exit()

# 2. 检查overtime记录
cur.execute("SELECT COUNT(*) FROM business_application_types WHERE type_code='overtime'")
count = cur.fetchone()[0]
print(f"overtime 记录数: {count}")

# 3. 直接模拟API查询
cur.execute("SELECT * FROM business_application_types WHERE type_code=%s AND is_active=1", ['overtime'])
row = cur.fetchone()
if row:
    print("✅ 查到了 overtime")
    cols = [d[0] for d in cur.description]
    for c, v in zip(cols, row):
        print(f"  {c}: {v}")
else:
    print("❌ 未查到 overtime")
    # 检查是不是ec_id过滤问题
    cur.execute("SELECT type_code, ec_id, project_id FROM business_application_types LIMIT 10")
    print("\n前10条记录:")
    for r in cur.fetchall():
        print(f"  {r}")

conn.close()
