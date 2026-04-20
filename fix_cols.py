#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 SQL 列名
content = content.replace('form_config, approval_config, status, sort_order',
                         'form_schema, approve_flow, is_active as status, sort_order')

# 修复代码中对 form_config 的引用
content = content.replace("item.get('form_config')", "item.get('form_schema')")
content = content.replace("item['form_config'] = json.loads(item['form_schema'])", "item['form_schema'] = json.loads(item['form_schema']) if item.get('form_schema') else {}")
content = content.replace("item['form_config'] = {}", "item['form_schema'] = {}")

content = content.replace("result.get('form_config')", "result.get('form_schema')")
content = content.replace("result['form_config'] = json.loads(result['form_schema'])", "result['form_schema'] = json.loads(result['form_schema']) if result.get('form_schema') else {}")
content = content.replace("result['form_config'] = {}", "result['form_schema'] = {}")

with open(svc_py, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已修复列名映射: form_config → form_schema, approval_config → approve_flow')
