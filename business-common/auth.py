"""
用户认证模块
"""
import urllib.request
import urllib.parse
import json
from .config import USER_SERVICE_URL, USER_SERVICE_URL_CLOUD, STAFF_SERVICE_URL_CLOUD

def verify_user(token, isdev='0', use_cloud=False):
    """验证用户并获取用户信息"""
    if not token:
        return None
    
    # 选择服务URL
    if use_cloud:
        base_url = USER_SERVICE_URL_CLOUD
    else:
        base_url = USER_SERVICE_URL
    
    # 尝试多个服务地址
    urls_to_try = [base_url]
    if base_url != USER_SERVICE_URL:
        urls_to_try.append(USER_SERVICE_URL)  # 回退到本地
    
    for url_base in urls_to_try:
        try:
            url = f"{url_base}?access_token={urllib.parse.quote(token)}&isdev={isdev}"
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=10) as resp:
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
            print(f'Verify error for {url_base}: {e}')
            continue
    return None

def verify_staff(token, isdev='0'):
    """验证员工身份 - 使用员工端云端服务"""
    if not token:
        return None
    
    # 员工端优先使用云端服务
    urls_to_try = [
        STAFF_SERVICE_URL_CLOUD,
        USER_SERVICE_URL_CLOUD,
        USER_SERVICE_URL
    ]
    
    for url_base in urls_to_try:
        try:
            url = f"{url_base}?access_token={urllib.parse.quote(token)}&isdev={isdev}"
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('success') and data.get('data'):
                    u = data['data']
                    user = {
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
                    # 员工必须有员工ID
                    if user.get('is_staff') or u.get('empName'):
                        return user
        except Exception as e:
            print(f'Staff verify error for {url_base}: {e}')
            continue
    return None
