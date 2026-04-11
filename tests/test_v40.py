"""
V40.0 自动化测试套件

测试覆盖：
1. 购物车智能推荐服务 (CartRecommendationService)
2. 会员生命周期管理服务 (MemberLifecycleService)
3. 用户行为追踪服务 (UserBehaviorService)

运行方式:
    cd tests
    python -m pytest test_v40.py -v
    python test_v40.py  # 直接运行
"""
import sys
import os
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCartRecommendationService(unittest.TestCase):
    """购物车智能推荐服务测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        try:
            from business_common.cart_recommendation_service import cart_recommendation_service
            cls.service = cart_recommendation_service
            cls.service_available = True
        except ImportError as e:
            print(f"[WARN] cart_recommendation_service 不可用: {e}")
            cls.service_available = False

    def test_service_exists(self):
        """测试服务是否存在"""
        if not self.service_available:
            self.skipTest("服务不可用")
        self.assertIsNotNone(self.service)

    def test_recommendation_types(self):
        """测试推荐类型定义"""
        if not self.service_available:
            self.skipTest("服务不可用")
        self.assertIn('cart', self.service.RECOMMEND_TYPES)
        self.assertIn('viewed', self.service.RECOMMEND_TYPES)
        self.assertIn('similar', self.service.RECOMMEND_TYPES)
        self.assertIn('purchased', self.service.RECOMMEND_TYPES)

    def test_get_recommendations_returns_list(self):
        """测试推荐结果返回列表"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_recommendations(
            user_id=999999,
            ec_id=1,
            project_id=1,
            recommend_type='cart'
        )
        self.assertIsInstance(result, list)

    def test_get_recommendations_with_exclude(self):
        """测试排除特定商品的推荐"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_recommendations(
            user_id=999999,
            ec_id=1,
            project_id=1,
            recommend_type='similar',
            exclude_product_ids=[1, 2, 3]
        )
        self.assertIsInstance(result, list)
        product_ids = [r.get('product_id') for r in result]
        for pid in [1, 2, 3]:
            self.assertNotIn(pid, product_ids)

    def test_similar_recommendation(self):
        """测试相似商品推荐"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_recommendations(
            user_id=999999,
            ec_id=1,
            project_id=1,
            recommend_type='similar',
            product_id=1
        )
        self.assertIsInstance(result, list)

    def test_viewed_recommendation(self):
        """测试浏览历史推荐"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_recommendations(
            user_id=999999,
            ec_id=1,
            project_id=1,
            recommend_type='viewed'
        )
        self.assertIsInstance(result, list)

    def test_purchased_recommendation(self):
        """测试购买记录推荐"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_recommendations(
            user_id=999999,
            ec_id=1,
            project_id=1,
            recommend_type='purchased'
        )
        self.assertIsInstance(result, list)


class TestMemberLifecycleService(unittest.TestCase):
    """会员生命周期管理服务测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        try:
            from business_common.member_lifecycle_service import member_lifecycle_service
            cls.service = member_lifecycle_service
            cls.service_available = True
        except ImportError as e:
            print(f"[WARN] member_lifecycle_service 不可用: {e}")
            cls.service_available = False

    def test_service_exists(self):
        """测试服务是否存在"""
        if not self.service_available:
            self.skipTest("服务不可用")
        self.assertIsNotNone(self.service)

    def test_stage_constants_defined(self):
        """测试阶段常量定义"""
        if not self.service_available:
            self.skipTest("服务不可用")
        self.assertEqual(self.service.STAGE_NEW_USER, 'new_user')
        self.assertEqual(self.service.STAGE_ACTIVE, 'active')
        self.assertEqual(self.service.STAGE_HOT, 'hot')
        self.assertEqual(self.service.STAGE_SLEEPING, 'sleeping')
        self.assertEqual(self.service.STAGE_CHURNING, 'churning')
        self.assertEqual(self.service.STAGE_CHURNED, 'churned')

    def test_stage_config_complete(self):
        """测试阶段配置完整性"""
        if not self.service_available:
            self.skipTest("服务不可用")
        for stage in [self.service.STAGE_NEW_USER, self.service.STAGE_ACTIVE,
                      self.service.STAGE_HOT, self.service.STAGE_SLEEPING,
                      self.service.STAGE_CHURNING, self.service.STAGE_CHURNED]:
            config = self.service.STAGE_CONFIG.get(stage)
            self.assertIsNotNone(config)
            self.assertIn('name', config)
            self.assertIn('color', config)
            self.assertIn('strategy', config)

    def test_get_member_stage_returns_dict(self):
        """测试获取会员阶段返回字典"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_member_stage(999999)
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('current_stage', result)

    def test_update_member_action(self):
        """测试更新会员行为"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.update_member_action(
            user_id=999999,
            action_type='browse',
            ec_id=1,
            project_id=1
        )
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)

    def test_execute_strategy_returns_result(self):
        """测试执行触达策略"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.execute_strategy(
            user_id=999999,
            strategy_code='test_strategy'
        )
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)

    def test_get_lifecycle_stats(self):
        """测试获取生命周期统计"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_lifecycle_stats(ec_id=1, project_id=1)
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get('success', False) or 'stage_distribution' in result)


class TestUserBehaviorService(unittest.TestCase):
    """用户行为追踪服务测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        try:
            from business_common.user_behavior_service import user_behavior_service
            cls.service = user_behavior_service
            cls.service_available = True
        except ImportError as e:
            print(f"[WARN] user_behavior_service 不可用: {e}")
            cls.service_available = False

    def test_service_exists(self):
        """测试服务是否存在"""
        if not self.service_available:
            self.skipTest("服务不可用")
        self.assertIsNotNone(self.service)

    def test_behavior_types_defined(self):
        """测试行为类型定义"""
        if not self.service_available:
            self.skipTest("服务不可用")
        self.assertIn('browse_product', self.service.BEHAVIOR_TYPES)
        self.assertIn('add_cart', self.service.BEHAVIOR_TYPES)
        self.assertIn('pay_order', self.service.BEHAVIOR_TYPES)
        self.assertIn('favorite', self.service.BEHAVIOR_TYPES)

    def test_track_behavior_returns_dict(self):
        """测试记录行为返回字典"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.track_behavior(
            user_id=999999,
            behavior_type='browse_product',
            target_type='product',
            target_id=1,
            target_name='测试商品'
        )
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)

    def test_track_product_view(self):
        """测试快捷方法：记录商品浏览"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.track_product_view(
            user_id=999999,
            product_id=1,
            product_name='测试商品'
        )
        self.assertIsInstance(result, dict)

    def test_track_add_cart(self):
        """测试快捷方法：记录加购"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.track_add_cart(
            user_id=999999,
            product_id=1,
            product_name='测试商品',
            quantity=2
        )
        self.assertIsInstance(result, dict)

    def test_track_favorite(self):
        """测试快捷方法：记录收藏"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.track_favorite(
            user_id=999999,
            product_id=1,
            product_name='测试商品',
            action='add'
        )
        self.assertIsInstance(result, dict)

    def test_track_order(self):
        """测试快捷方法：记录订单行为"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.track_order(
            user_id=999999,
            order_id=1,
            order_no='TEST20260406001',
            behavior_type='pay_order',
            amount=99.9
        )
        self.assertIsInstance(result, dict)

    def test_get_user_profile(self):
        """测试获取用户画像"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_user_profile(999999)
        self.assertIsInstance(result, dict)

    def test_get_recent_behaviors(self):
        """测试获取最近行为"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_recent_behaviors(user_id=999999, days=7)
        self.assertIsInstance(result, list)

    def test_get_behavior_stats(self):
        """测试获取行为统计"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_behavior_stats(user_id=999999, days=30)
        self.assertIsInstance(result, dict)

    def test_get_funnel_analysis(self):
        """测试获取漏斗分析"""
        if not self.service_available:
            self.skipTest("服务不可用")
        result = self.service.get_funnel_analysis(ec_id=1, project_id=1, days=30)
        self.assertIsInstance(result, dict)


class TestV40Integration(unittest.TestCase):
    """V40.0 集成测试"""

    def test_all_services_importable(self):
        """测试所有V40.0服务可以正常导入"""
        services = [
            'business_common.cart_recommendation_service',
            'business_common.member_lifecycle_service',
            'business_common.user_behavior_service'
        ]

        for service_path in services:
            try:
                __import__(service_path)
            except ImportError as e:
                self.fail(f"无法导入 {service_path}: {e}")

    def test_migration_v40_exists(self):
        """测试V40.0迁移脚本存在"""
        migration_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common',
            'migrate_v40.py'
        )
        self.assertTrue(os.path.exists(migration_path))


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("V40.0 自动化测试套件")
    print("=" * 60)
    print()

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestCartRecommendationService))
    suite.addTests(loader.loadTestsFromTestCase(TestMemberLifecycleService))
    suite.addTests(loader.loadTestsFromTestCase(TestUserBehaviorService))
    suite.addTests(loader.loadTestsFromTestCase(TestV40Integration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出摘要
    print()
    print("=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"运行: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
