#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

count = content.count('conn.cursor(dictionary=True)')
print(f'找到 {count} 处 conn.cursor(dictionary=True)')

content = content.replace('conn.cursor(dictionary=True)', 'conn.cursor(db.pymysql.cursors.DictCursor)')

with open(svc_py, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已替换为 db.pymysql.cursors.DictCursor')
