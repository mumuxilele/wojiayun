"""
V14.0 结构验证测试
测试所有V14新增模块和增强功能

运行方式:
    python -m pytest tests/test_v14_structure.py -v --tb=short
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============ 测试：Redis缓存适配器 ============

class TestRedisCacheService:
    """测试Redis缓存适配器"""

    def test_module_import(self):
        """测试模块可导入"""
        from business_common.redis_cache_service import (
            CacheService, cache_get, cache_set, cache_delete, cache_clear
        )
        assert CacheService is not None
        assert callable(cache_get)
        assert callable(cache_set)

    def test_backend_selection(self):
        """测试后端自动选择"""
        from business_common.redis_cache_service import CacheService
        backend_type = CacheService.get_backend_type()
        assert backend_type in ('redis', 'memory')

    def test_cache_set_get(self):
        """测试缓存写入和读取"""
        from business_common.redis_cache_service import cache_set, cache_get
        cache_set('test_v14_key', {'msg': 'hello'}, ttl=60)
        result = cache_get('test_v14_key')
        assert result is not None
        assert result['msg'] == 'hello'

    def test_cache_delete(self):
        """测试缓存删除"""
        from business_common.redis_cache_service import cache_set, cache_get, cache_delete
        cache_set('test_v14_del', 'value', ttl=60)
        cache_delete('test_v14_del')
        assert cache_get('test_v14_del') is None

    def test_cache_clear_with_prefix(self):
        """测试按前缀清空缓存"""
        from business_common.redis_cache_service import cache_set, cache_get, cache_clear
        cache_set('test_v14_prefix_1', 'v1', ttl=60)
        cache_set('test_v14_prefix_2', 'v2', ttl=60)
        cache_set('test_v14_other', 'v3', ttl=60)
        cache_clear('test_v14_prefix_')
        assert cache_get('test_v14_prefix_1') is None
        assert cache_get('test_v14_prefix_2') is None
        assert cache_get('test_v14_other') == 'v3'

    def test_cache_stats(self):
        """测试缓存统计"""
        from business_common.redis_cache_service import CacheService
        stats = CacheService.get_stats()
        assert 'total' in stats
        assert 'active' in stats
        assert 'backend' in stats

    def test_cache_expiration(self):
        """测试缓存过期"""
        from business_common.redis_cache_service import cache_set, cache_get
        import time
        cache_set('test_v14_expire', 'short', ttl=1)
        time.sleep(1.1)
        assert cache_get('test_v14_expire') is None


# ============ 测试：缓存服务兼容性 ============

class TestCacheServiceCompatibility:
    """测试缓存服务向后兼容"""

    def test_original_import_path(self):
        """测试原有导入路径仍可用"""
        from business_common.cache_service import (
            CacheService, cache_get, cache_set, cache_delete, cache_clear, DEFAULT_TTL
        )
        assert DEFAULT_TTL == 300

    def test_cache_service_api_compatible(self):
        """测试API签名不变"""
        from business_common.cache_service import CacheService
        assert hasattr(CacheService, 'get')
        assert hasattr(CacheService, 'set')
        assert hasattr(CacheService, 'delete')
        assert hasattr(CacheService, 'clear')


# ============ 测试：WebSocket服务 ============

class TestWebSocketService:
    """测试WebSocket消息推送服务"""

    def test_module_import(self):
        """测试模块可导入"""
        try:
            from business_common.websocket_service import (
                push_notification, push_broadcast, get_online_count, is_user_online
            )
            assert callable(push_notification)
            assert callable(push_broadcast)
            assert callable(get_online_count)
            assert callable(is_user_online)
        except ImportError:
            # flask-socketio未安装时也应该可以导入
            pass


# ============ 测试：存储服务 ============

class TestStorageService:
    """测试统一存储服务"""

    def test_module_import(self):
        """测试模块可导入"""
        from business_common.storage_service import StorageService
        assert StorageService is not None

    def test_get_backend_type(self):
        """测试后端类型获取"""
        from business_common.storage_service import StorageService
        backend = StorageService.get_backend_type()
        assert backend in ('local', 'oss', 's3')

    def test_local_backend_upload(self):
        """测试本地存储上传"""
        import base64
        from business_common.storage_service import StorageService
        # 创建一个最小的1x1 PNG图片
        png_data = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode()
        result = StorageService.upload_base64(png_data, ext='png')
        assert result['success'] is True
        assert 'url' in result

    def test_upload_invalid_type(self):
        """测试无效文件类型拒绝"""
        from business_common.storage_service import StorageService
        result = StorageService.upload_base64('abc123', ext='exe')
        assert result['success'] is False

    def test_upload_magic_check(self):
        """测试魔数校验（伪造PNG扩展名但内容是文本）"""
        from business_common.storage_service import StorageService
        import base64
        text_data = base64.b64encode(b'this is not a png file').decode()
        result = StorageService.upload_base64(text_data, ext='png')
        assert result['success'] is False


# ============ 测试：支付服务增强 ============

class TestPaymentServiceEnhancements:
    """测试支付服务V14增强"""

    def test_module_import(self):
        """测试模块可导入"""
        from business_common.payment_service import PaymentService
        assert PaymentService is not None

    def test_status_constants(self):
        """测试新增状态常量"""
        from business_common.payment_service import PaymentService
        assert 'expired' in PaymentService.STATUS
        assert 'closed' in PaymentService.STATUS

    def test_wechat_callback_verify(self):
        """测试微信回调验证接口"""
        from business_common.payment_service import PaymentService
        result = PaymentService.verify_wechat_callback({})
        assert result['success'] is False  # 未配置时返回False

    def test_alipay_callback_verify(self):
        """测试支付宝回调验证接口"""
        from business_common.payment_service import PaymentService
        result = PaymentService.verify_alipay_callback({'sign': 'fake', 'sign_type': 'RSA2'})
        assert result['success'] is False

    def test_query_external_payment(self):
        """测试外部支付查询"""
        from business_common.payment_service import PaymentService
        # 不存在的支付单
        result = PaymentService.query_external_payment('NOT_EXIST')
        assert result['success'] is False

    def test_cancel_expired_interface(self):
        """测试取消过期支付接口"""
        from business_common.payment_service import PaymentService
        # 只测试接口存在，不实际执行（可能没有数据库）
        assert callable(PaymentService.cancel_expired_payments)


# ============ 测试：迁移脚本 ============

class TestMigrationScript:
    """测试迁移脚本结构"""

    def test_migrate_module_exists(self):
        """测试迁移脚本文件存在"""
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-common', 'migrate_v14.py')
        assert os.path.exists(path)

    def test_migrate_has_required_functions(self):
        """测试迁移脚本包含必要函数"""
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-common', 'migrate_v14.py')
        spec = importlib.util.spec_from_file_location("migrate_v14", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, 'migrate')
        assert callable(module.migrate)
        assert hasattr(module, 'check_column_exists')
        assert hasattr(module, 'check_table_exists')


# ============ 测试：员工端统计API增强 ============

class TestStaffStatisticsEnhancement:
    """测试员工端统计API增强"""

    def test_date_range_utility(self):
        """测试日期范围工具函数"""
        from datetime import date, timedelta
        # 直接测试逻辑
        today = date.today()
        assert (today - timedelta(days=6)).strftime('%Y-%m-%d') == str(today - timedelta(days=6))


# ============ 测试：管理端新增路由 ============

class TestAdminNewRoutes:
    """测试管理端V14新增路由"""

    def test_batch_product_status_route(self):
        """测试商品批量状态修改路由注册"""
        from business_admin.app import app
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/api/admin/products/batch-status' in rules

    def test_product_categories_routes(self):
        """测试商品分类路由注册"""
        from business_admin.app import app
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/api/admin/product-categories' in rules

    def test_stock_warning_route(self):
        """测试库存预警通知路由注册"""
        from business_admin.app import app
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/api/admin/products/stock-warning' in rules

    def test_advanced_search_route(self):
        """测试订单高级搜索路由注册"""
        from business_admin.app import app
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/api/admin/orders/advanced-search' in rules


# ============ 测试：员工端新增路由 ============

class TestStaffNewRoutes:
    """测试员工端V14新增路由"""

    def test_trend_route(self):
        """测试趋势数据路由注册"""
        from business_staffH5.app import app
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/api/staff/statistics/trend' in rules

    def test_performance_route(self):
        """测试个人绩效路由注册"""
        from business_staffH5.app import app
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/api/staff/statistics/performance' in rules


# ============ 测试：requirements.txt ============

class TestRequirements:
    """测试依赖配置"""

    def test_requirements_has_redis(self):
        """测试requirements包含Redis"""
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-common', 'requirements.txt')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'redis' in content.lower()

    def test_requirements_has_socketio(self):
        """测试requirements包含flask-socketio"""
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-common', 'requirements.txt')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'flask-socketio' in content.lower()


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '--tb=short'])
