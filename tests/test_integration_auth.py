#!/usr/bin/env python3
"""
V32.0 会员注册/登录 API集成测试

测试覆盖:
1. 用户注册
2. 用户登录
3. 获取用户信息
4. 修改用户资料
5. 签到打卡
6. 获取积分历史

运行方式:
    pytest tests/test_integration_auth.py -v
"""

import pytest
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import (
    ApiClient, TestConfig, assert_success, assert_data_contains
)


# ============================================================
# 1. 用户注册测试
# ============================================================

class TestUserRegister:
    """用户注册测试"""

    def test_register_with_phone_password(self, user_api_client, config):
        """测试手机号密码注册"""
        phone = f"138{int(time.time()) % 100000000:08d}"

        data = {
            'phone': phone,
            'password': 'test123456',
            'nickname': f'用户{phone[-4:]}',
            'ec_id': config.TEST_EC_ID,
            'project_id': config.TEST_PROJECT_ID
        }

        response = user_api_client.post('/api/user/register', json=data)

        assert_success(response, "注册失败")
        assert_data_contains(response['data'], ['user_id', 'token', 'phone'])
        assert response['data']['phone'] == phone
        assert response['data'].get('initial_points', 0) >= 0

    def test_register_duplicate_phone(self, user_api_client, test_user, config):
        """测试重复手机号注册"""
        data = {
            'phone': test_user['phone'],
            'password': 'test123456',
            'ec_id': config.TEST_EC_ID,
            'project_id': config.TEST_PROJECT_ID
        }

        response = user_api_client.post('/api/user/register', json=data)
        assert not response['success'], "重复手机号应该注册失败"

    def test_register_missing_fields(self, user_api_client, config):
        """测试缺少必填字段"""
        data = {
            'password': 'test123456',
            'ec_id': config.TEST_EC_ID
        }

        response = user_api_client.post('/api/user/register', json=data)
        assert not response['success'], "缺少必填字段应该失败"


# ============================================================
# 2. 用户登录测试
# ============================================================

class TestUserLogin:
    """用户登录测试"""

    def test_login_with_password(self, user_api_client, test_user, config):
        """测试密码登录"""
        data = {
            'phone': test_user['phone'],
            'password': 'test123456',
            'ec_id': config.TEST_EC_ID,
            'project_id': config.TEST_PROJECT_ID
        }

        response = user_api_client.post('/api/user/login', json=data)
        assert_success(response, "登录失败")
        assert_data_contains(response['data'], ['user_id', 'token'])

    def test_login_wrong_password(self, user_api_client, test_user, config):
        """测试密码错误"""
        data = {
            'phone': test_user['phone'],
            'password': 'wrongpassword',
            'ec_id': config.TEST_EC_ID
        }

        response = user_api_client.post('/api/user/login', json=data)
        assert not response['success'], "密码错误应该登录失败"


# ============================================================
# 3. 用户信息测试
# ============================================================

class TestUserProfile:
    """用户信息测试"""

    def test_get_user_info(self, user_api_client, test_user):
        """测试获取用户信息"""
        user_api_client.set_token(test_user['token'])
        response = user_api_client.get('/api/user/profile')
        assert_success(response, "获取用户信息失败")
        data = response['data']
        assert_data_contains(data, ['user_id', 'phone', 'points'])

    def test_get_member_info(self, user_api_client, test_user):
        """测试获取会员信息"""
        user_api_client.set_token(test_user['token'])
        response = user_api_client.get('/api/user/member')
        assert_success(response, "获取会员信息失败")
        data = response['data']
        assert_data_contains(data, ['user_id', 'member_level', 'points'])


# ============================================================
# 4. 签到打卡测试
# ============================================================

class TestCheckin:
    """签到打卡测试"""

    def test_checkin(self, user_api_client, test_user):
        """测试签到"""
        user_api_client.set_token(test_user['token'])
        response = user_api_client.post('/api/user/checkin')
        assert_success(response, "签到失败")
        data = response['data']
        assert_data_contains(data, ['points', 'streak'])

    def test_checkin_twice_same_day(self, user_api_client, test_user):
        """测试同一天重复签到"""
        user_api_client.set_token(test_user['token'])
        user_api_client.post('/api/user/checkin')
        second_response = user_api_client.post('/api/user/checkin')
        assert not second_response['success'], "同一天重复签到应该失败"

    def test_get_checkin_status(self, user_api_client, test_user):
        """测试获取签到状态"""
        user_api_client.set_token(test_user['token'])
        response = user_api_client.get('/api/user/checkin/status')
        assert_success(response, "获取签到状态失败")
        data = response['data']
        assert_data_contains(data, ['already_checkin', 'current_streak'])


# ============================================================
# 5. 积分相关测试
# ============================================================

class TestPoints:
    """积分相关测试"""

    def test_get_points_history(self, user_api_client, test_user):
        """测试获取积分历史"""
        user_api_client.set_token(test_user['token'])
        response = user_api_client.get('/api/user/points/history')
        assert_success(response, "获取积分历史失败")
        data = response['data']
        assert 'logs' in data or 'total' in data


# ============================================================
# 6. 收货地址测试
# ============================================================

class TestAddress:
    """收货地址测试"""

    def test_add_address(self, user_api_client, test_user, config):
        """测试添加收货地址"""
        user_api_client.set_token(test_user['token'])
        address_data = {
            'receiver_name': '张三',
            'receiver_phone': '13800138000',
            'province': '广东省',
            'city': '深圳市',
            'district': '南山区',
            'detail_address': '科技园xx路xx号',
            'is_default': True,
            'ec_id': config.TEST_EC_ID,
            'project_id': config.TEST_PROJECT_ID
        }
        response = user_api_client.post('/api/user/addresses', json=address_data)
        assert_success(response, "添加地址失败")

    def test_get_addresses(self, user_api_client, test_user):
        """测试获取收货地址列表"""
        user_api_client.set_token(test_user['token'])
        response = user_api_client.get('/api/user/addresses')
        assert_success(response, "获取地址列表失败")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
