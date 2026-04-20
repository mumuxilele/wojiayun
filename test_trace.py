#!/usr/bin/env python3
import sys, os, traceback
sys.path.insert(0, '/www/wwwroot/wojiayun')
os.chdir('/www/wwwroot/wojiayun/business-userH5')

os.environ['DB_HOST'] = '47.98.238.209'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'Wojiacloud$2023'
os.environ['DB_NAME'] = 'visit_system'

try:
    from business_common.application_service import ApplicationService
    result = ApplicationService.get_application_type('overtime')
    print(f'Reuslt: {result}')
    if result:
        print('✅ SUCCESS')
    else:
        print('❌ Failed: result is None')
except Exception as e:
    print(f'❌ Exception: {e}')
    traceback.print_exc()
