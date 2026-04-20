#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Read the file
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix line 538 (index 537)
for i in range(len(lines)):
    if i == 537 and 'RFM' in lines[i]:
        # Replace the corrupted line with the correct one
        lines[i] = '        logging.warning("RFM概览查询失败: %s", str(e))\n'
        print(f"Fixed line {i+1}")

# Write back
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done")
