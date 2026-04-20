#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'WHERE type_code = %s AND status = 1' in line:
        lines[i] = line.replace('WHERE type_code = %s AND status = 1', 'WHERE type_code = %s AND is_active = 1')
        print(f'✅ Line {i+1}: fixed')
    elif 'WHERE ec_id = %s AND status = 1' in line:
        lines[i] = line.replace('WHERE ec_id = %s AND status = 1', 'WHERE ec_id = %s AND is_active = 1')
        print(f'✅ Line {i+1}: fixed')

with open(svc_py, 'w') as f:
    f.writelines(lines)

print('Done')
