#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if 'WHERE' in line and ('status' in line.lower() or 'form_config' in line.lower()):
        print(f'{i}: {line.rstrip()}')
