#!/usr/bin/env python3
import re

svc_py = '/www/wwwroot/wojiayun/business-common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        t = db.get_one(
            """SELECT * FROM business_application_types WHERE type_code=%s AND is_active=1""",
            [type_code]
        )'''

new = '''        import logging
        logging.info(f"[DEBUG application_service] get_application_type called with type_code={type_code}")
        t = db.get_one(
            """SELECT * FROM business_application_types WHERE type_code=%s AND is_active=1""",
            [type_code]
        )
        logging.info(f"[DEBUG application_service] get_application_type({type_code}) result: {t}")'''

if old in content:
    content = content.replace(old, new)
    with open(svc_py, 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ application_service.py 调试日志已添加')
else:
    print('❌ 未找到目标代码')
    # 搜索
    idx = content.find('WHERE type_code=%s AND is_active=1')
    if idx > 0:
        print(f'找到于 {idx}')
        print(content[max(0,idx-100):idx+200])
