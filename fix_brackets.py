#!/usr/bin/env python3
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the problematic line and fix it
old = "return jsonify({'success': True, 'data': {'stats': [], 'total': 0, 'overview': {}})"
new = "return jsonify({'success': True, 'data': {'stats': [], 'total': 0, 'overview': {}}})"

if old in content:
    content = content.replace(old, new)
    with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed")
else:
    print("Pattern not found")
    # Find the line
    for i, line in enumerate(content.split('\n')[535:545], start=536):
        if 'overview' in line:
            print(f"Line {i}: {repr(line)}")
