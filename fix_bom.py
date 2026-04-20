#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

# Read the app.py file
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'rb') as f:
    content = f.read()

# Check for BOM
if content.startswith(b'\xef\xbb\xbf'):
    print("Found BOM, removing...")
    content = content[3:]

# Check encoding issues
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'wb') as f:
    f.write(content)

print("File saved without BOM")

# Now verify with Python
import subprocess
result = subprocess.run(
    ['/www/wwwroot/wojiayun/venv/bin/python', '-c', 
     'import ast; ast.parse(open("/www/wwwroot/wojiayun/business-admin/app.py").read())'],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("SYNTAX OK")
else:
    print(f"SYNTAX ERROR: {result.stderr}")
