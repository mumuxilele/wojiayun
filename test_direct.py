#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/www/wwwroot/wojiayun')
os.chdir('/www/wwwroot/wojiayun/business-userH5')

# 设置环境变量
os.environ['DB_HOST'] = '47.98.238.209'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'Wojiacloud$2023'
os.environ['DB_NAME'] = 'visit_system'

# 直接导入测试
from business_common.application_service import ApplicationService

result = ApplicationService.get_application_type('overtime')
print(f'Reuslt: {result}')
if result:
    print('✅ 查询成功')
    print('type_name:', result.get('type_name'))
else:
    print('❌ 查询失败，返回 None')
