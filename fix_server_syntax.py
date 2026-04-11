#!/usr/bin/env python3
import re

file_path = '/www/wwwroot/wojiayun/business-admin/app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []
for i, line in enumerate(lines):
    # 修复 return jsonify({'success': False, 'msg': '...'} 缺少闭合括号的情况
    if 'return jsonify' in line and line.strip().endswith('}'):
        if not line.rstrip().endswith('})'):
            line = line.rstrip() + ')\n'
    fixed_lines.append(line)

content = ''.join(fixed_lines)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all syntax errors")

# 验证语法
try:
    compile(content, file_path, 'exec')
    print("Syntax check passed!")
except SyntaxError as e:
    print(f"Syntax error still exists at line {e.lineno}: {e.msg}")
