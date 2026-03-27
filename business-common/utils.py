"""
工具函数模块
"""
from datetime import datetime
import hashlib
import random
import string

def success(data=None, msg='success'):
    """成功响应"""
    return {'success': True, 'msg': msg, 'data': data}

def error(msg='error', code=400):
    """错误响应"""
    return {'success': False, 'msg': msg}, code

def generate_no(prefix=''):
    """生成单号"""
    now = datetime.now()
    date_str = now.strftime('%Y%m%d%H%M%S')
    rand_str = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}{date_str}{rand_str}"

def get_client_ip():
    """获取客户端IP"""
    from flask import request
    return request.remote_addr or '127.0.0.1'
