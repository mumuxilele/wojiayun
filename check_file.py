#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ast
import sys

filename = '/www/wwwroot/wojiayun/business-admin/app.py'

with open(filename, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Try to parse
try:
    ast.parse(content)
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"Error at line {e.lineno}: {e.msg}")
    # Show context
    lines = content.split('\n')
    start = max(0, e.lineno - 3)
    end = min(len(lines), e.lineno + 2)
    for i in range(start, end):
        marker = ">>> " if i == e.lineno - 1 else "    "
        print(f"{marker}{i+1}: {lines[i]}")
