#!/usr/bin/env python3
import sys, os, traceback
sys.path.insert(0, '/www/wwwroot/wojiayun')
os.chdir('/www/wwwroot/wojiayun/business-userH5')

os.environ['DB_HOST'] = '47.98.238.209'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'Wojiacloud$2023'
os.environ['DB_NAME'] = 'visit_system'

# 模拟 get_application_type 的内部调用
from business_common import db

sql = """SELECT * FROM business_application_types WHERE type_code=%s AND is_active=1"""
params = ['overtime']

print('尝试执行 SQL...')
try:
    result = db.get_one(sql, params)
    print(f'✅ db.get_one 成功: {result}')
except Exception as e:
    print(f'❌ db.get_one 失败: {e}')
    traceback.print_exc()

# 尝试直接调用
try:
    conn = db.get_db()
    print(f'✅ db.get_db 成功: {conn}')
except Exception as e:
    print(f'❌ db.get_db 失败: {e}')
    traceback.print_exc()
