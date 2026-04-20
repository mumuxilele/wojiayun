#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import re

app_file = '/www/wwwroot/wojiayun/business-admin/app.py'

with open(app_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all problematic f-string lines with logging.warning
patterns = [
    ('logging.warning(f"RFM概览查询失败: {e}")', 'logging.warning("RFM概览查询失败: %s", str(e))'),
    ('logging.warning(f"审计日志记录失败: {e}")', 'logging.warning("审计日志记录失败: %s", str(e))'),
    ('logging.warning(f"运营看板概览查询失败: {e}")', 'logging.warning("运营看板概览查询失败: %s", str(e))'),
    ('logging.warning(f"运营趋势查询失败: {e}")', 'logging.warning("运营趋势查询失败: %s", str(e))'),
]

for old, new in patterns:
    if old in content:
        content = content.replace(old, new)
        print(f"Fixed: {old[:50]}...")
    else:
        print(f"Not found: {old[:50]}...")

# Also try regex for any remaining f-strings in logging.warning
import re
content = re.sub(
    r'logging\.warning\(f"([^"]*):\s*\{([^}]+)\}"\)',
    lambda m: f'logging.warning("{m.group(1)}: %s", {m.group(2)})',
    content
)

with open(app_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
