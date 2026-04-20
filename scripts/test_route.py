#!/usr/bin/env python3
"""测试 Flask 路由"""
import sys
import os
sys.path.insert(0, '/www/wwwroot/wojiayun/business-staffH5')
sys.path.insert(0, '/www/wwwroot/wojiayun')

os.environ['DB_HOST'] = '47.98.238.209'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'Wojiacloud$2023'
os.environ['DB_NAME'] = 'visit_system'

import app
print("\n已注册的路由:")
for rule in app.app.url_map.iter_rules():
    print(f"  {rule.endpoint:30s} {rule.rule}")
