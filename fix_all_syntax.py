#!/usr/bin/env python3
import re

file_path = r'c:\Users\kingdee\WorkBuddy\Claw\wojiayun\business-admin\app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复所有 return jsonify({'success': False, 'msg': '...'} 缺少闭合括号的情况
# 匹配模式：return jsonify({...} 后面没有 ) 的情况
pattern = r"(return jsonify\(\{[^}]+\}')(\s|$)"
replacement = r"\1)\2"
content = re.sub(pattern, replacement, content)

# 保存修复后的文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all missing closing parentheses in return jsonify statements")

# 验证语法
try:
    compile(content, file_path, 'exec')
    print("Syntax check passed!")
except SyntaxError as e:
    print(f"Syntax error still exists: {e}")
    print(f"Line {e.lineno}: {e.text}")
