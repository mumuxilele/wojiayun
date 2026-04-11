#!/usr/bin/env python3
"""
V44.0 自动化测试
测试范围:
  - 外部认证服务
  - 企微推送服务
  - 系统联动服务
  - 大厦门禁卡申请
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExternalAuthService:
    """外部认证服务测试"""

    def test_service_exists(self):
        """测试服务模块存在"""
        from business_common import external_auth_service
        assert external_auth_service.ExternalAuthService is not None

    def test_auth_urls_defined(self):
        """测试认证地址定义"""
        from business_common.external_auth_service import ExternalAuthService
        
        assert hasattr(ExternalAuthService, 'USER_AUTH_URL')
        assert hasattr(ExternalAuthService, 'STAFF_AUTH_URL')
        assert 'wojiacloud.com' in ExternalAuthService.USER_AUTH_URL
        assert 'wojiacloud.com' in ExternalAuthService.STAFF_AUTH_URL

    def test_verify_methods_exist(self):
        """测试验证方法存在"""
        from business_common.external_auth_service import ExternalAuthService
        
        assert hasattr(ExternalAuthService, 'verify_user_token')
        assert hasattr(ExternalAuthService, 'verify_staff_token')
        assert hasattr(ExternalAuthService, 'get_user_info')
        assert hasattr(ExternalAuthService, 'get_staff_info')

    def test_decorators_exist(self):
        """测试装饰器存在"""
        from business_common.external_auth_service import require_external_user, require_external_staff
        
        assert callable(require_external_user)
        assert callable(require_external_staff)


class TestWeComPushService:
    """企微推送服务测试"""

    def test_service_exists(self):
        """测试服务模块存在"""
        from business_common import wecom_push_service
        assert wecom_push_service.WeComPushService is not None

    def test_push_methods_exist(self):
        """测试推送方法存在"""
        from business_common.wecom_push_service import WeComPushService
        
        assert hasattr(WeComPushService, 'send_message')
        assert hasattr(WeComPushService, 'push_approval_result')
        assert hasattr(WeComPushService, 'push_application_remind')
        assert hasattr(WeComPushService, 'push_expire_remind')
        assert hasattr(WeComPushService, 'push_to_approvers')


class TestSystemLinkageService:
    """系统联动服务测试"""

    def test_service_exists(self):
        """测试服务模块存在"""
        from business_common import system_linkage_service
        assert system_linkage_service.SystemLinkageService is not None

    def test_access_control_methods(self):
        """测试门禁系统方法"""
        from business_common.system_linkage_service import SystemLinkageService
        
        assert hasattr(SystemLinkageService, 'grant_access_permission')
        assert hasattr(SystemLinkageService, 'revoke_access_permission')

    def test_lift_control_methods(self):
        """测试梯控系统方法"""
        from business_common.system_linkage_service import SystemLinkageService
        
        assert hasattr(SystemLinkageService, 'reserve_cargo_lift')
        assert hasattr(SystemLinkageService, 'check_lift_availability')

    def test_hvac_methods(self):
        """测试暖通系统方法"""
        from business_common.system_linkage_service import SystemLinkageService
        
        assert hasattr(SystemLinkageService, 'request_hvac_overtime')

    def test_monitor_methods(self):
        """测试监控系统方法"""
        from business_common.system_linkage_service import SystemLinkageService
        
        assert hasattr(SystemLinkageService, 'log_monitor_query')


class TestAccessCardApplication:
    """大厦门禁卡申请测试"""

    def test_migrate_script_exists(self):
        """测试迁移脚本存在"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'migrate_v44.py'
        )
        assert os.path.exists(script_path)

    def test_api_module_exists(self):
        """测试API模块存在"""
        from business_common import v44_api
        assert hasattr(v44_api, 'register_v44_user_apis')
        assert hasattr(v44_api, 'register_v44_staff_apis')


class TestCodeQuality:
    """代码质量检查"""

    def test_external_auth_imports(self):
        """测试external_auth_service导入成功"""
        from business_common import external_auth_service
        assert external_auth_service.external_auth is not None

    def test_wecom_push_imports(self):
        """测试wecom_push_service导入成功"""
        from business_common import wecom_push_service
        assert wecom_push_service.wecom_push is not None

    def test_system_linkage_imports(self):
        """测试system_linkage_service导入成功"""
        from business_common import system_linkage_service
        assert system_linkage_service.system_linkage is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
