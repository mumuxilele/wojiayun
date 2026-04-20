#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/www/wwwroot/wojiayun')
sys.path.insert(0, '/www/wwwroot/wojiayun/business-staffH5')

os.environ['DB_HOST'] = '47.98.238.209'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'Wojiacloud$2023'
os.environ['DB_NAME'] = 'visit_system'

# 清除缓存
if 'app' in sys.modules:
    del sys.modules['app']

import app

print("Routes containing 'business':")
for r in app.app.url_map.iter_rules():
    if 'business' in r.rule:
        print(f"  {r.endpoint}: {r.rule}")

print("\nAll routes:")
for r in app.app.url_map.iter_rules():
    print(f"  {r.endpoint}: {r.rule}")
