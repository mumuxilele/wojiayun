"""
V39.0 自动化测试
覆盖会员成长任务接通、商品分享闭环、智能优惠推荐与支付后成长任务触发。
"""

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUSINESS_COMMON_DIR = os.path.join(PROJECT_ROOT, 'business-common')


def ensure_business_common_package():
    if 'business_common' in sys.modules:
        return
    pkg = types.ModuleType('business_common')
    pkg.__path__ = [BUSINESS_COMMON_DIR]
    pkg.__file__ = os.path.join(BUSINESS_COMMON_DIR, '__init__.py')
    sys.modules['business_common'] = pkg


ensure_business_common_package()


def import_attr_or_skip(module_path, attr_name):
    try:
        module = __import__(module_path, fromlist=[attr_name])
        return getattr(module, attr_name)
    except (ImportError, ModuleNotFoundError) as e:
        raise unittest.SkipTest(f"服务导入失败（环境依赖缺失）: {e}")


def read_text(*parts):

    path = os.path.join(PROJECT_ROOT, *parts)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()



class TestV39Imports(unittest.TestCase):
    """V39.0 关键模块导入测试"""

    def test_discount_calculator_import(self):
        discount_calculator = import_attr_or_skip(
            'business_common.discount_calculator_service',
            'discount_calculator'
        )
        self.assertIsNotNone(discount_calculator)
        self.assertTrue(hasattr(discount_calculator, 'calculate_optimal_discount'))
        self.assertTrue(hasattr(discount_calculator, 'calculate_preview'))

    def test_growth_task_service_import(self):
        growth_task_service = import_attr_or_skip(
            'business_common.growth_task_service',
            'growth_task_service'
        )
        self.assertIsNotNone(growth_task_service)
        self.assertTrue(hasattr(growth_task_service, 'on_order_completed'))
        self.assertTrue(hasattr(growth_task_service, 'on_review'))

    def test_share_service_import(self):
        share_service = import_attr_or_skip(
            'business_common.share_service',
            'share_service'
        )
        self.assertIsNotNone(share_service)
        self.assertTrue(hasattr(share_service, 'record_share'))
        self.assertTrue(hasattr(share_service, 'generate_poster_config'))



class TestV39FrontendContracts(unittest.TestCase):
    """V39.0 前端集成契约测试"""

    @classmethod
    def setUpClass(cls):
        cls.member_html = read_text('business-userH5', 'member.html')
        cls.product_detail_html = read_text('business-userH5', 'product_detail.html')
        cls.checkout_html = read_text('business-userH5', 'checkout.html')

    def test_member_page_loads_growth_tasks_api(self):
        self.assertIn("/api/user/growth/tasks", self.member_html)
        self.assertIn("function loadGrowthTasks()", self.member_html)
        self.assertIn("loadGrowthTasks();", self.member_html)
        self.assertIn("renderUpgradeTasks(m, growthTaskData)", self.member_html)

    def test_product_detail_wires_share_record_and_poster_api(self):
        self.assertIn("/api/user/share/record", self.product_detail_html)
        self.assertIn("/api/user/share/poster/config", self.product_detail_html)
        self.assertIn("async function shareProduct()", self.product_detail_html)
        self.assertIn("normalizeShareUrl", self.product_detail_html)

    def test_checkout_wires_optimal_discount_api(self):
        self.assertIn("/api/user/discount/optimal", self.checkout_html)
        self.assertIn("async function loadOptimalDiscount()", self.checkout_html)
        self.assertIn("function applyOptimalPlan()", self.checkout_html)
        self.assertIn("optimalDiscountSection", self.checkout_html)

    def test_checkout_supports_buy_now_qty_param(self):
        self.assertIn("params.get('quantity') || params.get('qty') || '1'", self.checkout_html)


class TestV39BackendContracts(unittest.TestCase):
    """V39.0 后端闭环契约测试"""

    @classmethod
    def setUpClass(cls):
        cls.user_app = read_text('business-userH5', 'app.py')
        cls.payment_service = read_text('business-common', 'payment_service.py')

    def test_review_creation_triggers_reward_and_growth_task(self):
        self.assertIn("review_reward_service.grant_reward", self.user_app)
        self.assertIn("growth_task_service.on_review", self.user_app)
        self.assertIn("评价提交成功", self.user_app)

    def test_share_poster_api_accepts_share_url(self):
        self.assertIn("request.args.get('share_url')", self.user_app)
        self.assertIn("share_url=share_url or None", self.user_app)

    def test_payment_success_triggers_order_growth_task(self):
        self.assertIn("growth_task_service.on_order_completed", self.payment_service)
        self.assertIn("订单成长任务触发失败", self.payment_service)
        self.assertIn("if pay_record.get('order_type') == 'order'", self.payment_service)


class TestV39ServiceLogic(unittest.TestCase):
    """V39.0 纯逻辑服务测试"""

    @classmethod
    def setUpClass(cls):
        cls.discount_calculator = import_attr_or_skip(
            'business_common.discount_calculator_service',
            'discount_calculator'
        )


    def test_calculate_preview_with_discount_coupon_and_points(self):
        coupon = {
            'coupon_type': 'discount',
            'discount_value': 0.9,
            'max_discount': 12,
        }
        result = self.discount_calculator.calculate_preview(100.0, coupon, 500)
        self.assertEqual(result['coupon_discount'], 10.0)
        self.assertEqual(result['points_deduction'], 5.0)
        self.assertEqual(result['final_amount'], 85.0)
        self.assertEqual(result['total_discount'], 15.0)

    def test_calculate_preview_limits_points_by_after_coupon_amount(self):
        coupon = {
            'coupon_type': 'cash',
            'discount_value': 10,
            'max_discount': 0,
        }
        result = self.discount_calculator.calculate_preview(100.0, coupon, 50000)
        self.assertEqual(result['coupon_discount'], 10.0)
        self.assertLessEqual(result['use_points'], 1800)
        self.assertEqual(result['final_amount'], 72.0)


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestV39Imports))
    suite.addTests(loader.loadTestsFromTestCase(TestV39FrontendContracts))
    suite.addTests(loader.loadTestsFromTestCase(TestV39BackendContracts))
    suite.addTests(loader.loadTestsFromTestCase(TestV39ServiceLogic))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print("V39.0 测试总结")
    print("=" * 60)
    print(f"测试用例: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
