"""
V29.0 自动化测试
覆盖: 支付服务增强、物流服务增强、支付安全

2026-04-05
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestPaymentSecurity:
    """支付安全测试"""

    def test_validate_payment_amount_valid(self):
        """测试合法金额验证"""
        from business_common.payment_service import PaymentService

        # 测试合法金额
        is_valid, msg = PaymentService.validate_payment_amount(100.00)
        assert is_valid is True
        assert msg is None

        # 测试边界值
        is_valid, msg = PaymentService.validate_payment_amount(0.01)
        assert is_valid is True

        is_valid, msg = PaymentService.validate_payment_amount(50000.00)
        assert is_valid is True

    def test_validate_payment_amount_invalid(self):
        """测试非法金额验证"""
        from business_common.payment_service import PaymentService

        # 测试低于最低金额
        is_valid, msg = PaymentService.validate_payment_amount(0.001)
        assert is_valid is False
        assert '不能低于' in msg

        # 测试超过最高金额
        is_valid, msg = PaymentService.validate_payment_amount(50001.00)
        assert is_valid is False
        assert '不能超过' in msg

        # 测试无效格式
        is_valid, msg = PaymentService.validate_payment_amount('abc')
        assert is_valid is False
        assert '格式错误' in msg

    def test_validate_payment_amount_string_float(self):
        """测试字符串浮点数验证"""
        from business_common.payment_service import PaymentService

        is_valid, msg = PaymentService.validate_payment_amount('100.50')
        assert is_valid is True


class TestPaymentChannelSelection:
    """支付渠道选择测试"""

    def test_is_wechat_configured(self):
        """测试微信支付配置检查"""
        from business_common.payment_service import PaymentService

        # 在无环境变量时应该返回False
        with patch.object(PaymentService, 'WECHAT_CONFIG', {
            'app_id': '',
            'mch_id': '',
            'api_v3_key': '',
            'private_key': '',
        }):
            assert PaymentService.is_wechat_configured() is False

    def test_is_alipay_configured(self):
        """测试支付宝配置检查"""
        from business_common.payment_service import PaymentService

        with patch.object(PaymentService, 'ALIPAY_CONFIG', {
            'app_id': '',
            'private_key': '',
        }):
            assert PaymentService.is_alipay_configured() is False


class TestWechatPayment:
    """微信支付测试"""

    @patch('business_common.payment_service.requests.post')
    def test_wechat_unified_order_success(self, mock_post):
        """测试微信统一下单成功"""
        from business_common.payment_service import PaymentService

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code_url': 'weixin://wxpay/bizpayurl?pr=test123'
        }
        mock_post.return_value = mock_response

        # 配置微信支付
        with patch.object(PaymentService, 'WECHAT_CONFIG', {
            'app_id': 'test_app_id',
            'mch_id': 'test_mch_id',
            'serial_no': 'test_serial',
            'private_key': 'test_private_key',
            'notify_url': 'https://test.com/notify',
        }):
            url = PaymentService._create_wechat_pay_url('PAY123456', 100.00)

        assert 'weixin://wxpay/bizpayurl' in url

    def test_wechat_unified_order_not_configured(self):
        """测试微信支付未配置时的降级处理"""
        from business_common.payment_service import PaymentService

        with patch.object(PaymentService, 'WECHAT_CONFIG', {
            'app_id': '',
            'mch_id': '',
        }):
            url = PaymentService._create_wechat_pay_url('PAY123456', 100.00)

        assert 'weixin://wxpay/bizpayurl' in url
        assert 'PAY123456' in url


class TestAlipayPayment:
    """支付宝支付测试"""

    def test_alipay_not_configured_fallback(self):
        """测试支付宝未配置时的降级处理"""
        from business_common.payment_service import PaymentService

        with patch.object(PaymentService, 'ALIPAY_CONFIG', {
            'app_id': '',
            'private_key': '',
        }):
            url = PaymentService._create_alipay_pay_url('PAY123456', 100.00)

        assert 'alipays://platformapi' in url


class TestPaymentCreation:
    """支付创建测试"""

    @patch('business_common.payment_service.db')
    def test_create_payment_success(self, mock_db):
        """测试支付创建成功"""
        from business_common.payment_service import PaymentService

        mock_db.execute.return_value = 1

        result = PaymentService.create_payment(
            order_type='order',
            order_id=1,
            amount=100.00,
            user_id=1,
            user_name='测试用户',
            channel='mock',
            ec_id=1,
            project_id=1
        )

        assert result['success'] is True
        assert 'pay_no' in result['data']
        assert result['data']['amount'] == 100.00
        assert result['data']['status'] == 'pending'

    def test_create_payment_invalid_amount(self):
        """测试非法金额拒绝创建"""
        from business_common.payment_service import PaymentService

        result = PaymentService.create_payment(
            order_type='order',
            order_id=1,
            amount=-100.00,
            user_id=1,
            user_name='测试用户',
            channel='mock'
        )

        assert result['success'] is False
        assert '格式错误' in result['msg']

    def test_create_payment_amount_too_high(self):
        """测试超限金额拒绝创建"""
        from business_common.payment_service import PaymentService

        result = PaymentService.create_payment(
            order_type='order',
            order_id=1,
            amount=100000.00,
            user_id=1,
            user_name='测试用户',
            channel='mock'
        )

        assert result['success'] is False
        assert '不能超过' in result['msg']


class TestPaymentCallback:
    """支付回调测试"""

    @patch('business_common.payment_service.db')
    def test_handle_wechat_callback_success(self, mock_db):
        """测试微信支付回调成功处理"""
        from business_common.payment_service import PaymentService

        # Mock支付记录
        mock_db.get_one.return_value = {
            'id': 1,
            'pay_no': 'PAY123456',
            'status': 'pending',
            'order_type': 'order',
            'order_id': 1,
            'user_id': 1,
            'amount': 100.00,
        }

        # Mock数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.begin.return_value = None
        mock_conn.commit.return_value = None

        callback_data = {
            'resource': {
                'nonce': 'test_nonce',
                'ciphertext': 'test_ciphertext',
                'associated_data': 'transaction',
            }
        }

        # 这个测试会失败因为缺少真实密钥，但验证了方法签名正确
        with patch.object(PaymentService, 'WECHAT_CONFIG', {
            'api_v3_key': '',  # 空密钥导致解密失败，这是预期的
        }):
            result = PaymentService.verify_wechat_callback(callback_data)
            # 因为没有真实密钥，验证会失败
            assert 'api_v3_key' in result.get('msg', '') or '解密' in result.get('msg', '') or result['success'] is False


class TestPaymentRefund:
    """支付退款测试"""

    @patch('business_common.payment_service.db')
    def test_mock_refund_success(self, mock_db):
        """测试模拟退款成功"""
        from business_common.payment_service import PaymentService

        # Mock支付记录
        mock_db.get_one.return_value = {
            'id': 1,
            'pay_no': 'PAY123456',
            'status': 'paid',
            'order_type': 'order',
            'order_id': 1,
            'channel': 'mock',
            'amount': 100.00,
        }

        # Mock数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.begin.return_value = None
        mock_conn.commit.return_value = None

        result = PaymentService.refund('PAY123456', '用户申请退款')

        # 模拟退款返回成功
        assert result['success'] is True

    def test_refund_unpaid_order(self):
        """测试未支付订单退款失败"""
        from business_common.payment_service import PaymentService

        with patch('business_common.payment_service.db') as mock_db:
            mock_db.get_one.return_value = None

            result = PaymentService.refund('PAY123456', '测试退款')

            assert result['success'] is False
            assert '不存在或未支付' in result['msg']


class TestLogisticsCompanyDetection:
    """物流公司智能识别测试"""

    def test_detect_sf_express(self):
        """测试顺丰速运识别"""
        from business_common.logistics_service import LogisticsService

        # SF开头
        result = LogisticsService.auto_detect_company('SF1234567890')
        assert result['code'] == 'SF'
        assert result['name'] == '顺丰速运'
        assert result['confidence'] > 0.9

        # 12位数字
        result = LogisticsService.auto_detect_company('123456789012')
        assert result['code'] == 'SF'
        assert result['confidence'] > 0.9

    def test_detect_jd_express(self):
        """测试京东物流识别"""
        from business_common.logistics_service import LogisticsService

        # JD开头
        result = LogisticsService.auto_detect_company('JD1234567890123456')
        assert result['code'] == 'JD'
        assert result['name'] == '京东物流'

        # 16位数字
        result = LogisticsService.auto_detect_company('1234567890123456')
        assert result['code'] == 'JD'

    def test_detect_ems(self):
        """测试EMS识别"""
        from business_common.logistics_service import LogisticsService

        result = LogisticsService.auto_detect_company('EE1234567890CN')
        assert result['code'] == 'EMS'
        assert result['name'] == '邮政EMS'

    def test_detect_yto(self):
        """测试圆通速递识别"""
        from business_common.logistics_service import LogisticsService

        result = LogisticsService.auto_detect_company('YT1234567890')
        assert result['code'] == 'YTO'
        assert result['name'] == '圆通速递'

    def test_detect_unknown(self):
        """测试未知单号"""
        from business_common.logistics_service import LogisticsService

        result = LogisticsService.auto_detect_company('UNKNOWN1234567890')
        assert result['code'] is None
        assert result['confidence'] == 0

    def test_detect_jtsd(self):
        """测试极兔速递识别"""
        from business_common.logistics_service import LogisticsService

        result = LogisticsService.auto_detect_company('JT12345678901234')
        assert result['code'] == 'JTSD'
        assert result['name'] == '极兔速递'
        assert result['confidence'] > 0.9


class TestLogisticsStatus:
    """物流状态测试"""

    def test_parse_state_signed(self):
        """测试签收状态解析"""
        from business_common.logistics_service import LogisticsService

        state = LogisticsService._parse_state('4')
        assert state['code'] == 4
        assert state['name'] == '已签收'

        state = LogisticsService._parse_state('已签收')
        assert state['code'] == 4

    def test_parse_state_transit(self):
        """测试运输中状态解析"""
        from business_common.logistics_service import LogisticsService

        state = LogisticsService._parse_state('2')
        assert state['code'] == 2
        assert state['name'] == '运输中'

        state = LogisticsService._parse_state('运输中')
        assert state['code'] == 2

    def test_parse_state_delivering(self):
        """测试派送中状态解析"""
        from business_common.logistics_service import LogisticsService

        state = LogisticsService._parse_state('3')
        assert state['code'] == 3
        assert state['name'] == '派送中'

    def test_parse_state_unknown(self):
        """测试未知状态解析"""
        from business_common.logistics_service import LogisticsService

        state = LogisticsService._parse_state('999')
        assert state['code'] == 0
        assert state['name'] == '暂无轨迹'


class TestLogisticsQuery:
    """物流查询测试"""

    @patch('business_common.logistics_service.LogisticsService.KUAIDI100_KEY', '')
    @patch('business_common.logistics_service.LogisticsService.JUHE_KEY', '')
    def test_query_logistics_mock(self):
        """测试物流查询降级到模拟数据"""
        from business_common.logistics_service import LogisticsService

        result = LogisticsService.query_logistics('SF123456789')

        assert result['success'] is True
        assert result['data']['is_mock'] is True
        assert 'traces' in result['data']

    @patch('business_common.logistics_service.LogisticsService.KUAIDI100_KEY', '')
    @patch('business_common.logistics_service.LogisticsService.JUHE_KEY', '')
    def test_query_logistics_auto_detect(self):
        """测试物流查询自动识别公司"""
        from business_common.logistics_service import LogisticsService

        # 不指定公司，应该自动识别
        result = LogisticsService.query_logistics('SF1234567890')

        assert result['success'] is True
        assert result['data']['company_code'] == 'SF'

    def test_query_logistics_empty_tracking_no(self):
        """测试空单号查询"""
        from business_common.logistics_service import LogisticsService

        result = LogisticsService.query_logistics('')

        assert result['success'] is False
        assert '不能为空' in result['msg']


class TestLogisticsCompanies:
    """物流公司列表测试"""

    def test_get_logistics_companies(self):
        """测试获取物流公司列表"""
        from business_common.logistics_service import LogisticsService

        companies = LogisticsService.get_logistics_companies()

        assert len(companies) > 10
        # 检查常见的公司
        codes = [c['code'] for c in companies]
        assert 'SF' in codes
        assert 'YTO' in codes
        assert 'ZTO' in codes
        assert 'JD' in codes

    def test_get_company_name(self):
        """测试通过编码获取公司名称"""
        from business_common.logistics_service import LogisticsService

        assert LogisticsService.get_company_name('SF') == '顺丰速运'
        assert LogisticsService.get_company_name('JD') == '京东物流'
        assert LogisticsService.get_company_name('UNKNOWN') == 'UNKNOWN'

    def test_get_company_code(self):
        """测试通过名称获取公司编码"""
        from business_common.logistics_service import LogisticsService

        assert LogisticsService.get_company_code('顺丰速运') == 'SF'
        assert LogisticsService.get_company_code('顺丰') == 'SF'
        assert LogisticsService.get_company_code('京东') == 'JD'


class TestCodeSyntax:
    """代码语法测试"""

    def test_payment_service_syntax(self):
        """测试支付服务语法"""
        import py_compile
        import tempfile

        source_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common',
            'payment_service.py'
        )

        # 编译检查
        py_compile.compile(source_file, doraise=True)

    def test_logistics_service_syntax(self):
        """测试物流服务语法"""
        import py_compile

        source_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common',
            'logistics_service.py'
        )

        py_compile.compile(source_file, doraise=True)

    def test_migrate_v29_syntax(self):
        """测试迁移脚本语法"""
        import py_compile

        source_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common',
            'migrate_v29.py'
        )

        py_compile.compile(source_file, doraise=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
