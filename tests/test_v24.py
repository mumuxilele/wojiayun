#!/usr/bin/env python3
"""
V24.0 自动化测试
测试范围:
  - 支付服务集成
  - 物流服务增强
  - 拼团服务
  - 统一错误码
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPaymentServiceV24:
    """支付服务V24.0测试"""

    def test_wechat_config_loading(self):
        """测试微信支付配置加载"""
        from business_common.payment_service import PaymentService
        
        # 检查配置类方法
        assert hasattr(PaymentService, 'WECHAT_CONFIG')
        assert hasattr(PaymentService, 'ALIPAY_CONFIG')
        assert hasattr(PaymentService, 'is_wechat_configured')
        assert hasattr(PaymentService, 'is_alipay_configured')

    def test_wechat_sign_method(self):
        """测试微信签名方法存在"""
        from business_common.payment_service import PaymentService
        
        assert hasattr(PaymentService, '_wechat_sign')
        assert hasattr(PaymentService, '_alipay_sign')

    def test_wechat_pay_url_generation(self):
        """测试微信支付URL生成方法"""
        from business_common.payment_service import PaymentService
        
        result = PaymentService._create_wechat_pay_url('TEST123', 100.00)
        # 未配置时应返回Mock URL
        assert 'weixin://wxpay' in result or 'TEST123' in result

    def test_alipay_pay_url_generation(self):
        """测试支付宝支付URL生成方法"""
        from business_common.payment_service import PaymentService
        
        result = PaymentService._create_alipay_pay_url('TEST123', 100.00)
        # 未配置时应返回Mock URL
        assert 'alipays://' in result or 'TEST123' in result


class TestLogisticsServiceV24:
    """物流服务V24.0测试"""

    def test_logistics_config_loading(self):
        """测试物流配置从环境变量读取"""
        from business_common.logistics_service import LogisticsService
        
        assert hasattr(LogisticsService, 'KUAIDI100_KEY')
        assert hasattr(LogisticsService, 'JUHE_KEY')

    def test_kuaidi100_query_method(self):
        """测试快递100查询方法存在"""
        from business_common.logistics_service import LogisticsService
        
        assert hasattr(LogisticsService, '_query_kuaidi100')

    def test_query_logistics_fallback(self):
        """测试物流查询降级逻辑"""
        from business_common.logistics_service import LogisticsService
        
        # 无配置时应返回模拟数据
        result = LogisticsService.query_logistics('TEST123456')
        assert result.get('success') == True
        assert result.get('data', {}).get('is_mock') == True


class TestGroupBuyService:
    """拼团服务测试"""

    def test_group_buy_service_exists(self):
        """测试拼团服务模块存在"""
        from business_common import group_buy_service
        assert hasattr(group_buy_service, 'GroupBuyService')

    def test_group_buy_status_constants(self):
        """测试拼团状态常量"""
        from business_common.group_buy_service import GroupBuyService
        
        assert 'pending' in GroupBuyService.STATUS
        assert 'ongoing' in GroupBuyService.STATUS
        assert 'success' in GroupBuyService.STATUS
        assert 'failed' in GroupBuyService.STATUS

    def test_group_buy_order_status(self):
        """测试拼团订单状态"""
        from business_common.group_buy_service import GroupBuyService
        
        assert 'pending' in GroupBuyService.ORDER_STATUS
        assert 'paid' in GroupBuyService.ORDER_STATUS


class TestErrorCodeV24:
    """错误码V24.0测试"""

    def test_error_code_ranges(self):
        """测试错误码范围定义"""
        from business_common.response_builder import ErrorCode
        
        # 验证错误码存在
        assert hasattr(ErrorCode, 'PARAM_ERROR')
        assert hasattr(ErrorCode, 'AUTH_FAILED')
        assert hasattr(ErrorCode, 'PERMISSION_DENIED')


class TestCodeQuality:
    """代码质量检查"""

    def test_payment_service_imports(self):
        """测试payment_service导入成功"""
        from business_common import payment_service
        assert payment_service.PaymentService is not None

    def test_logistics_service_imports(self):
        """测试logistics_service导入成功"""
        from business_common import logistics_service
        assert logistics_service.LogisticsService is not None

    def test_group_buy_service_imports(self):
        """测试group_buy_service导入成功"""
        from business_common import group_buy_service
        assert group_buy_service.GroupBuyService is not None

    def test_migrate_v24_exists(self):
        """测试V24迁移脚本存在"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'migrate_v24.py'
        )
        assert os.path.exists(script_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])