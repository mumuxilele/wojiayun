#!/usr/bin/env python3
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
line539 = lines[538]  # 0-indexed
print(f'Line 539: {repr(line539)}')
print(f'Length: {len(line539)}')
