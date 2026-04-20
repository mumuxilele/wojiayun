#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/www/wwwroot/wojiayun')
os.chdir('/www/wwwroot/wojiayun/business-userH5')

os.environ['DB_HOST'] = '47.98.238.209'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'Wojiacloud$2023'
os.environ['DB_NAME'] = 'visit_system'

from flask import Flask, jsonify
app = Flask(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db

print('db module file:', db.__file__)
print('db attrs:', [a for a in dir(db) if not a.startswith('_')])

# 直接导入 application_service
from business_common.application_service import ApplicationService
print('ApplicationService imported')

# 测试
try:
    result = ApplicationService.get_application_type('overtime')
    print('Result:', result)
except Exception as e:
    print('Exception in ApplicationService:', e)
    import traceback
    traceback.print_exc()
