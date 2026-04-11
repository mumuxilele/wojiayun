"""
V32.0 自动化测试框架
测试范围:
  - 购物车功能测试
  - 订单流程测试
  - 库存预警测试
  - FAQ功能测试
  - 消息推送测试
"""
import unittest
import json
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestShoppingCart(unittest.TestCase):
    """购物车功能测试"""

    def setUp(self):
        """测试初始化"""
        from business_common import db
        self.db = db
        self.user_id = 'test_user_001'
        self.ec_id = 'test_ec'
        self.project_id = 'test_project'

    def test_cart_add_item(self):
        """测试添加商品到购物车"""
        from business_common.cart_service import cart_service

        # 添加商品
        result = cart_service.add_to_cart(
            user_id=self.user_id,
            product_id=1,
            quantity=2,
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        self.assertIsNotNone(result)
        self.assertIn('success', result)

    def test_cart_update_quantity(self):
        """测试更新购物车商品数量"""
        from business_common.cart_service import cart_service

        result = cart_service.update_quantity(
            user_id=self.user_id,
            cart_id=1,
            quantity=5
        )

        self.assertIsNotNone(result)

    def test_cart_merge(self):
        """测试购物车合并"""
        from business_common.cart_service import cart_service

        result = cart_service.merge_cart(
            user_id=self.user_id,
            session_id='session_123',
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        self.assertIsNotNone(result)

    def test_quick_buy(self):
        """测试立即购买"""
        from business_common.cart_service import cart_service

        result = cart_service.create_quick_order(
            user_id=self.user_id,
            product_id=1,
            quantity=1,
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        self.assertIsNotNone(result)


class TestOrderEnhancement(unittest.TestCase):
    """订单增强功能测试"""

    def setUp(self):
        self.order_id = 1
        self.user_id = 'test_user_001'
        self.ec_id = 'test_ec'
        self.project_id = 'test_project'

    def test_update_order_address(self):
        """测试修改订单收货地址"""
        from business_common.order_enhance_service import order_enhance

        result = order_enhance.update_order(
            order_id=self.order_id,
            user_id=self.user_id,
            update_data={
                'receiver_name': '张三',
                'receiver_phone': '13800138000',
                'receiver_address': '北京市朝阳区xxx'
            }
        )

        self.assertIsNotNone(result)

    def test_partial_refund(self):
        """测试部分退款"""
        from business_common.order_enhance_service import order_enhance

        result = order_enhance.partial_refund(
            order_id=self.order_id,
            user_id=self.user_id,
            refund_items=[
                {'product_id': 1, 'quantity': 1}
            ],
            reason='商品损坏'
        )

        self.assertIsNotNone(result)
        self.assertIn('success', result)

    def test_add_order_note(self):
        """测试添加订单留言"""
        from business_common.order_enhance_service import order_enhance

        result = order_enhance.add_order_note(
            order_id=self.order_id,
            user_id=self.user_id,
            note_type='user_question',
            content='请问什么时候发货？'
        )

        self.assertIsNotNone(result)

    def test_cancel_with_reason(self):
        """测试带原因的订单取消"""
        from business_common.order_enhance_service import order_enhance

        result = order_enhance.cancel_with_reason(
            order_id=self.order_id,
            user_id=self.user_id,
            reason='不想要了'
        )

        self.assertIsNotNone(result)


class TestInventoryAlert(unittest.TestCase):
    """库存预警测试"""

    def setUp(self):
        self.ec_id = 'test_ec'
        self.project_id = 'test_project'

    def test_get_low_stock_products(self):
        """测试获取低库存商品"""
        from business_common.inventory_alert_service import inventory_alert

        result = inventory_alert.get_low_stock_products(
            ec_id=self.ec_id,
            project_id=self.project_id,
            threshold=10
        )

        self.assertIsInstance(result, list)

    def test_get_inventory_report(self):
        """测试库存统计报表"""
        from business_common.inventory_alert_service import inventory_alert

        result = inventory_alert.get_inventory_report(
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        self.assertIsNotNone(result)
        self.assertIn('total_products', result)

    def test_replenish_suggestions(self):
        """测试补货建议"""
        from business_common.inventory_alert_service import inventory_alert

        result = inventory_alert.get_replenish_suggestions(
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        self.assertIsInstance(result, list)


class TestFAQService(unittest.TestCase):
    """FAQ知识库测试"""

    def setUp(self):
        self.ec_id = 'test_ec'
        self.project_id = 'test_project'
        self.user_id = 'test_user_001'

    def test_get_categories(self):
        """测试获取FAQ分类"""
        from business_common.faq_service import faq_service

        result = faq_service.get_categories(
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_search_faqs(self):
        """测试FAQ搜索"""
        from business_common.faq_service import faq_service

        result = faq_service.search_faqs(
            query='退款',
            ec_id=self.ec_id,
            project_id=self.project_id,
            limit=5
        )

        self.assertIsInstance(result, list)

    def test_get_faq_detail(self):
        """测试获取FAQ详情"""
        from business_common.faq_service import faq_service

        result = faq_service.get_faq_detail(
            faq_id=1,
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        # 可能是None（如果FAQ不存在），但不报错
        self.assertTrue(result is None or isinstance(result, dict))

    def test_submit_feedback(self):
        """测试提交FAQ反馈"""
        from business_common.faq_service import faq_service

        result = faq_service.submit_feedback(
            faq_id=1,
            user_id=self.user_id,
            is_helpful=True
        )

        self.assertIsNotNone(result)
        self.assertIn('success', result)


class TestPushService(unittest.TestCase):
    """消息推送测试"""

    def setUp(self):
        self.user_id = 'test_user_001'
        self.ec_id = 'test_ec'
        self.project_id = 'test_project'

    def test_get_template(self):
        """测试获取推送模板"""
        from business_common.push_service import push_service

        result = push_service.get_template(
            template_code='order_paid',
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        self.assertIsNotNone(result)

    def test_send_message(self):
        """测试发送消息"""
        from business_common.push_service import push_service

        result = push_service.send_message(
            template_code='order_paid',
            user_id=self.user_id,
            params={
                'order_no': 'ORD202401010001',
                'amount': '99.00'
            },
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        self.assertIsNotNone(result)

    def test_batch_send(self):
        """测试批量发送"""
        from business_common.push_service import push_service

        result = push_service.batch_send(
            template_code='reminder',
            user_ids=['user1', 'user2', 'user3'],
            params={'content': '这是一条测试消息'},
            ec_id=self.ec_id,
            project_id=self.project_id
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.get('total', 0) >= 3)


class TestAPIVersioning(unittest.TestCase):
    """API版本管理测试"""

    def test_version_detection(self):
        """测试版本检测"""
        from business_common.api_versioning import APIVersionMiddleware

        # 测试默认版本
        version = APIVersionMiddleware.get_version()
        self.assertIsNotNone(version)

    def test_version_upgrade_check(self):
        """测试版本升级检查"""
        from business_common.api_versioning import APIVersionMiddleware

        status = APIVersionMiddleware.should_upgrade('v3')
        self.assertEqual(status, 'ok')

        status = APIVersionMiddleware.should_upgrade('v1')
        self.assertIn(status, ['ok', 'deprecated'])


class TestEnhancedMonitor(unittest.TestCase):
    """系统监控测试"""

    def test_get_metrics(self):
        """测试获取系统指标"""
        from business_common.enhanced_monitor import EnhancedMonitor

        result = EnhancedMonitor.get_metrics()
        self.assertIsNotNone(result)
        self.assertIn('system', result)

    def test_health_check(self):
        """测试健康检查"""
        from business_common.enhanced_monitor import EnhancedMonitor

        result = EnhancedMonitor.get_health_check()
        self.assertIsNotNone(result)
        self.assertIn('healthy', result)
        self.assertIn('checks', result)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_complete_order_flow(self):
        """测试完整订单流程"""
        from business_common.cart_service import cart_service
        from business_common.order_enhance_service import order_enhance

        user_id = 'integration_test_user'
        ec_id = 'test_ec'
        project_id = 'test_project'

        # 1. 添加购物车
        cart_result = cart_service.add_to_cart(
            user_id=user_id,
            product_id=1,
            quantity=2,
            ec_id=ec_id,
            project_id=project_id
        )
        self.assertTrue(cart_result.get('success', False) or 'msg' in cart_result)

        # 2. 获取购物车
        cart = cart_service.get_cart(user_id, ec_id, project_id)
        self.assertIn('items', cart)

        # 3. 添加订单留言
        note_result = order_enhance.add_order_note(
            order_id=1,
            user_id=user_id,
            note_type='user_question',
            content='集成测试留言'
        )
        self.assertIn('success', note_result)

    def test_complete_refund_flow(self):
        """测试完整退款流程"""
        from business_common.order_enhance_service import order_enhance

        # 1. 申请部分退款
        refund_result = order_enhance.partial_refund(
            order_id=1,
            user_id='test_user',
            refund_items=[
                {'product_id': 1, 'quantity': 1}
            ],
            reason='集成测试退款'
        )
        self.assertIn('success', refund_result)

        # 2. 获取订单留言
        notes = order_enhance.get_order_notes(
            order_id=1,
            user_id='test_user'
        )
        self.assertIn('success', notes)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestShoppingCart))
    suite.addTests(loader.loadTestsFromTestCase(TestOrderEnhancement))
    suite.addTests(loader.loadTestsFromTestCase(TestInventoryAlert))
    suite.addTests(loader.loadTestsFromTestCase(TestFAQService))
    suite.addTests(loader.loadTestsFromTestCase(TestPushService))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIVersioning))
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✓ 所有测试通过!")
    else:
        print("\n✗ 部分测试失败")
        if result.failures:
            print("\n失败详情:")
            for test, trace in result.failures:
                print(f"  - {test}: {trace[:200]}...")
        if result.errors:
            print("\n错误详情:")
            for test, trace in result.errors:
                print(f"  - {test}: {trace[:200]}...")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
