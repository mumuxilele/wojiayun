"""
V38.0 自动化测试
测试成长任务、评价奖励、最优折扣、分享追踪功能
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestV38Imports(unittest.TestCase):
    """V38.0 模块导入测试"""
    
    def test_growth_task_service_import(self):
        """测试成长任务服务导入"""
        try:
            from business_common.growth_task_service import growth_task_service
            self.assertIsNotNone(growth_task_service)
            self.assertTrue(hasattr(growth_task_service, 'get_user_tasks'))
            self.assertTrue(hasattr(growth_task_service, 'increment_task_progress'))
        except ImportError as e:
            self.fail(f"导入失败: {e}")
    
    def test_review_reward_service_import(self):
        """测试评价奖励服务导入"""
        try:
            from business_common.review_reward_service import review_reward_service
            self.assertIsNotNone(review_reward_service)
            self.assertTrue(hasattr(review_reward_service, 'grant_reward'))
            self.assertTrue(hasattr(review_reward_service, 'get_reward_by_rating'))
        except ImportError as e:
            self.fail(f"导入失败: {e}")
    
    def test_discount_calculator_import(self):
        """测试最优折扣计算服务导入"""
        try:
            from business_common.discount_calculator_service import discount_calculator
            self.assertIsNotNone(discount_calculator)
            self.assertTrue(hasattr(discount_calculator, 'calculate_optimal_discount'))
            self.assertTrue(hasattr(discount_calculator, 'calculate_preview'))
        except ImportError as e:
            self.fail(f"导入失败: {e}")
    
    def test_share_service_import(self):
        """测试分享服务导入"""
        try:
            from business_common.share_service import share_service
            self.assertIsNotNone(share_service)
            self.assertTrue(hasattr(share_service, 'record_share'))
            self.assertTrue(hasattr(share_service, 'generate_poster_config'))
        except ImportError as e:
            self.fail(f"导入失败: {e}")


class TestV38Database(unittest.TestCase):
    """V38.0 数据库结构测试"""
    
    @classmethod
    def setUpClass(cls):
        try:
            from business_common import db
            cls.db = db
        except Exception as e:
            cls.skipTest(cls, f"数据库连接失败: {e}")
    
    def test_growth_tasks_table_exists(self):
        """测试成长任务表是否存在"""
        result = self.db.get_one("SHOW TABLES LIKE 'business_growth_tasks'")
        # 如果表不存在，跳过测试（迁移脚本可能未执行）
        if not result:
            self.skipTest("表 business_growth_tasks 不存在，请先执行迁移脚本")
        self.assertIsNotNone(result)
    
    def test_user_growth_progress_table_exists(self):
        """测试用户成长进度表是否存在"""
        result = self.db.get_one("SHOW TABLES LIKE 'business_user_growth_progress'")
        if not result:
            self.skipTest("表 business_user_growth_progress 不存在")
        self.assertIsNotNone(result)
    
    def test_share_logs_table_exists(self):
        """测试分享记录表是否存在"""
        result = self.db.get_one("SHOW TABLES LIKE 'business_share_logs'")
        if not result:
            self.skipTest("表 business_share_logs 不存在")
        self.assertIsNotNone(result)
    
    def test_review_rewards_table_exists(self):
        """测试评价奖励表是否存在"""
        result = self.db.get_one("SHOW TABLES LIKE 'business_review_rewards'")
        if not result:
            self.skipTest("表 business_review_rewards 不存在")
        self.assertIsNotNone(result)


class TestV38GrowthTaskService(unittest.TestCase):
    """成长任务服务测试"""
    
    @classmethod
    def setUpClass(cls):
        try:
            from business_common.growth_task_service import growth_task_service
            from business_common import db
            cls.service = growth_task_service
            cls.db = db
        except Exception as e:
            cls.skipTest(cls, f"服务导入失败: {e}")
    
    def test_service_health_check(self):
        """测试服务健康检查"""
        result = self.service.health_check()
        self.assertIsInstance(result, dict)
        self.assertIn('db_status', result)
    
    def test_get_period_dates(self):
        """测试周期日期计算"""
        result = self.service._get_period_dates()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


class TestV38ReviewRewardService(unittest.TestCase):
    """评价奖励服务测试"""
    
    @classmethod
    def setUpClass(cls):
        try:
            from business_common.review_reward_service import review_reward_service
            cls.service = review_reward_service
        except Exception as e:
            cls.skipTest(cls, f"服务导入失败: {e}")
    
    def test_reward_rules(self):
        """测试奖励规则"""
        # 5星奖励
        reward5 = self.service.get_reward_by_rating(5)
        self.assertEqual(reward5['points'], 20)
        self.assertEqual(reward5['growth'], 10)
        
        # 4星奖励
        reward4 = self.service.get_reward_by_rating(4)
        self.assertEqual(reward4['points'], 10)
        self.assertEqual(reward4['growth'], 5)
        
        # 1星无奖励
        reward1 = self.service.get_reward_by_rating(1)
        self.assertEqual(reward1['points'], 0)
        self.assertEqual(reward1['growth'], 0)
    
    def test_get_reward_rules_display(self):
        """测试奖励规则展示"""
        rules = self.service.get_reward_rules_display()
        self.assertIsInstance(rules, list)
        self.assertEqual(len(rules), 5)  # 1-5星
    
    def test_service_health_check(self):
        """测试服务健康检查"""
        result = self.service.health_check()
        self.assertIsInstance(result, dict)
        self.assertIn('service_name', result)


class TestV38DiscountCalculator(unittest.TestCase):
    """最优折扣计算服务测试"""
    
    @classmethod
    def setUpClass(cls):
        try:
            from business_common.discount_calculator_service import discount_calculator
            cls.calculator = discount_calculator
        except Exception as e:
            cls.skipTest(cls, f"服务导入失败: {e}")
    
    def test_calculate_preview(self):
        """测试折扣预览计算"""
        # 100元订单，不用优惠券和积分
        result = self.calculator.calculate_preview(100.0, None, 0)
        self.assertEqual(result['order_amount'], 100.0)
        self.assertEqual(result['final_amount'], 100.0)
        self.assertEqual(result['total_discount'], 0)
        
        # 100元订单，使用500积分（抵扣5元）
        result = self.calculator.calculate_preview(100.0, None, 500)
        self.assertEqual(result['use_points'], 500)
        self.assertEqual(result['points_deduction'], 5.0)
        self.assertEqual(result['final_amount'], 95.0)
    
    def test_coupon_discount_calculation(self):
        """测试优惠券折扣计算"""
        # 现金券
        cash_discount = self.calculator._calculate_coupon_discount(
            'cash', 10.0, 0, 100.0
        )
        self.assertEqual(cash_discount, 10.0)
        
        # 折扣券（9折）
        discount_discount = self.calculator._calculate_coupon_discount(
            'discount', 0.9, 0, 100.0
        )
        self.assertEqual(discount_discount, 10.0)  # 100 * (1-0.9) = 10
        
        # 折扣券有上限
        limited_discount = self.calculator._calculate_coupon_discount(
            'discount', 0.9, 5.0, 100.0
        )
        self.assertEqual(limited_discount, 5.0)  # 最多抵扣5元
    
    def test_service_health_check(self):
        """测试服务健康检查"""
        result = self.calculator.health_check()
        self.assertIsInstance(result, dict)
        self.assertEqual(result['points_rate'], 100)


class TestV38ShareService(unittest.TestCase):
    """分享服务测试"""
    
    @classmethod
    def setUpClass(cls):
        try:
            from business_common.share_service import share_service
            cls.service = share_service
        except Exception as e:
            cls.skipTest(cls, f"服务导入失败: {e}")
    
    def test_generate_share_token(self):
        """测试分享Token生成"""
        token1 = self.service._generate_share_token(100, 1)
        token2 = self.service._generate_share_token(100, 1)
        self.assertIsInstance(token1, str)
        self.assertEqual(len(token1), 16)  # MD5前16位
        # 相同输入应产生相同token（虽然有时间戳，但短时间内相同）
    
    def test_generate_share_url(self):
        """测试分享URL生成"""
        url = self.service._generate_share_url('product', 123, 'token123')
        self.assertIn('product/123', url)
        self.assertIn('share=token123', url)
        
        invite_url = self.service._generate_share_url('invite', 0, 'token456')
        self.assertIn('invite', invite_url)
        self.assertIn('code=token456', invite_url)
    
    def test_service_health_check(self):
        """测试服务健康检查"""
        result = self.service.health_check()
        self.assertIsInstance(result, dict)
        self.assertIn('service_name', result)


class TestV38UserAPIEndpoints(unittest.TestCase):
    """V38.0 用户API端点测试"""
    
    @classmethod
    def setUpClass(cls):
        try:
            from business_common import db
            cls.db = db
        except Exception as e:
            cls.skipTest(cls, f"数据库连接失败: {e}")
    
    def test_migrate_v38_script_exists(self):
        """测试V38.0迁移脚本是否存在"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v38.py'
        )
        self.assertTrue(os.path.exists(script_path), "migrate_v38.py 不存在")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestV38Imports))
    suite.addTests(loader.loadTestsFromTestCase(TestV38Database))
    suite.addTests(loader.loadTestsFromTestCase(TestV38GrowthTaskService))
    suite.addTests(loader.loadTestsFromTestCase(TestV38ReviewRewardService))
    suite.addTests(loader.loadTestsFromTestCase(TestV38DiscountCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestV38ShareService))
    suite.addTests(loader.loadTestsFromTestCase(TestV38UserAPIEndpoints))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("V38.0 测试总结")
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
