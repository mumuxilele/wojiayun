#!/usr/bin/env python3
"""
外部认证服务模块 V44.0
功能：
  - 用户端Token验证（wj.wojiacloud.com）
  - 员工端Token验证（gj.wojiacloud.com）
  - 统一身份认证接口
"""
import json
import logging
import requests
from functools import wraps
from . import db

logger = logging.getLogger(__name__)


class ExternalAuthService:
    """外部认证服务"""

    # 外部认证服务地址
    USER_AUTH_URL = 'https://wj.wojiacloud.com/api/user/info'
    STAFF_AUTH_URL = 'https://gj.wojiacloud.com/api/staff/info'

    # Token缓存时间（秒）
    TOKEN_CACHE_TTL = 300  # 5分钟

    @staticmethod
    def verify_user_token(token, isdev='0'):
        """
        验证用户端Token

        Args:
            token: 用户access_token
            isdev: 是否开发环境

        Returns:
            dict: 用户信息，包含user_id, ec_id, project_id等
        """
        if not token:
            return None

        try:
            # 调用外部认证接口
            url = f"{ExternalAuthService.USER_AUTH_URL}?access_token={token}"
            if isdev and isdev != '0':
                url += f"&isdev={isdev}"

            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    user_info = data.get('data', {})
                    # 确保必要字段存在
                    return {
                        'user_id': user_info.get('userId') or user_info.get('user_id'),
                        'user_name': user_info.get('userName') or user_info.get('user_name'),
                        'user_phone': user_info.get('phone') or user_info.get('user_phone'),
                        'ec_id': user_info.get('ecId') or user_info.get('ec_id'),
                        'project_id': user_info.get('projectId') or user_info.get('project_id'),
                        'company_name': user_info.get('companyName') or user_info.get('company_name'),
                    }

            logger.warning(f"用户Token验证失败: status={resp.status_code}")
            return None

        except requests.RequestException as e:
            logger.error(f"用户Token验证请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"用户Token验证异常: {e}")
            return None

    @staticmethod
    def verify_staff_token(token, isdev='0'):
        """
        验证员工端Token

        Args:
            token: 员工access_token
            isdev: 是否开发环境

        Returns:
            dict: 员工信息，包含staff_id, ec_id, project_id等
        """
        if not token:
            return None

        try:
            # 调用外部认证接口
            url = f"{ExternalAuthService.STAFF_AUTH_URL}?access_token={token}"
            if isdev and isdev != '0':
                url += f"&isdev={isdev}"

            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    staff_info = data.get('data', {})
                    # 确保必要字段存在
                    return {
                        'staff_id': staff_info.get('staffId') or staff_info.get('staff_id'),
                        'staff_name': staff_info.get('staffName') or staff_info.get('staff_name'),
                        'staff_phone': staff_info.get('phone') or staff_info.get('staff_phone'),
                        'ec_id': staff_info.get('ecId') or staff_info.get('ec_id'),
                        'project_id': staff_info.get('projectId') or staff_info.get('project_id'),
                        'department': staff_info.get('department'),
                        'position': staff_info.get('position'),
                        'roles': staff_info.get('roles', []),
                    }

            logger.warning(f"员工Token验证失败: status={resp.status_code}")
            return None

        except requests.RequestException as e:
            logger.error(f"员工Token验证请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"员工Token验证异常: {e}")
            return None

    @staticmethod
    def get_user_info(token):
        """
        获取用户完整信息（getUserInfo接口）

        Args:
            token: 用户access_token

        Returns:
            dict: 用户完整信息
        """
        return ExternalAuthService.verify_user_token(token)

    @staticmethod
    def get_staff_info(token):
        """
        获取员工完整信息

        Args:
            token: 员工access_token

        Returns:
            dict: 员工完整信息
        """
        return ExternalAuthService.verify_staff_token(token)


def require_external_user(f):
    """
    装饰器：验证外部用户Token
    使用方式：@require_external_user
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request, jsonify

        token = request.args.get('access_token') or request.headers.get('Token')
        isdev = request.args.get('isdev', '0')

        if not token:
            return jsonify({'success': False, 'msg': '请先登录', 'code': 10001})

        user = ExternalAuthService.verify_user_token(token, isdev)
        if not user:
            return jsonify({'success': False, 'msg': '登录已过期，请重新登录', 'code': 10002})

        return f(user, *args, **kwargs)

    return decorated


def require_external_staff(f):
    """
    装饰器：验证外部员工Token
    使用方式：@require_external_staff
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request, jsonify

        token = request.args.get('access_token') or request.headers.get('Token')
        isdev = request.args.get('isdev', '0')

        if not token:
            return jsonify({'success': False, 'msg': '请先登录', 'code': 20001})

        staff = ExternalAuthService.verify_staff_token(token, isdev)
        if not staff:
            return jsonify({'success': False, 'msg': '登录已过期，请重新登录', 'code': 20002})

        return f(staff, *args, **kwargs)

    return decorated


# 便捷实例
external_auth = ExternalAuthService()
