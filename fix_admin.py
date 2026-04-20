#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import ast

filename = '/www/wwwroot/wojiayun/business-admin/app.py'

with open(filename, 'rb') as f:
    raw = f.read()

# Check for BOM
if raw.startswith(b'\xef\xbb\xbf'):
    print("Found UTF-8 BOM, removing...")
    raw = raw[3:]
    with open(filename, 'wb') as f:
        f.write(raw)
    print("BOM removed")
else:
    print("No BOM found")

# Try parsing
try:
    with open(filename, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    ast.parse(content)
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    lines = content.split('\n')
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+2)):
        marker = ">>> " if i == e.lineno-1 else "    "
        print(f"{marker}{i+1}: {lines[i]}")
