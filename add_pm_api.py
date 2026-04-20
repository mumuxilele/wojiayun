#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Read the base app (working version)
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if points-mall API already exists
if 'points-mall' in content:
    print("points-mall API already exists")
    exit(0)

# Read the new version to extract points-mall API
with open('/tmp/new_admin_app.py', 'r', encoding='utf-8') as f:
    new_lines = f.readlines()

# Find the points-mall API section (around line 4176)
pm_lines = []
in_pm_section = False
brace_count = 0

for i, line in enumerate(new_lines):
    if 'points-mall' in line and '@app.route' in line:
        in_pm_section = True
    
    if in_pm_section:
        pm_lines.append(line)
        brace_count += line.count('{') - line.count('}')
        if brace_count == 0 and 'def ' in line:
            # Found the next function, stop
            break

# Find where to insert (before if __name__)
insert_pos = content.find("if __name__")
if insert_pos == -1:
    print("Could not find __name__ block")
    exit(1)

# Add the API
new_content = content[:insert_pos] + '\n# ============ 积分商城 API ============\n' + ''.join(pm_lines) + '\n' + content[insert_pos:]

# Write
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Added points-mall API")
