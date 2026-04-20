#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复所有错误的列名
fixes = [
    # SQL WHERE 子句中的 status → is_active
    ('WHERE status = 1', 'WHERE is_active = 1'),
    # SQL 表名错误
    ('FROM t_bdc_application', 'FROM business_applications'),
    # 错误的别名/列名引用
    ('item.get(\'status\')', "item.get('is_active')"),
]

for old, new in fixes:
    count = content.count(old)
    if count > 0:
        content = content.replace(old, new)
        print(f'✅ 替换 {count} 处: {old[:50]} → {new[:50]}')

with open(svc_py, 'w', encoding='utf-8') as f:
    f.write(content)

print('\n修复完成')
