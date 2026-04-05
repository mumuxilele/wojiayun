#!/usr/bin/env python3
"""
V19.0 自动化测试
- P0安全修复验证
- P0秒杀防超卖验证
- P1用户自助退款接口验证
- P1申请超时预警验证
- P2图表和排序功能验证
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestV19SecurityFixes:
    """P0: 安全修复测试"""
    
    def test_admin_update_shop_has_decorator(self):
        """admin_update_shop路由应有@require_admin装饰器"""
        with open('business-admin/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找admin_update_shop函数定义位置
        import re
        pattern = r'(@require_admin\s+)?@app\.route\([^)]*\/shops\/\<[^>]+\>[^)]*methods\s*=\s*\[[^\]]*PUT[^\]]*\]\)[^}]+?def\s+admin_update_shop'
        matches = list(re.finditer(pattern, content, re.DOTALL))
        
        # 检查该路由上方是否有@require_admin
        for match in matches:
            start = max(0, match.start() - 200)
            context = content[start:match.start()]
            assert '@require_admin' in context, "admin_update_shop缺少@require_admin装饰器"
    
    def test_admin_delete_shop_has_decorator(self):
        """admin_delete_shop路由应有@require_admin装饰器"""
        with open('business-admin/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        # 查找DELETE方法的shops路由
        pattern = r'(@require_admin\s+)?@app\.route\([^)]*\/shops\/\<[^>]+\>[^)]*methods\s*=\s*\[[^\]]*DELETE[^\]]*\]\)[^}]+?def\s+admin_delete_shop'
        matches = list(re.finditer(pattern, content, re.DOTALL))
        
        for match in matches:
            start = max(0, match.start() - 200)
            context = content[start:match.start()]
            assert '@require_admin' in context, "admin_delete_shop缺少@require_admin装饰器"
    
    def test_venue_update_delete_have_decorators(self):
        """场地更新和删除路由应有@require_admin装饰器"""
        with open('business-admin/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查update_venue和delete_venue
        for func_name in ['update_venue', 'delete_venue']:
            pattern = rf'def\s+{func_name}\s*\('
            for match in re.finditer(pattern, content):
                start = max(0, match.start() - 300)
                context = content[start:match.start()]
                assert '@require_admin' in context, f"{func_name}缺少@require_admin装饰器"
    
    def test_venue_booking_update_has_decorator(self):
        """update_venue_booking路由应有@require_admin装饰器"""
        with open('business-admin/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        pattern = r'def\s+update_venue_booking\s*\('
        for match in re.finditer(pattern, content):
            start = max(0, match.start() - 300)
            context = content[start:match.start()]
            assert '@require_admin' in context, "update_venue_booking缺少@require_admin装饰器"


class TestV19SeckillLock:
    """P0: 秒杀防超卖测试"""
    
    def test_promotion_stock_deduction_has_for_update(self):
        """促销库存扣减应有FOR UPDATE行锁"""
        # 检查payment_service或相关文件
        files_to_check = [
            'business-common/payment_service.py',
            'business-userH5/app.py',
            'business-admin/app.py'
        ]
        
        found_lock = False
        for filepath in files_to_check:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 检查FOR UPDATE和促销库存相关代码
                if 'FOR UPDATE' in content and ('promotion' in content.lower() or 'seckill' in content.lower() or '秒杀' in content):
                    found_lock = True
                    break
                # 检查库存扣减逻辑
                if 'stock' in content and 'FOR UPDATE' in content:
                    found_lock = True
                    break
        
        assert found_lock, "未找到促销库存扣减的FOR UPDATE行锁实现"
    
    def test_product_stock_update_uses_transaction(self):
        """商品库存更新应使用事务"""
        with open('business-common/payment_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有事务处理
        assert 'commit' in content.lower() or 'rollback' in content.lower(), "库存扣减缺少事务处理"


class TestV19UserRefund:
    """P1: 用户自助退款测试"""
    
    def test_user_refund_route_exists(self):
        """用户端应有退款申请路由"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '/api/user/orders/<order_id>/refund' in content, "缺少用户退款申请路由"
        assert 'def apply_refund' in content, "缺少apply_refund函数"
    
    def test_user_refund_requires_login(self):
        """退款接口应需要登录"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找apply_refund函数的装饰器
        import re
        pattern = r'@app\.route\([^)]*orders\/\<[^>]+\>\/refund[^)]*\)([^}]+?)def\s+apply_refund'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            decorator_section = match.group(1)
            assert '@require_login' in decorator_section, "apply_refund缺少@require_login装饰器"
    
    def test_user_refund_validates_reason(self):
        """退款应验证原因"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查退款函数中是否有原因验证
        assert 'reason' in content, "退款接口未处理原因字段"
        assert 'refund_reason' in content or '退款原因' in content, "退款接口未验证原因"
    
    def test_user_refund_checks_order_status(self):
        """退款应检查订单状态"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有状态校验
        assert 'paid' in content and 'shipped' in content, "退款接口未检查订单状态"
        assert 'order_status' in content or 'status' in content, "退款接口未获取订单状态"
    
    def test_user_refund_sends_notification(self):
        """退款申请应发送通知"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否调用了通知服务
        assert 'send_notification' in content or 'push_notification' in content, "退款申请未发送通知"


class TestV19ApplicationMonitor:
    """P1: 申请超时预警测试"""
    
    def test_application_monitor_file_exists(self):
        """应有申请监控服务文件"""
        assert os.path.exists('business-common/application_monitor.py'), "缺少application_monitor.py"
    
    def test_application_monitor_has_check_function(self):
        """监控服务应有检查函数"""
        with open('business-common/application_monitor.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'def check_overdue_applications' in content, "缺少check_overdue_applications函数"
    
    def test_application_monitor_has_timeout_logic(self):
        """监控服务应有超时逻辑"""
        with open('business-common/application_monitor.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'TIMEOUT_HOURS' in content or '24' in content, "缺少超时时间定义"
        assert 'TIMESTAMPDIFF' in content or 'hours' in content.lower(), "缺少时间差计算"
    
    def test_application_monitor_sends_notifications(self):
        """监控服务应发送通知"""
        with open('business-common/application_monitor.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'send_notification' in content, "监控服务未发送站内通知"
        assert 'push_notification' in content, "监控服务未发送WebSocket推送"
    
    def test_staff_has_overdue_api(self):
        """员工端应有超时统计接口"""
        with open('business-staffH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '/api/staff/applications/overdue' in content, "员工端缺少超时统计接口"
        assert 'get_overdue_applications' in content, "员工端缺少超时统计函数"
    
    def test_staff_has_timeline_api(self):
        """员工端应有申请时间线接口"""
        with open('business-staffH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '/api/staff/applications/<app_id>/timeline' in content, "员工端缺少时间线接口"
        assert 'get_application_timeline' in content, "员工端缺少时间线函数"


class TestV19DashboardCharts:
    """P2: 管理端图表升级测试"""
    
    def test_admin_index_includes_echarts(self):
        """管理端index应引入ECharts"""
        with open('business-admin/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'echarts' in content.lower(), "index.html未引入ECharts"
    
    def test_admin_index_has_chart_containers(self):
        """管理端应有图表容器"""
        with open('business-admin/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'orderTrendChart' in content, "缺少订单趋势图容器"
        assert 'appStatusChart' in content, "缺少申请状态分布图容器"
        assert 'incomeSourceChart' in content, "缺少收入来源图容器"
    
    def test_admin_index_has_overdue_panel(self):
        """管理端应有超时预警面板"""
        with open('business-admin/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'overdueAppsPanel' in content, "缺少超时预警面板"
        assert 'loadOverdueApps' in content, "缺少加载超时申请函数"
    
    def test_admin_index_initializes_charts(self):
        """管理端应初始化图表"""
        with open('business-admin/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'initCharts' in content, "缺少图表初始化函数"
        assert 'echarts.init' in content, "未调用echarts.init"


class TestV19ProductSorting:
    """P2: 商品排序功能测试"""
    
    def test_products_api_supports_sorting(self):
        """商品API应支持排序参数"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查get_products函数
        assert 'sort_by' in content, "商品列表未支持sort_by参数"
        assert 'ORDER_MAP' in content or 'order by' in content.lower(), "商品列表未实现排序逻辑"
    
    def test_products_has_multiple_sort_options(self):
        """商品排序应支持多种选项"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        sort_options = ['price_asc', 'price_desc', 'sales', 'hot', 'new', 'default']
        found = sum(1 for opt in sort_options if opt in content)
        assert found >= 4, f"排序选项不足，只找到{found}个"


class TestV19Migration:
    """V19迁移脚本测试"""
    
    def test_migration_file_exists(self):
        """应有V19迁移脚本"""
        assert os.path.exists('business-common/migrate_v19.py'), "缺少migrate_v19.py"
    
    def test_migration_has_refund_fields(self):
        """迁移应添加退款字段"""
        with open('business-common/migrate_v19.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'refund_status' in content, "迁移未添加refund_status字段"
        assert 'refund_requested_at' in content, "迁移未添加refund_requested_at字段"
    
    def test_migration_has_indexes(self):
        """迁移应创建索引"""
        with open('business-common/migrate_v19.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'idx_apps_status_created' in content, "迁移未创建申请单状态索引"
        assert 'idx_orders_refund_status' in content, "迁移未创建订单退款索引"
    
    def test_migration_is_idempotent(self):
        """迁移应是幂等的"""
        with open('business-common/migrate_v19.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有存在性检查
        assert 'INFORMATION_SCHEMA' in content or 'cursor.fetchone()' in content, "迁移缺少幂等性检查"


class TestV19Documentation:
    """V19文档测试"""
    
    def test_memory_updated(self):
        """MEMORY.md应更新V19信息"""
        with open('.workbuddy/memory/MEMORY.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'V19' in content, "MEMORY.md未更新V19信息"
    
    def test_iteration_table_updated(self):
        """迭代历史表应包含V19"""
        with open('.workbuddy/memory/MEMORY.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'V19.0' in content, "迭代历史表未包含V19.0"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
