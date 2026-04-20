#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ast
import sys

try:
    with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
        code = f.read()
    ast.parse(code)
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    print(f"Line: {e.text}")
    sys.exit(1)
