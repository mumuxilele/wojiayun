#!/usr/bin/env python3
import subprocess

# Get new version
result = subprocess.run(
    ['git', 'show', '2d96d1e:business-admin/app.py'],
    capture_output=True, cwd='/www/wwwroot/wojiayun'
)
new_lines = result.stdout.decode('utf-8').split('\n')

# Extract overview (lines 273-300) and trend (lines 300-350)
overview_start = 272  # 0-indexed
overview_end = 300
trend_start = 300
trend_end = 350

overview_code = '\n'.join(new_lines[overview_start:overview_end])
trend_code = '\n'.join(new_lines[trend_start:trend_end])

print(f"Overview: {len(overview_code)} chars")
print(f"Trend: {len(trend_code)} chars")

# Read old version
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    old_content = f.read()

# Check if already exists
if 'statistics/overview' in old_content:
    print("Overview API already exists")
else:
    # Insert before 'if __name__'
    if '__name__' in old_content:
        idx = old_content.find('if __name__')
        new_content = old_content[:idx] + '\n' + overview_code + '\n' + trend_code + '\n' + old_content[idx:]
        with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Added overview and trend APIs")
    else:
        print("Could not find insertion point")
