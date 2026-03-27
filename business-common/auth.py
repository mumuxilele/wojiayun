"""
用户认证模块
"""
import urllib.request
import urllib.parse
import json
from .config import USER_SERVICE_URL

def verify_user(token, isdev='0'):
    """验证用户并获取用户信息"""
    if not token:
        return None
    
    try:
        url = f"{USER_SERVICE_URL}?access_token={urllib.parse.quote(token)}&isdev={isdev}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('success') and data.get('data'):
                u = data['data']
                return {
                    'user_id': u.get('userId') or u.get('id'),
                    'user_name': u.get('userName') or u.get('empName'),
                    'phone': u.get('userPhone') or u.get('empPhone'),
                    'emp_id': u.get('empId'),
                    'staff_id': u.get('staffId'),
                    'ec_id': u.get('ecId'),
                    'project_id': u.get('projectId'),
                    'is_staff': bool(u.get('empId') or u.get('staffId')),
                    'raw_data': u
                }
    except Exception as e:
        print(f'User verify error: {e}')
    return None

def verify_staff(token, isdev='0'):
    """验证员工身份"""
    user = verify_user(token, isdev)
    if user and user.get('is_staff'):
        return user
    return None
