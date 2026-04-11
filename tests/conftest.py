"""
V32.0 API集成测试配置模块
提供测试所需的fixtures和辅助函数

使用方式:
    pytest tests/test_integration_*.py -v

Fixtures:
    - base_url: 服务基础URL
    - test_user: 测试用户
    - auth_token: 认证Token
    - api_client: HTTP客户端
"""

import os
import sys
import pytest
import requests
import json
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============ 测试配置 ============

class TestConfig:
    """测试配置"""

    # 服务地址配置
    USER_H5_URL = os.environ.get('TEST_USER_H5_URL', 'http://127.0.0.1:22311')
    STAFF_H5_URL = os.environ.get('TEST_STAFF_H5_URL', 'http://127.0.0.1:22312')
    ADMIN_URL = os.environ.get('TEST_ADMIN_URL', 'http://127.0.0.1:22313')

    # 测试数据
    TEST_EC_ID = int(os.environ.get('TEST_EC_ID', '1'))
    TEST_PROJECT_ID = int(os.environ.get('TEST_PROJECT_ID', '1'))

    # 测试用户
    TEST_USER_PHONE = os.environ.get('TEST_USER_PHONE', '13800138000')
    TEST_USER_PASSWORD = os.environ.get('TEST_USER_PASSWORD', 'test123456')

    # 测试管理员
    TEST_ADMIN_PHONE = os.environ.get('TEST_ADMIN_PHONE', '13900139000')
    TEST_ADMIN_PASSWORD = os.environ.get('TEST_ADMIN_PASSWORD', 'admin123')

    # 请求超时
    TIMEOUT = 10


# ============ API客户端 ============

class ApiClient:
    """API请求客户端"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.token = None

    def set_token(self, token: str):
        """设置认证Token"""
        self.token = token
        self.session.headers.update({'Token': token})

    def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法 (GET/POST/PUT/DELETE)
            path: API路径
            **kwargs: 其他请求参数

        Returns:
            Dict: {
                "status_code": int,
                "success": bool,
                "data": dict,
                "msg": str
            }
        """
        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=kwargs.pop('timeout', TestConfig.TIMEOUT),
                **kwargs
            )

            status_code = response.status_code

            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {'raw': response.text}

            # 判断业务成功
            if status_code == 200 and data.get('success') is not False:
                return {
                    'status_code': status_code,
                    'success': True,
                    'data': data,
                    'msg': data.get('msg', '操作成功')
                }
            else:
                return {
                    'status_code': status_code,
                    'success': False,
                    'data': data,
                    'msg': data.get('msg', f'请求失败({status_code})')
                }

        except requests.exceptions.Timeout:
            return {
                'status_code': 0,
                'success': False,
                'data': None,
                'msg': '请求超时'
            }
        except requests.exceptions.ConnectionError:
            return {
                'status_code': 0,
                'success': False,
                'data': None,
                'msg': '连接失败，请确认服务是否启动'
            }
        except Exception as e:
            return {
                'status_code': 0,
                'success': False,
                'data': None,
                'msg': str(e)
            }

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """GET请求"""
        return self.request('GET', path, **kwargs)

    def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """POST请求"""
        return self.request('POST', path, **kwargs)

    def put(self, path: str, **kwargs) -> Dict[str, Any]:
        """PUT请求"""
        return self.request('PUT', path, **kwargs)

    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """DELETE请求"""
        return self.request('DELETE', path, **kwargs)


# ============ Pytest Fixtures ============

@pytest.fixture(scope='session')
def config():
    """测试配置"""
    return TestConfig()


@pytest.fixture(scope='session')
def user_api_client(config):
    """用户端API客户端"""
    return ApiClient(config.USER_H5_URL)


@pytest.fixture(scope='session')
def staff_api_client(config):
    """员工端API客户端"""
    return ApiClient(config.STAFF_H5_URL)


@pytest.fixture(scope='session')
def admin_api_client(config):
    """管理端API客户端"""
    return ApiClient(config.ADMIN_URL)


@pytest.fixture(scope='function')
def test_user_phone():
    """生成测试用手机号"""
    import time
    import random
    return f"138{int(time.time()) % 100000000:08d}"


@pytest.fixture(scope='function')
def test_user(user_api_client, test_user_phone, config):
    """
    创建测试用户并返回用户信息

    使用方式:
        def test_something(test_user):
            user_id = test_user['user_id']
            token = test_user['token']
    """
    # 注册用户
    register_data = {
        'phone': test_user_phone,
        'password': 'test123456',
        'nickname': f'测试用户{test_user_phone[-4:]}',
        'ec_id': config.TEST_EC_ID,
        'project_id': config.TEST_PROJECT_ID
    }

    response = user_api_client.post('/api/user/register', json=register_data)

    if response['success']:
        return {
            'user_id': response['data'].get('user_id'),
            'token': response['data'].get('token'),
            'phone': test_user_phone,
            'api_client': user_api_client
        }

    # 如果注册失败，尝试登录
    login_data = {
        'phone': test_user_phone,
        'password': 'test123456',
        'ec_id': config.TEST_EC_ID,
        'project_id': config.TEST_PROJECT_ID
    }

    login_response = user_api_client.post('/api/user/login', json=login_data)

    if login_response['success']:
        return {
            'user_id': login_response['data'].get('user_id'),
            'token': login_response['data'].get('token'),
            'phone': test_user_phone,
            'api_client': user_api_client
        }

    pytest.skip(f"无法创建测试用户: {response['msg']}")


@pytest.fixture(scope='function')
def admin_user(admin_api_client, config):
    """获取管理端测试用户"""
    login_data = {
        'phone': config.TEST_ADMIN_PHONE,
        'password': config.TEST_ADMIN_PASSWORD,
        'ec_id': config.TEST_EC_ID
    }

    response = admin_api_client.post('/api/admin/login', json=login_data)

    if response['success']:
        token = response['data'].get('token')
        admin_api_client.set_token(token)

        return {
            'user_id': response['data'].get('user_id'),
            'token': token,
            'api_client': admin_api_client
        }

    pytest.skip(f"无法登录管理员账户: {response['msg']}")


@pytest.fixture(scope='function')
def auth_token(test_user):
    """获取认证Token"""
    return test_user['token']


@pytest.fixture(scope='function')
def auth_headers(auth_token):
    """获取认证请求头"""
    return {'Token': auth_token}


# ============ 辅助函数 ============

def assert_success(response: Dict[str, Any], msg: str = None):
    """断言请求成功"""
    assert response['success'], f"请求失败: {response['msg']}" + (f" - {msg}" if msg else "")


def assert_response_code(response: Dict[str, Any], code: int, msg: str = None):
    """断言响应码"""
    assert response['status_code'] == code, \
        f"期望状态码{code}, 实际{response['status_code']}" + (f" - {msg}" if msg else "")


def assert_data_contains(data: Dict, keys: list):
    """断言数据包含指定字段"""
    for key in keys:
        assert key in data, f"响应数据缺少字段: {key}"


def create_test_product(admin_api_client, config, category_id=None):
    """创建测试商品"""
    product_data = {
        'name': f'测试商品_{int(time.time())}',
        'description': '这是一个测试商品',
        'price': 99.99,
        'original_price': 199.99,
        'category_id': category_id or 1,
        'stock': 100,
        'ec_id': config.TEST_EC_ID,
        'project_id': config.TEST_PROJECT_ID,
        'images': ['https://example.com/image.jpg']
    }

    response = admin_api_client.post('/api/admin/products', json=product_data)

    if response['success']:
        return {
            'product_id': response['data'].get('product_id'),
            'product_data': product_data
        }

    return None


def create_test_order(user_api_client, test_user, config, product_id, quantity=1):
    """创建测试订单"""
    order_data = {
        'items': [{
            'product_id': product_id,
            'quantity': quantity
        }],
        'ec_id': config.TEST_EC_ID,
        'project_id': config.TEST_PROJECT_ID,
        'remark': '测试订单'
    }

    # 设置用户Token
    user_api_client.set_token(test_user['token'])

    response = user_api_client.post('/api/user/orders', json=order_data)

    if response['success']:
        return {
            'order_id': response['data'].get('order_id'),
            'order_no': response['data'].get('order_no')
        }

    return None


import time
