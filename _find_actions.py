import os
import re

admin_dir = '/www/wwwroot/wojiayun/business-admin/'
for f in os.listdir(admin_dir):
    if f.endswith('.html'):
        path = os.path.join(admin_dir, f)
        content = open(path, encoding='utf-8', errors='ignore').read()
        matches = re.findall(r'class=["\']actions["\'][^>]*>.*?</td>', content, re.DOTALL)
        if matches:
            print(f'=== {f} ===')
            for m in matches[:2]:
                print(repr(m[:300]))
                print()
