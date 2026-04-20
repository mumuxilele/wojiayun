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

if 'app' in sys.modules:
    del sys.modules['app']

import app

# 使用 Flask test client 测试
client = app.app.test_client()

# 测试 /business-common/list-style.css
print("Testing /business-common/list-style.css:")
response = client.get('/business-common/list-style.css')
print(f"  Status: {response.status_code}")
print(f"  Content-Type: {response.content_type}")
if response.status_code == 200:
    print(f"  Content length: {len(response.data)}")
else:
    print(f"  Response: {response.get_json()}")
