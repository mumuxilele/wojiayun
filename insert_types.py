#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)
with conn.cursor() as cur:
    cur.execute("""INSERT IGNORE INTO business_application_types 
        (type_code, type_name, icon, category, description, require_attachment, is_active) VALUES
        ('overtime', '加班申请', '⏰', 'work', '加班申请与审批', 0, 1),
        ('leave', '请假申请', '📅', 'work', '请假申请与审批', 0, 1),
        ('repair', '报修申请', '🔧', 'service', '物业报修', 1, 1),
        ('booking', '预约申请', '📅', 'service', '场地/服务预约', 0, 1),
        ('complaint', '投诉建议', '📝', 'service', '投诉与建议', 0, 1),
        ('consult', '咨询服务', '💬', 'service', '咨询与帮助', 0, 1),
        ('other', '其他申请', '📋', 'general', '其他类型申请', 0, 1)
    """)
    conn.commit()
    
    cur.execute("SELECT type_code, type_name FROM business_application_types")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")
conn.close()
print('Done')
