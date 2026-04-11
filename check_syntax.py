#!/usr/bin/env python3
import re

file_path = r'c:\Users\kingdee\WorkBuddy\Claw\wojiayun\business-admin\app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

errors = []
for i, line in enumerate(lines, 1):
    # 检查 return jsonify 语句是否缺少闭合括号
    if 'return jsonify' in line and line.strip().endswith('}'):
        if not line.strip().endswith('})'):
            errors.append((i, line.strip()))

if errors:
    print(f"Found {len(errors)} potential syntax errors:")
    for line_num, line in errors:
        print(f"Line {line_num}: {line}")
else:
    print("No syntax errors found in return jsonify statements")
