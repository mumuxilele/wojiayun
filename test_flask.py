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

def mock_login(f):
    def wrapper(*args, **kwargs):
        user = {'userId': 123, 'name': 'test', 'ecId': '5c4969cb51394395b25e78d1dac2f3e0'}
        return f(user, *args, **kwargs)
    return wrapper

@app.route('/api/user/application/types/<type_code>', methods=['GET'])
@mock_login
def get_detail(user, type_code):
    from business_common.application_service import ApplicationService
    app_type = ApplicationService.get_application_type(type_code)
    if not app_type:
        return jsonify({'success': False, 'msg': '申请类型不存在'})
    return jsonify({'success': True, 'data': app_type})

with app.test_client() as c:
    r = c.get('/api/user/application/types/overtime')
    print(r.status_code, r.get_json())
