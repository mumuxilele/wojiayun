#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 JSON 解析 - 兼容 str 和 dict 类型
old = '''                try:
                    if result.get('form_schema'):
                        result['form_schema'] = json.loads(result['form_schema'])
                except:
                    result['form_schema'] = {}
                try:
                    if result.get('approve_flow'):
                        result['approve_flow'] = json.loads(result['approve_flow'])
                except:
                    result['approve_flow'] = {}'''

new = '''                if result.get('form_schema') and isinstance(result['form_schema'], str):
                    try:
                        result['form_schema'] = json.loads(result['form_schema'])
                    except:
                        result['form_schema'] = {}
                if result.get('approve_flow') and isinstance(result['approve_flow'], str):
                    try:
                        result['approve_flow'] = json.loads(result['approve_flow'])
                    except:
                        result['approve_flow'] = {}'''

# 也修复 get_application_types 中的同样问题
old2 = '''                try:
                    if item.get('form_schema'):
                        item['form_schema'] = json.loads(item['form_schema'])
                except:
                    item['form_schema'] = {}
                try:
                    if item.get('approve_flow'):
                        item['approve_flow'] = json.loads(item['approve_flow'])
                except:
                    item['approve_flow'] = {}'''

new2 = '''                if item.get('form_schema') and isinstance(item['form_schema'], str):
                    try:
                        item['form_schema'] = json.loads(item['form_schema'])
                    except:
                        item['form_schema'] = {}
                if item.get('approve_flow') and isinstance(item['approve_flow'], str):
                    try:
                        item['approve_flow'] = json.loads(item['approve_flow'])
                    except:
                        item['approve_flow'] = {}'''

c1 = content.count(old)
c2 = content.count(old2)
content = content.replace(old, new)
content = content.replace(old2, new2)

with open(svc_py, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Fixed result block: {c1}, item block: {c2}')
