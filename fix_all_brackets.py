#!/usr/bin/env python3
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all missing closing braces in jsonify returns
# Pattern: jsonify({'...': '...'}( -> jsonify({'...': '...'})
content = content.replace(
    "return jsonify({'success': False, 'msg': '单次操作不超过50个'}(", 
    "return jsonify({'success': False, 'msg': '单次操作不超过50个'})"
)

# Find and fix all similar patterns
import re
pattern = r"return jsonify\(\{[^)]+\}\("
matches = list(re.finditer(pattern, content))
if matches:
    print(f"Found {len(matches)} potential issues")
    for m in matches:
        print(f"Match at position {m.start()}: {content[m.start():m.start()+60]}...")
else:
    print("No more simple patterns found")

with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Written")
