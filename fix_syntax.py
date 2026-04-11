#!/usr/bin/env python3
import sys

file_path = '/www/wwwroot/wojiayun/business-admin/app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复语法错误
content = content.replace("'overview': {}})", "'overview': {}}})")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed syntax error in app.py")
