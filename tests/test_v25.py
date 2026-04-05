#!/usr/bin/env python3
"""
V25.0 自动化测试套件
测试范围: 积分商品管理、拼团活动管理、运营数据API
"""
import sys
import os
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestPointsMallService:
    """积分商品服务测试"""
    
    def test_points_goods_table_exists(self):
        """测试积分商品表是否存在"""
        from business_common import db
        
        result = db.get_one("""
            SELECT COUNT(*) as cnt 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'business_points_goods'
        """)
        assert result is not None
        assert result.get('cnt', 0) > 0, "积分商品表不存在"
    
    def test_points_exchanges_table_exists(self):
        """测试积分兑换记录表是否存在"""
        from business_common import db
        
        result = db.get_one("""
            SELECT COUNT(*) as cnt 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'business_points_exchanges'
        """)
        assert result is not None
        assert result.get('cnt', 0) > 0, "积分兑换记录表不存在"
    
    def test_points_goods_crud(self):
        """测试积分商品CRUD操作"""
        from business_common import db
        
        goods_name = f"测试积分商品_{int(time.time())}"
        
        # 创建
        db.execute("""
            INSERT INTO business_points_goods 
            (goods_name, category, points_price, stock, total_stock, status)
            VALUES (%s, 'gift', 100, 10, 10, 'active')
        """, [goods_name])
        
        # 查询
        goods = db.get_one("SELECT * FROM business_points_goods WHERE goods_name=%s", [goods_name])
        assert goods is not None, "商品创建失败"
        assert goods['points_price'] == 100, "积分价格错误"
        assert goods['status'] == 'active', "状态错误"
        
        # 更新
        db.execute("UPDATE business_points_goods SET points_price=200 WHERE goods_name=%s", [goods_name])
        goods = db.get_one("SELECT * FROM business_points_goods WHERE goods_name=%s", [goods_name])
        assert goods['points_price'] == 200, "积分价格更新失败"
        
        # 删除
        db.execute("UPDATE business_points_goods SET deleted=1 WHERE goods_name=%s", [goods_name])
        goods = db.get_one("SELECT * FROM business_points_goods WHERE goods_name=%s AND deleted=0", [goods_name])
        assert goods is None, "商品删除失败"
    
    def test_points_exchange_flow(self):
        """测试积分兑换完整流程"""
        from business_common import db
        
        exchange_no = f"PEX{int(time.time())}"
        user_id = 1
        
        # 创建兑换记录
        db.execute("""
            INSERT INTO business_points_exchanges 
            (exchange_no, user_id, user_name, goods_id, goods_name, points_price, total_points, status)
            VALUES (%s, %s, '测试用户', 1, '测试商品', 100, 100, 'paid')
        """, [exchange_no, user_id])
        
        # 查询记录
        exchange = db.get_one("SELECT * FROM business_points_exchanges WHERE exchange_no=%s", [exchange_no])
        assert exchange is not None, "兑换记录创建失败"
        assert exchange['status'] == 'paid', "状态错误"
        assert exchange['total_points'] == 100, "积分数量错误"
        
        # 更新状态
        db.execute("UPDATE business_points_exchanges SET status='shipped', shipped_by='admin' WHERE exchange_no=%s", [exchange_no])
        exchange = db.get_one("SELECT * FROM business_points_exchanges WHERE exchange_no=%s", [exchange_no])
        assert exchange['status'] == 'shipped', "状态更新失败"
        
        # 清理
        db.execute("UPDATE business_points_exchanges SET deleted=1 WHERE exchange_no=%s", [exchange_no])


class TestGroupBuyService:
    """拼团活动服务测试"""
    
    def test_group_activities_table_exists(self):
        """测试拼团活动表是否存在"""
        from business_common import db
        
        result = db.get_one("""
            SELECT COUNT(*) as cnt 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'business_group_activities'
        """)
        assert result is not None
        assert result.get('cnt', 0) > 0, "拼团活动表不存在"
    
    def test_group_orders_table_exists(self):
        """测试拼团订单表是否存在"""
        from business_common import db
        
        result = db.get_one("""
            SELECT COUNT(*) as cnt 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'business_group_orders'
        """)
        assert result is not None
        assert result.get('cnt', 0) > 0, "拼团订单表不存在"
    
    def test_group_activity_crud(self):
        """测试拼团活动CRUD操作"""
        from business_common import db
        
        activity_no = f"GRP{int(time.time())}"
        
        # 创建
        db.execute("""
            INSERT INTO business_group_activities 
            (activity_no, name, product_id, group_price, min_people, max_people, status)
            VALUES (%s, '测试拼团活动', 1, 29.9, 2, 10, 'pending')
        """, [activity_no])
        
        # 查询
        activity = db.get_one("SELECT * FROM business_group_activities WHERE activity_no=%s", [activity_no])
        assert activity is not None, "活动创建失败"
        assert activity['min_people'] == 2, "最小人数错误"
        assert activity['status'] == 'pending', "状态错误"
        
        # 启动活动
        db.execute("UPDATE business_group_activities SET status='ongoing' WHERE activity_no=%s", [activity_no])
        activity = db.get_one("SELECT * FROM business_group_activities WHERE activity_no=%s", [activity_no])
        assert activity['status'] == 'ongoing', "活动启动失败"
        
        # 清理
        db.execute("UPDATE business_group_activities SET deleted=1 WHERE activity_no=%s", [activity_no])
    
    def test_group_order_flow(self):
        """测试拼团订单流程"""
        from business_common import db
        
        order_no = f"GO{int(time.time())}"
        activity_no = f"GRP{int(time.time())}"
        
        # 创建活动
        db.execute("""
            INSERT INTO business_group_activities 
            (activity_no, name, product_id, group_price, min_people, status)
            VALUES (%s, '测试活动', 1, 29.9, 2, 'ongoing')
        """, [activity_no])
        
        # 创建订单
        db.execute("""
            INSERT INTO business_group_orders 
            (order_no, activity_no, product_id, group_price, user_id, user_name, status)
            VALUES (%s, %s, 1, 29.9, 1, '测试用户', 'pending')
        """, [order_no, activity_no])
        
        # 查询订单
        order = db.get_one("SELECT * FROM business_group_orders WHERE order_no=%s", [order_no])
        assert order is not None, "订单创建失败"
        assert order['status'] == 'pending', "状态错误"
        
        # 支付订单
        db.execute("UPDATE business_group_orders SET status='paid' WHERE order_no=%s", [order_no])
        order = db.get_one("SELECT * FROM business_group_orders WHERE order_no=%s", [order_no])
        assert order['status'] == 'paid', "支付状态更新失败"
        
        # 更新活动参与人数
        db.execute("""
            UPDATE business_group_activities 
            SET current_people = current_people + 1 
            WHERE activity_no=%s
        """, [activity_no])
        
        activity = db.get_one("SELECT * FROM business_group_activities WHERE activity_no=%s", [activity_no])
        assert activity['current_people'] == 1, "参与人数更新失败"
        
        # 清理
        db.execute("UPDATE business_group_orders SET deleted=1 WHERE order_no=%s", [order_no])
        db.execute("UPDATE business_group_activities SET deleted=1 WHERE activity_no=%s", [activity_no])


class TestAdminAPIRoutes:
    """管理端API路由测试"""
    
    def test_points_mall_routes_exist(self):
        """测试积分商品API路由是否存在"""
        import importlib.util
        spec = importlib.util.find_spec('flask')
        assert spec is not None, "Flask未安装"
        
        # 读取admin app.py检查路由定义
        admin_path = os.path.join(os.path.dirname(__file__), '..', 'business-admin', 'app.py')
        with open(admin_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键路由
        routes = [
            '/api/admin/points-mall/goods',
            '/api/admin/group-buy/activities'
        ]
        for route in routes:
            assert route in content, f"路由 {route} 不存在于admin app.py"


class TestDataBoardPage:
    """数据看板页面测试"""
    
    def test_data_board_html_exists(self):
        """测试数据看板页面是否存在"""
        admin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_board_path = os.path.join(admin_path, 'business-admin', 'data-board.html')
        assert os.path.exists(data_board_path), "数据看板页面不存在"
    
    def test_data_board_echarts_imported(self):
        """测试数据看板是否引入了ECharts"""
        admin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_board_path = os.path.join(admin_path, 'business-admin', 'data-board.html')
        with open(data_board_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'echarts' in content.lower(), "数据看板未引入ECharts"
    
    def test_points_mall_html_exists(self):
        """测试积分商品管理页面是否存在"""
        admin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        points_mall_path = os.path.join(admin_path, 'business-admin', 'points-mall.html')
        assert os.path.exists(points_mall_path), "积分商品管理页面不存在"
    
    def test_group_buy_html_exists(self):
        """测试拼团活动管理页面是否存在"""
        admin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        group_buy_path = os.path.join(admin_path, 'business-admin', 'group-buy.html')
        assert os.path.exists(group_buy_path), "拼团活动管理页面不存在"


class TestCodeQuality:
    """代码质量测试"""
    
    def test_admin_app_syntax(self):
        """测试admin app.py语法"""
        admin_path = os.path.join(os.path.dirname(__file__), '..', 'business-admin', 'app.py')
        
        # 尝试编译检查
        with open(admin_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        try:
            compile(code, admin_path, 'exec')
        except SyntaxError as e:
            pytest.fail(f"语法错误: {e}")
    
    def test_no_hardcoded_passwords(self):
        """测试无硬编码密码"""
        admin_path = os.path.join(os.path.dirname(__file__), '..', 'business-admin', 'app.py')
        with open(admin_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查常见的硬编码模式
        dangerous_patterns = [
            'password = "', 
            'password=\'',
            'DB_PASSWORD = "'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in content:
                # 排除注释和文档字符串中的内容
                lines = content.split('\n')
                for line in lines:
                    if pattern in line and not line.strip().startswith('#'):
                        if '"""' not in line and "'''" not in line:
                            # 检查是否是真正的密码设置
                            if 'os.environ' not in line and 'getenv' not in line:
                                pytest.fail(f"发现可能的硬编码密码: {line.strip()[:80]}")


class TestMigrationV25:
    """V25.0迁移测试"""
    
    def test_all_tables_created(self):
        """测试所有V25相关表已创建"""
        from business_common import db
        
        required_tables = [
            'business_points_goods',
            'business_points_exchanges',
            'business_group_activities',
            'business_group_orders'
        ]
        
        for table in required_tables:
            result = db.get_one("""
                SELECT COUNT(*) as cnt 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = %s
            """, [table])
            
            assert result is not None, f"表 {table} 查询失败"
            assert result.get('cnt', 0) > 0, f"表 {table} 不存在"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
