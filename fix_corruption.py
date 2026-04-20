#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

# Read the broken app.py from git
import subprocess
result = subprocess.run(
    ['git', 'show', '2d96d1e:business-admin/app.py'],
    capture_output=True,
    cwd='/www/wwwroot/wojiayun'
)
if result.returncode != 0:
    print("Git failed:", result.stderr)
    exit(1)

content = result.stdout.decode('utf-8', errors='replace')

# Find the corrupted line and fix it
# The corruption pattern: f"RFM概览查询失败: {e}" becomes f"RFMM-fM-...{e}"
# Fix by replacing the corrupted f-string with correct one

# Pattern to find corrupted RFM logging.warning line
corrupt_pattern = r'logging\.warning\(f"RFM[^"]*\{e\}"\)'
correct_replacement = 'logging.warning("RFM概览查询失败: %s", str(e))'

new_content = re.sub(corrupt_pattern, correct_replacement, content)

if new_content == content:
    print("No corruption found or already fixed")
else:
    print("Fixed corruption")

# Write the fixed content
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Written fixed app.py")

# Verify syntax
try:
    compile(new_content, 'app.py', 'exec')
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
