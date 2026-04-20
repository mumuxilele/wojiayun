#!/usr/bin/env python3
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 539 (0-indexed: line 538)
if "overview: {}))" in lines[538]:
    lines[538] = lines[538].replace("overview: {}))", "overview: {}}))")
    print("Fixed line 539")
    with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Written")
else:
    print("Pattern not found, checking...")
    print(f"Line 539: {repr(lines[538])}")
