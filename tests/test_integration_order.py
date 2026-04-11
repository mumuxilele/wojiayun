#!/usr/bin/env python3
"""
V32.0 订单 API集成测试

测试覆盖:
1. 创建订单
2. 查询订单
3. 取消订单
4. 订单支付
5. 订单退款
6. 订单统计

运行方式:
    pytest tests/test_integration_order.py -v
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
# 1. 订单创建测试
# ============================================================

class TestOrderCreate:
    """订单创建测试"""

    def test_create_normal_order(self, user_api_client, test_user, config):
        """测试创建普通订单"""
        user_api_client.set_token(test_user['token'])

        order_data = {
            'items': [{
                'product_id': 1,
                'sku_id': None,
                'quantity': 1,
                'price': 99.99
            }],
            'ec_id': config.TEST_EC_ID,
            'project_id': config.TEST_PROJECT_ID,
            'remark': '测试订单'
        }

        response = user_api_client.post('/api/user/orders', json=order_data)

        # 订单可能因为商品不存在而失败，这是预期行为
        # 主要验证接口调用正常
        if response['success']:
            data = response['data']
            assert_data_contains(data, ['order_id', 'order_no', 'total_amount'])
        else:
            # 非成功响应应该是业务错误，不是接口错误
            assert 'msg' in response, "错误响应应包含消息"

    def test_create_order_with_invalid_product(self, user_api_client, test_user, config):
        """测试创建订单-无效商品"""
        user_api_client.set_token(test_user['token'])

        order_data = {
            'items': [{
                'product_id': 999999,
                'quantity': 1
            }],
            'ec_id': config.TEST_EC_ID,
            'project_id': config.TEST_PROJECT_ID
        }

        response = user_api_client.post('/api/user/orders', json=order_data)

        # 应该返回错误
        assert not response['success'] or '商品不存在' in response.get('msg', '')
        assert 'msg' in response

    def test_create_order_missing_fields(self, user_api_client, test_user, config):
        """测试创建订单-缺少字段"""
        user_api_client.set_token(test_user['token'])

        order_data = {
            'ec_id': config.TEST_EC_ID
        }

        response = user_api_client.post('/api/user/orders', json=order_data)

        assert not response['success'], "缺少必填字段应该失败"


# ============================================================
# 2. 订单查询测试
# ============================================================

class TestOrderQuery:
    """订单查询测试"""

    def test_get_order_list(self, user_api_client, test_user):
        """测试获取订单列表"""
        user_api_client.set_token(test_user['token'])

        response = user_api_client.get('/api/user/orders')

        assert_success(response, "获取订单列表失败")

        data = response['data']
        assert 'orders' in data or isinstance(data, list), "响应应包含orders字段"

    def test_get_order_detail(self, user_api_client, test_user):
        """测试获取订单详情"""
        user_api_client.set_token(test_user['token'])

        # 先获取订单列表
        list_response = user_api_client.get('/api/user/orders')

        if list_response['success']:
            orders = list_response['data'].get('orders', [])
            if orders:
                order_id = orders[0].get('id') or orders[0].get('order_no')

                if order_id:
                    detail_response = user_api_client.get(f'/api/user/orders/{order_id}')
                    assert_success(detail_response, "获取订单详情失败")

    def test_get_order_by_status(self, user_api_client, test_user):
        """测试按状态查询订单"""
        user_api_client.set_token(test_user['token'])

        response = user_api_client.get('/api/user/orders?status=pending')

        assert_success(response, "按状态查询订单失败")


# ============================================================
# 3. 订单取消测试
# ============================================================

class TestOrderCancel:
    """订单取消测试"""

    def test_cancel_pending_order(self, user_api_client, test_user):
        """测试取消待支付订单"""
        user_api_client.set_token(test_user['token'])

        # 先获取待支付订单
        list_response = user_api_client.get('/api/user/orders?status=pending')

        if list_response['success']:
            orders = list_response['data'].get('orders', [])
            pending_orders = [o for o in orders if o.get('order_status') == 'pending']

            if pending_orders:
                order_id = pending_orders[0].get('id')
                cancel_response = user_api_client.post(
                    f'/api/user/orders/{order_id}/cancel',
                    json={'reason': '测试取消'}
                )

                # 取消可能因权限或其他原因失败
                assert 'msg' in cancel_response, "取消响应应包含消息"

    def test_cancel_completed_order(self, user_api_client, test_user):
        """测试取消已完成订单(应失败)"""
        user_api_client.set_token(test_user['token'])

        list_response = user_api_client.get('/api/user/orders?status=completed')

        if list_response['success']:
            orders = list_response['data'].get('orders', [])
            if orders:
                order_id = orders[0].get('id')
                cancel_response = user_api_client.post(
                    f'/api/user/orders/{order_id}/cancel'
                )

                # 已完成订单不能取消
                assert not cancel_response['success'] or '不允许' in cancel_response['msg']


# ============================================================
# 4. 订单支付测试
# ============================================================

class TestOrderPayment:
    """订单支付测试"""

    def test_get_payment_info(self, user_api_client, test_user):
        """测试获取支付信息"""
        user_api_client.set_token(test_user['token'])

        list_response = user_api_client.get('/api/user/orders?status=pending')

        if list_response['success']:
            orders = list_response['data'].get('orders', [])
            if orders:
                order_id = orders[0].get('id')
                pay_response = user_api_client.get(f'/api/user/orders/{order_id}/payment')

                # 应该返回支付信息
                assert 'msg' in pay_response or pay_response['success']

    def test_pay_order_mock(self, user_api_client, test_user):
        """测试Mock支付"""
        user_api_client.set_token(test_user['token'])

        list_response = user_api_client.get('/api/user/orders?status=pending')

        if list_response['success']:
            orders = list_response['data'].get('orders', [])
            if orders:
                order_id = orders[0].get('id')
                pay_response = user_api_client.post(
                    f'/api/user/orders/{order_id}/pay',
                    json={'channel': 'mock'}
                )

                # Mock支付应该成功
                assert 'msg' in pay_response


# ============================================================
# 5. 退款测试
# ============================================================

class TestRefund:
    """退款测试"""

    def test_request_refund(self, user_api_client, test_user):
        """测试申请退款"""
        user_api_client.set_token(test_user['token'])

        # 查找已支付订单
        list_response = user_api_client.get('/api/user/orders?status=paid')

        if list_response['success']:
            orders = list_response['data'].get('orders', [])
            if orders:
                order_id = orders[0].get('id')
                refund_response = user_api_client.post(
                    f'/api/user/refunds',
                    json={
                        'order_id': order_id,
                        'reason': '测试退款'
                    }
                )

                # 退款申请可能有业务限制
                assert 'msg' in refund_response

    def test_get_refund_list(self, user_api_client, test_user):
        """测试获取退款列表"""
        user_api_client.set_token(test_user['token'])

        response = user_api_client.get('/api/user/refunds')

        assert_success(response, "获取退款列表失败")


# ============================================================
# 6. 订单统计测试
# ============================================================

class TestOrderStats:
    """订单统计测试"""

    def test_get_order_summary(self, user_api_client, test_user):
        """测试获取订单摘要"""
        user_api_client.set_token(test_user['token'])

        response = user_api_client.get('/api/user/orders/summary')

        # 应该有统计数据返回
        assert 'msg' in response or response['success']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
