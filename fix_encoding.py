#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import re

app_file = '/www/wwwroot/wojiayun/business-admin/app.py'

with open(app_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the problematic line with f-string
old_line = "logging.warning(f\"RFM概览查询失败: {e}\")"
new_line = 'logging.warning("RFM概览查询失败: %s", str(e))'

if old_line in content:
    content = content.replace(old_line, new_line)
    print(f"Fixed: {old_line}")
else:
    print("Line not found, checking for pattern...")
    # Try to find lines with logging.warning and f"
    matches = re.findall(r'logging\.warning\(f"[^"]*"\)', content)
    for m in matches[:3]:
        print(f"Found: {m}")

with open(app_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
