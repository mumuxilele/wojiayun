#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

# Read the new version (with points-mall API)
new_app = '/tmp/new_app.py'
old_app = '/tmp/working_app.py'

# Extract points-mall API section from new version (lines 4176-4350)
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where to insert (before the if __name__ block)
insert_line = -1
for i, line in enumerate(lines):
    if '__name__' in line and '__main__' in line:
        insert_line = i
        break

if insert_line == -1:
    print("Could not find __name__ line")
    sys.exit(1)

# Extract points-mall API (lines 4176 to ~4350)
pm_start = 4175  # 0-indexed
pm_end = 4350

# Read the new version file
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    new_lines = f.readlines()

# Get points-mall API code
pm_code = new_lines[pm_start:pm_end]

# Read the old version (working)
with open(old_app, 'r', encoding='utf-8') as f:
    old_lines = f.readlines()

# Find __name__ in old version
old_insert = -1
for i, line in enumerate(old_lines):
    if '__name__' in line and '__main__' in line:
        old_insert = i
        break

if old_insert == -1:
    print("Could not find __name__ in old version")
    sys.exit(1)

# Insert points-mall API before __name__
new_lines = old_lines[:old_insert] + ['\n', '# ============ 积分商城 API ============\n'] + pm_code + old_lines[old_insert:]

# Write the merged file
with open(old_app, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Added points-mall API. Total lines: {len(new_lines)}")

# Verify syntax
import subprocess
result = subprocess.run(
    ['/www/wwwroot/wojiayun/venv/bin/python', '-m', 'py_compile', old_app],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("SYNTAX OK - Ready to deploy")
else:
    print(f"SYNTAX ERROR: {result.stderr.decode('utf-8', errors='replace')[:200]}")
