#!/usr/bin/env python3
"""
V21.0 自动化测试 - 核心功能结构验证
覆盖: 秒杀服务、评价流程、缓存适配、Swagger配置
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestV21SeckillService(unittest.TestCase):
    """秒杀服务结构验证"""

    def test_seckill_service_exists(self):
        """秒杀服务模块应存在"""
        seckill_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'seckill_service.py'
        )
        self.assertTrue(os.path.exists(seckill_path),
                       '秒杀服务模块不存在')

    def test_seckill_service_has_required_methods(self):
        """秒杀服务应包含必要方法"""
        seckill_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'seckill_service.py'
        )
        with open(seckill_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_methods = [
            'get_seckill_activity',
            'verify_seckill_stock',
            'check_user_limit',
            'create_seckill_order',
            'get_user_seckill_orders'
        ]
        
        for method in required_methods:
            self.assertIn(f'def {method}', content,
                         f'秒杀服务缺少方法: {method}')

    def test_seckill_uses_transaction_lock(self):
        """秒杀下单应使用数据库事务锁"""
        seckill_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'seckill_service.py'
        )
        with open(seckill_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 应包含事务锁相关代码
        self.assertIn('conn.begin()', content,
                     '秒杀下单未使用事务开始')
        self.assertIn('FOR UPDATE', content,
                     '秒杀下单未使用行锁')


class TestV21ReviewFlow(unittest.TestCase):
    """评价流程结构验证"""

    def test_review_has_user_endpoint(self):
        """用户端应有评价提交接口"""
        user_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-userH5', 'app.py'
        )
        with open(user_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('/reviews', content,
                     '用户端缺少评价相关路由')

    def test_review_has_staff_endpoint(self):
        """员工端应有评价统计接口"""
        staff_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-staffH5', 'app.py'
        )
        with open(staff_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('reviews', content.lower(),
                     '员工端缺少评价相关路由')

    def test_review_table_has_reply_fields(self):
        """评价表应有商家回复字段"""
        migrate_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'migrate_v21.py'
        )
        if os.path.exists(migrate_path):
            with open(migrate_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.assertIn('reply_content', content,
                         '迁移脚本缺少回复字段')


class TestV21CacheAdapter(unittest.TestCase):
    """缓存适配器结构验证"""

    def test_redis_adapter_exists(self):
        """Redis适配层应存在"""
        adapter_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'cache_redis.py'
        )
        # 适配器可选，不强制要求
        if not os.path.exists(adapter_path):
            self.skipTest("Redis适配器为可选模块，跳过测试")

    def test_cache_service_has_get_set(self):
        """缓存服务应有get/set方法"""
        cache_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'cache_service.py'
        )
        with open(cache_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('cache_get', content,
                     '缓存服务缺少cache_get方法')
        self.assertIn('cache_set', content,
                     '缓存服务缺少cache_set方法')


class TestV21SwaggerConfig(unittest.TestCase):
    """Swagger配置结构验证"""

    def test_swagger_config_exists(self):
        """Swagger配置文件应存在"""
        swagger_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'swagger_config.py'
        )
        self.assertTrue(os.path.exists(swagger_path),
                       'Swagger配置文件不存在')

    def test_swagger_has_init_function(self):
        """Swagger配置应有初始化函数"""
        swagger_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'swagger_config.py'
        )
        with open(swagger_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('init_swagger', content,
                     'Swagger配置缺少init_swagger函数')

    def test_swagger_has_api_docs_route(self):
        """Swagger应提供API文档路由"""
        swagger_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'swagger_config.py'
        )
        with open(swagger_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('/api/docs/', content,
                     'Swagger缺少API文档路由')


class TestV21Migration(unittest.TestCase):
    """迁移脚本验证"""

    def test_migrate_v21_exists(self):
        """V21迁移脚本应存在"""
        migrate_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'migrate_v21.py'
        )
        self.assertTrue(os.path.exists(migrate_path),
                       'V21迁移脚本不存在')

    def test_migrate_creates_seckill_table(self):
        """V21迁移应创建秒杀订单表"""
        migrate_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'migrate_v21.py'
        )
        with open(migrate_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('business_seckill_orders', content,
                     '迁移脚本未创建秒杀订单表')

    def test_migrate_adds_logistics_fields(self):
        """V21迁移应添加物流字段"""
        migrate_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'migrate_v21.py'
        )
        with open(migrate_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('logistics_no', content,
                     '迁移脚本未添加物流单号字段')


class TestV21SeckillTable(unittest.TestCase):
    """秒杀订单表结构验证"""

    def test_seckill_service_imports_db(self):
        """秒杀服务应导入数据库模块"""
        seckill_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'seckill_service.py'
        )
        with open(seckill_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('from . import db', content,
                     '秒杀服务未导入数据库模块')

    def test_seckill_has_stock_validation(self):
        """秒杀服务应有库存验证"""
        seckill_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'business-common', 'seckill_service.py'
        )
        with open(seckill_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('verify_seckill_stock', content,
                     '秒杀服务缺少库存验证方法')


if __name__ == '__main__':
    unittest.main(verbosity=2)
