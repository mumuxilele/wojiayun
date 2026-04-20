#!/usr/bin/env python3
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines[536:542], start=537):
    preview = repr(line[:80])
    print(f'{i}: {preview}')
