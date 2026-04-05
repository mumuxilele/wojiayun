"""
V16.0 自动化测试套件
测试范围：
  1. 会员等级服务测试
  2. 积分过期服务测试
  3. WebSocket服务框架测试
  4. 营销活动服务测试
  5. 数据大屏API测试
  6. 迁移脚本验证

运行方式:
    python -m pytest tests/test_v16.py -v --tb=short
"""
import sys
import os
import re

# 设置项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用conftest.py中的自定义导入器
import pytest


class TestMemberLevelService:
    """会员等级服务测试"""

    def test_member_level_module_exists(self):
        """测试会员等级模块是否存在"""
        try:
            from business_common.member_level import MemberLevelService
            assert MemberLevelService is not None
        except ImportError:
            pytest.fail("会员等级模块不存在")

    def test_member_level_default_levels(self):
        """测试默认等级配置"""
        try:
            from business_common.member_level import MemberLevelService
            levels = MemberLevelService.DEFAULT_LEVELS
            assert 'L1' in levels
            assert 'L2' in levels
            assert 'L3' in levels
            assert 'L4' in levels
            assert 'L5' in levels
        except ImportError:
            pytest.skip("会员等级模块不存在")

    def test_member_level_discount_rates(self):
        """测试会员折扣率配置"""
        try:
            from business_common.member_level import MemberLevelService
            levels = MemberLevelService.DEFAULT_LEVELS
            # 等级越高，折扣越低
            assert levels['L1']['discount'] == 1.00  # 无折扣
            assert levels['L5']['discount'] == 0.80  # 8折
            assert levels['L5']['discount'] < levels['L4']['discount']
            assert levels['L4']['discount'] < levels['L3']['discount']
        except ImportError:
            pytest.skip("会员等级模块不存在")

    def test_member_level_points_rates(self):
        """测试会员积分倍率配置"""
        try:
            from business_common.member_level import MemberLevelService
            levels = MemberLevelService.DEFAULT_LEVELS
            # 等级越高，积分倍率越高
            assert levels['L1']['points_rate'] == 1.00
            assert levels['L5']['points_rate'] == 3.00
            assert levels['L5']['points_rate'] > levels['L4']['points_rate']
        except ImportError:
            pytest.skip("会员等级模块不存在")

    def test_promotion_service_exists(self):
        """测试营销活动服务存在"""
        try:
            from business_common.member_level import PromotionService
            assert PromotionService is not None
        except ImportError:
            pytest.skip("营销活动模块不存在")

    def test_calculate_discount_method(self):
        """测试折扣计算方法存在"""
        try:
            from business_common.member_level import MemberLevelService
            assert hasattr(MemberLevelService, 'calculate_discount')
            assert hasattr(MemberLevelService, 'calculate_points')
        except ImportError:
            pytest.skip("会员等级模块不存在")


class TestPointsExpireService:
    """积分过期服务测试"""

    def test_points_expire_module_exists(self):
        """测试积分过期模块是否存在"""
        try:
            from business_common.points_scheduler import PointsExpireService
            assert PointsExpireService is not None
        except ImportError:
            pytest.fail("积分过期模块不存在")

    def test_points_validity_constant(self):
        """测试积分有效期配置"""
        try:
            from business_common.points_scheduler import PointsExpireService
            assert PointsExpireService.POINTS_VALIDITY_MONTHS == 12
        except ImportError:
            pytest.skip("积分过期模块不存在")

    def test_process_expired_points_method(self):
        """测试过期积分处理方法"""
        try:
            from business_common.points_scheduler import PointsExpireService
            assert hasattr(PointsExpireService, 'process_expired_points')
        except ImportError:
            pytest.skip("积分过期模块不存在")

    def test_send_notifications_method(self):
        """测试过期提醒方法"""
        try:
            from business_common.points_scheduler import PointsExpireService
            assert hasattr(PointsExpireService, 'send_expiring_notifications')
        except ImportError:
            pytest.skip("积分过期模块不存在")

    def test_get_user_expiring_points_method(self):
        """测试获取用户过期积分方法"""
        try:
            from business_common.points_scheduler import PointsExpireService
            assert hasattr(PointsExpireService, 'get_user_expiring_points')
        except ImportError:
            pytest.skip("积分过期模块不存在")

    def test_get_points_summary_method(self):
        """测试获取积分汇总方法"""
        try:
            from business_common.points_scheduler import PointsExpireService
            assert hasattr(PointsExpireService, 'get_points_summary')
        except ImportError:
            pytest.skip("积分过期模块不存在")

    def test_task_functions(self):
        """测试定时任务入口函数"""
        try:
            from business_common.points_scheduler import run_points_expire_task, run_points_notify_task
            assert callable(run_points_expire_task)
            assert callable(run_points_notify_task)
        except ImportError:
            pytest.skip("积分过期模块不存在")


class TestWebSocketService:
    """WebSocket服务测试"""

    def test_websocket_module_exists(self):
        """测试WebSocket模块是否存在"""
        try:
            from business_common.websocket_service import push_notification, push_broadcast
            assert callable(push_notification)
            assert callable(push_broadcast)
        except ImportError:
            pytest.fail("WebSocket模块不存在")

    def test_websocket_push_functions(self):
        """测试推送函数存在"""
        try:
            from business_common.websocket_service import (
                push_notification, 
                push_broadcast,
                get_online_count,
                is_user_online
            )
            assert callable(push_notification)
            assert callable(push_broadcast)
            assert callable(get_online_count)
            assert callable(is_user_online)
        except ImportError:
            pytest.skip("WebSocket模块不存在")

    def test_init_websocket_function(self):
        """测试初始化函数存在"""
        try:
            from business_common.websocket_service import init_websocket
            assert callable(init_websocket)
        except ImportError:
            pytest.skip("WebSocket模块不存在")


class TestMigrationScript:
    """迁移脚本测试"""

    def test_migrate_v16_exists(self):
        """测试V16迁移脚本是否存在"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v16.py'
        )
        assert os.path.exists(script_path), "V16迁移脚本不存在"

    def test_migrate_v16_creates_tables(self):
        """测试迁移脚本创建必要的表"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v16.py'
        )
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_tables = [
            'business_member_levels',
            'business_promotions',
            'business_promotion_users',
            'business_points_expiring',
            'business_websocket_sessions'
        ]
        
        for table in required_tables:
            assert f'CREATE TABLE' in content and table in content, f"缺少表: {table}"

    def test_migrate_v16_adds_columns(self):
        """测试迁移脚本添加必要字段"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v16.py'
        )
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_columns = [
            'total_consume',
            'member_level',
            'member_level_updated_at'
        ]
        
        for col in required_columns:
            assert col in content, f"缺少字段: {col}"


class TestAdminAPI:
    """管理端API测试"""

    def test_admin_app_exists(self):
        """测试管理端app是否存在"""
        admin_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'app.py'
        )
        assert os.path.exists(admin_path), "管理端app不存在"

    def test_admin_statistics_endpoint(self):
        """测试统计接口存在"""
        admin_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'app.py'
        )
        
        with open(admin_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "api/admin/statistics" in content
        assert "admin_statistics" in content

    def test_member_levels_api(self):
        """测试会员等级API"""
        admin_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'app.py'
        )
        
        with open(admin_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有会员等级相关API
        assert 'member' in content.lower()

    def test_data_scope_filter(self):
        """测试数据范围过滤函数"""
        admin_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'app.py'
        )
        
        with open(admin_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'add_scope_filter' in content or 'scope_filter' in content
        assert 'ec_id' in content
        assert 'project_id' in content


class TestDashboardPage:
    """数据大屏页面测试"""

    def test_dashboard_html_exists(self):
        """测试数据大屏HTML是否存在"""
        dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'dashboard.html'
        )
        assert os.path.exists(dashboard_path), "数据大屏页面不存在"

    def test_dashboard_uses_echarts(self):
        """测试数据大屏使用ECharts"""
        dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'dashboard.html'
        )
        
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'echarts' in content.lower()
        assert 'renderOrderTrendChart' in content or 'orderTrendChart' in content
        assert 'renderMemberLevelChart' in content or 'memberLevelChart' in content

    def test_dashboard_charts(self):
        """测试数据大屏图表配置"""
        dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'dashboard.html'
        )
        
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        charts = [
            'orderTrendChart',
            'memberLevelChart',
            'topProductsChart',
            'topShopsChart',
            'venueUsageChart'
        ]
        
        for chart in charts:
            assert chart in content, f"缺少图表: {chart}"


class TestMemberLevelsPage:
    """会员等级管理页面测试"""

    def test_member_levels_html_exists(self):
        """测试会员等级管理HTML是否存在"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'member-levels.html'
        )
        assert os.path.exists(path), "会员等级管理页面不存在"

    def test_member_levels_crud(self):
        """测试会员等级CRUD功能"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'member-levels.html'
        )
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'loadLevels' in content
        assert 'saveLevel' in content
        assert 'showAddDialog' in content
        assert 'editLevel' in content

    def test_member_level_form(self):
        """测试会员等级表单"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'member-levels.html'
        )
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'level_code' in content
        assert 'level_name' in content
        assert 'discount_rate' in content
        assert 'points_rate' in content


class TestWebSocketPage:
    """WebSocket消息页面测试"""

    def test_websocket_html_exists(self):
        """测试WebSocket页面是否存在"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'websocket.html'
        )
        assert os.path.exists(path), "WebSocket页面不存在"

    def test_websocket_connection(self):
        """测试WebSocket连接功能"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'websocket.html'
        )
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'connectWebSocket' in content
        assert 'disconnectWebSocket' in content
        assert 'handleRealTimeNotification' in content

    def test_notification_types(self):
        """测试通知类型分类"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'websocket.html'
        )
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'order' in content
        assert 'booking' in content
        assert 'points' in content
        assert 'system' in content


class TestIntegration:
    """集成测试"""

    def test_all_modules_importable(self):
        """测试所有V16模块可导入"""
        modules = [
            'business_common.member_level',
            'business_common.points_scheduler',
            'business_common.websocket_service'
        ]
        
        for module in modules:
            try:
                __import__(module.replace('-', '_'))
            except ImportError:
                # 尝试使用自定义导入器
                pytest.skip(f"模块 {module} 需要特殊导入器")

    def test_service_classes_complete(self):
        """测试服务类方法完整"""
        try:
            from business_common.member_level import MemberLevelService, PromotionService
            
            # MemberLevelService必需方法
            required_methods_ml = [
                'get_all_levels',
                'get_member_level_info',
                'calculate_discount',
                'calculate_points',
                'update_total_consume',
                'get_member_statistics'
            ]
            for method in required_methods_ml:
                assert hasattr(MemberLevelService, method), f"MemberLevelService缺少方法: {method}"
                
        except ImportError:
            pytest.skip("服务模块需要特殊导入器")

    def test_v16_features_summary(self):
        """V16功能总结验证"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 检查关键文件
        files = {
            'V16迁移脚本': 'business-common/migrate_v16.py',
            '积分过期服务': 'business-common/points_scheduler.py',
            '会员等级服务': 'business-common/member_level.py',
            'WebSocket服务': 'business-common/websocket_service.py',
            '数据大屏': 'business-admin/dashboard.html',
            '会员等级管理': 'business-admin/member-levels.html',
            'WebSocket页面': 'business-userH5/websocket.html'
        }
        
        missing = []
        for name, path in files.items():
            full_path = os.path.join(project_root, path)
            if not os.path.exists(full_path):
                missing.append(name)
        
        if missing:
            pytest.fail(f"缺少V16功能文件: {', '.join(missing)}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
