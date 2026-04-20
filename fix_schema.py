#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 form_config → form_schema 的遗留引用
fixes = [
    ("result.get('form_config')", "result.get('form_schema')"),
    ("result['form_config']", "result['form_schema']"),
    ("item.get('form_config')", "item.get('form_schema')"),
    ("item['form_config']", "item['form_schema']"),
]
for old, new in fixes:
    c = content.count(old)
    if c > 0:
        content = content.replace(old, new)
        print(f'✅ {c}x: {old} → {new}')

with open(svc_py, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
