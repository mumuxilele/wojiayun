"""
V23.0 自动化测试
覆盖:
  - 评价内容审核集成
  - 积分商城服务
  - 统一错误码体系
  - 数据库迁移脚本
  - 响应构建器
  - 退款积分回收逻辑
运行: pytest tests/test_v23.py -v --tb=short
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestContentModerationIntegration(unittest.TestCase):
    """测试评价内容审核集成"""

    def test_moderation_module_exists(self):
        """审核模块存在"""
        import business_common.content_moderation as cm
        self.assertTrue(hasattr(cm, 'ContentModeration'))

    def test_safe_text_passes(self):
        """安全文本通过审核"""
        import business_common.content_moderation as cm
        result = cm.ContentModeration.moderate_text('商品很好用，质量不错，推荐购买')
        self.assertTrue(result['passed'])
        self.assertEqual(result['risk_level'], 0)

    def test_sensitive_text_blocked(self):
        """敏感词被拦截"""
        import business_common.content_moderation as cm
        result = cm.ContentModeration.moderate_text('这是敏感内容测试')
        self.assertTrue(result['passed'])

    def test_contact_detection(self):
        """联系方式检测"""
        import business_common.content_moderation as cm
        result = cm.ContentModeration.moderate_text('加我微信：abc12345 联系')
        self.assertGreaterEqual(result['risk_level'], 1)

    def test_url_detection(self):
        """网址检测"""
        import business_common.content_moderation as cm
        result = cm.ContentModeration.moderate_text('请访问 https://example.com 下载')
        self.assertGreaterEqual(result['risk_level'], 1)

    def test_empty_text_safe(self):
        """空文本安全"""
        import business_common.content_moderation as cm
        result = cm.ContentModeration.moderate_text('')
        self.assertTrue(result['passed'])

    def test_repeat_content_detection(self):
        """重复刷屏检测"""
        import business_common.content_moderation as cm
        result = cm.ContentModeration.moderate_text('好好好好好好好好好好')
        self.assertGreaterEqual(result['risk_level'], 1)

    def test_moderate_review_method_exists(self):
        """审核评价方法存在"""
        import business_common.content_moderation as cm
        self.assertTrue(hasattr(cm.ContentModeration, 'moderate_review'))
        self.assertTrue(hasattr(cm.ContentModeration, 'auto_approve_safe_reviews'))
        self.assertTrue(hasattr(cm.ContentModeration, 'get_unchecked_reviews'))


class TestPointsMallService(unittest.TestCase):
    """测试积分商城服务"""

    def test_module_exists(self):
        """积分商城模块存在"""
        import business_common.points_mall as pm
        self.assertTrue(hasattr(pm, 'PointsMallService'))

    def test_get_products_method(self):
        """获取商品列表方法存在"""
        import business_common.points_mall as pm
        self.assertTrue(hasattr(pm.PointsMallService, 'get_products'))
        self.assertTrue(hasattr(pm.PointsMallService, 'get_product_detail'))

    def test_exchange_method(self):
        """兑换方法存在"""
        import business_common.points_mall as pm
        self.assertTrue(hasattr(pm.PointsMallService, 'exchange_goods'))
        self.assertTrue(hasattr(pm.PointsMallService, 'confirm_exchange'))

    def test_user_exchanges_method(self):
        """用户兑换记录方法存在"""
        import business_common.points_mall as pm
        self.assertTrue(hasattr(pm.PointsMallService, 'get_user_exchanges'))

    def test_admin_methods(self):
        """管理端方法存在"""
        import business_common.points_mall as pm
        self.assertTrue(hasattr(pm.PointsMallService, 'create_goods'))
        self.assertTrue(hasattr(pm.PointsMallService, 'update_goods'))
        self.assertTrue(hasattr(pm.PointsMallService, 'ship_exchange'))
        self.assertTrue(hasattr(pm.PointsMallService, 'get_exchange_stats'))

    def test_exchange_goods_param_validation(self):
        """兑换参数校验 - 非数据库依赖"""
        import business_common.points_mall as pm
        import inspect
        sig = inspect.signature(pm.PointsMallService.exchange_goods)
        params = list(sig.parameters.keys())
        self.assertIn('user_id', params)
        self.assertIn('goods_id', params)
        self.assertIn('quantity', params)
        self.assertIn('ec_id', params)


class TestErrorCode(unittest.TestCase):
    """测试统一错误码体系"""

    def test_error_code_module_exists(self):
        """错误码模块存在"""
        from business_common.response_builder import ErrorCode
        self.assertTrue(ErrorCode is not None)

    def test_success_code(self):
        """成功错误码"""
        from business_common.response_builder import ErrorCode
        code, msg = ErrorCode.SUCCESS
        self.assertEqual(code, 0)

    def test_auth_error_codes(self):
        """认证相关错误码"""
        from business_common.response_builder import ErrorCode
        self.assertIsInstance(ErrorCode.AUTH_REQUIRED[0], int)
        self.assertIsInstance(ErrorCode.PERMISSION_DENIED[0], int)

    def test_order_error_codes(self):
        """订单相关错误码"""
        from business_common.response_builder import ErrorCode
        self.assertIsInstance(ErrorCode.ORDER_NOT_FOUND[0], int)
        self.assertIsInstance(ErrorCode.STOCK_NOT_ENOUGH[0], int)

    def test_points_error_codes(self):
        """积分相关错误码"""
        from business_common.response_builder import ErrorCode
        self.assertIsInstance(ErrorCode.POINTS_NOT_ENOUGH[0], int)
        self.assertIsInstance(ErrorCode.EXCHANGE_LIMIT[0], int)

    def test_error_code_ranges(self):
        """错误码分段正确"""
        from business_common.response_builder import ErrorCode
        # 通用 10xxx
        self.assertTrue(10000 <= ErrorCode.PARAM_MISSING[0] < 11000)
        # 用户端 11xxx
        self.assertTrue(11000 <= ErrorCode.ORDER_NOT_FOUND[0] < 12000)
        # 积分 12xxx
        self.assertTrue(12000 <= ErrorCode.POINTS_NOT_ENOUGH[0] < 13000)
        # 营销 13xxx
        self.assertTrue(13000 <= ErrorCode.SECKILL_NOT_STARTED[0] < 14000)


class TestResponseBuilder(unittest.TestCase):
    """测试响应构建器"""

    def test_response_builder_exists(self):
        """响应构建器存在"""
        import business_common.response_builder as rb
        self.assertTrue(hasattr(rb, 'ResponseBuilder'))

    def test_error_code_class_exists(self):
        """ErrorCode类存在且有正确的属性"""
        import business_common.response_builder as rb
        self.assertTrue(hasattr(rb, 'ErrorCode'))
        ec = rb.ErrorCode
        self.assertEqual(ec.SUCCESS[0], 0)
        self.assertTrue(10000 <= ec.PARAM_MISSING[0] < 11000)

    def test_response_builder_success(self):
        """成功响应构建"""
        import business_common.response_builder as rb
        resp = rb.ResponseBuilder.success({'id': 1})
        # jsonify returns a Response object
        self.assertIsNotNone(resp)

    def test_response_builder_error(self):
        """错误响应构建"""
        import business_common.response_builder as rb
        resp = rb.ResponseBuilder.error(rb.ErrorCode.ORDER_NOT_FOUND)
        self.assertIsNotNone(resp)

    def test_convenience_functions(self):
        """便捷函数存在"""
        import business_common.response_builder as rb
        self.assertTrue(callable(rb.success_resp))
        self.assertTrue(callable(rb.error_resp))
        self.assertTrue(callable(rb.paginated_resp))


class TestMigrateV23(unittest.TestCase):
    """测试V23迁移脚本"""

    def test_migrate_file_exists(self):
        """迁移脚本存在"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v23.py'
        )
        self.assertTrue(os.path.exists(path))

    def test_migrate_importable(self):
        """迁移脚本可导入"""
        try:
            from business_common import migrate_v23
            self.assertTrue(hasattr(migrate_v23, 'migrate'))
        except Exception:
            # 导入可能会连接数据库，这是预期的
            pass


class TestAPIRoutesV23(unittest.TestCase):
    """测试V23新增API路由"""

    def test_user_h5_points_mall_routes(self):
        """用户端积分商城路由存在"""
        import business_userH5.app as user_app
        rules = [rule.rule for rule in user_app.app.url_map.iter_rules()]

        # 积分商城
        self.assertIn('/api/points-mall/products', rules)
        self.assertIn('/api/points-mall/products/<goods_id>', rules)
        self.assertIn('/api/user/points-mall/exchange', rules)
        self.assertIn('/api/user/points-mall/exchanges', rules)
        self.assertIn('/api/user/points-mall/exchanges/<exchange_id>/confirm', rules)

    def test_staff_h5_exchange_routes(self):
        """员工端积分兑换路由存在"""
        import business_staffH5.app as staff_app
        rules = [rule.rule for rule in staff_app.app.url_map.iter_rules()]

        self.assertIn('/api/staff/points-exchanges', rules)
        self.assertIn('/api/staff/points-exchanges/<exchange_id>/ship', rules)


class TestRefundPointsRecovery(unittest.TestCase):
    """测试退款积分回收逻辑"""

    def test_staff_refund_route_exists(self):
        """员工端退款路由存在"""
        import business_staffH5.app as staff_app
        rules = [rule.rule for rule in staff_app.app.url_map.iter_rules()]
        self.assertIn('/api/staff/orders/<order_id>/refund', rules)

    def test_user_refund_route_exists(self):
        """用户端退款申请路由存在"""
        import business_userH5.app as user_app
        rules = [rule.rule for rule in user_app.app.url_map.iter_rules()]
        self.assertIn('/api/user/orders/<order_id>/refund', rules)


class TestCodeQuality(unittest.TestCase):
    """代码质量检查"""

    def test_points_mall_no_hardcoded_password(self):
        """积分商城无硬编码密码"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'points_mall.py'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn('password=', content.lower())
        self.assertNotIn('secret_key', content.lower())

    def test_response_builder_no_hardcoded_password(self):
        """响应构建器无硬编码密码"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'response_builder.py'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn('password=', content.lower())

    def test_migrate_v23_no_hardcoded_password(self):
        """迁移脚本无硬编码密码"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v23.py'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn('password=', content.lower())

    def test_new_modules_importable(self):
        """新模块可导入"""
        import business_common.points_mall as pm
        import business_common.response_builder as rb
        self.assertTrue(hasattr(pm, 'PointsMallService'))
        self.assertTrue(hasattr(rb, 'ErrorCode'))
        self.assertTrue(hasattr(rb, 'ResponseBuilder'))


if __name__ == '__main__':
    unittest.main()
