"""
V17.0 自动化测试套件
测试范围：
  1. 健康检查服务测试
  2. 数据导出服务测试
  3. API文档生成测试
  4. 员工端数据隔离验证
  5. 员工端统计增强验证

运行方式:
    python -m pytest tests/test_v17.py -v --tb=short
"""
import sys
import os
import re

# 设置项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestHealthCheckService:
    """健康检查服务测试"""

    def test_health_check_module_exists(self):
        """测试健康检查模块是否存在"""
        try:
            from business_common.health_check import HealthCheck
            assert HealthCheck is not None
        except ImportError:
            pytest.fail("健康检查模块不存在")

    def test_health_check_class_methods(self):
        """测试健康检查类方法"""
        try:
            from business_common.health_check import HealthCheck
            checker = HealthCheck()
            
            # 验证必要方法存在
            assert hasattr(checker, 'check_database')
            assert hasattr(checker, 'check_cache')
            assert hasattr(checker, 'check_disk_space')
            assert hasattr(checker, 'check_memory')
            assert hasattr(checker, 'check_cpu')
            assert hasattr(checker, 'check_process')
            assert hasattr(checker, 'run_all_checks')
            assert hasattr(checker, 'get_summary')
        except ImportError:
            pytest.skip("健康检查模块不存在")

    def test_health_check_result_structure(self):
        """测试健康检查返回结构"""
        try:
            from business_common.health_check import HealthCheck
            checker = HealthCheck()
            result = checker.get_summary()
            
            # 验证返回字段
            assert 'status' in result
            assert 'timestamp' in result
            assert 'duration_ms' in result
            assert 'checks_total' in result
            assert 'checks_passed' in result
        except ImportError:
            pytest.skip("健康检查模块不存在")


class TestExportService:
    """数据导出服务测试"""

    def test_export_service_module_exists(self):
        """测试导出服务模块是否存在"""
        try:
            from business_common.export_service import ExportService
            assert ExportService is not None
        except ImportError:
            pytest.fail("导出服务模块不存在")

    def test_export_service_methods(self):
        """测试导出服务方法"""
        try:
            from business_common.export_service import ExportService
            exporter = ExportService()
            
            # 验证必要方法存在
            assert hasattr(exporter, 'export_to_csv')
            assert hasattr(exporter, 'export_to_excel')
            assert hasattr(exporter, 'export_to_json')
            assert hasattr(exporter, 'export_orders')
            assert hasattr(exporter, 'export_members')
            assert hasattr(exporter, 'export_applications')
            assert hasattr(exporter, 'export_products')
        except ImportError:
            pytest.skip("导出服务模块不存在")

    def test_csv_export_functionality(self):
        """测试CSV导出功能"""
        try:
            from business_common.export_service import ExportService
            
            test_data = [
                {'id': 1, 'name': '测试1', 'value': 100},
                {'id': 2, 'name': '测试2', 'value': 200}
            ]
            
            exporter = ExportService()
            filepath = exporter.export_to_csv(test_data, 'test_export')
            
            # 验证文件生成
            assert filepath is not None
            assert os.path.exists(filepath)
            assert filepath.endswith('.csv')
            
            # 验证文件内容
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                assert 'id' in content
                assert 'name' in content
                assert '测试1' in content
            
            # 清理测试文件
            os.remove(filepath)
        except ImportError:
            pytest.skip("导出服务模块不存在")

    def test_json_export_functionality(self):
        """测试JSON导出功能"""
        try:
            from business_common.export_service import ExportService
            
            test_data = [
                {'id': 1, 'name': '测试1'},
                {'id': 2, 'name': '测试2'}
            ]
            
            exporter = ExportService()
            filepath = exporter.export_to_json(test_data, 'test_json')
            
            # 验证文件生成
            assert filepath is not None
            assert os.path.exists(filepath)
            assert filepath.endswith('.json')
            
            # 验证JSON格式
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert 'data' in data
                assert len(data['data']) == 2
            
            # 清理测试文件
            os.remove(filepath)
        except ImportError:
            pytest.skip("导出服务模块不存在")


class TestApiDocsGenerator:
    """API文档生成器测试"""

    def test_api_docs_generator_exists(self):
        """测试API文档生成器是否存在"""
        generator_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'api_docs_generator.py'
        )
        assert os.path.exists(generator_path), "API文档生成器不存在"

    def test_parse_flask_routes_function(self):
        """测试Flask路由解析功能"""
        generator_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'api_docs_generator.py'
        )
        
        with open(generator_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证解析函数存在
        assert 'parse_flask_routes' in content
        assert 'generate_openapi_spec' in content
        assert 'generate_api_docs' in content


class TestStaffDataIsolation:
    """员工端数据隔离测试"""

    def test_booking_complete_has_scope_filter(self):
        """测试预约完成接口是否有数据隔离"""
        staff_app_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-staffH5', 'app.py'
        )
        
        with open(staff_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找 staff_complete_booking 函数
        pattern = r"def staff_complete_booking.*?(?=\n\ndef |\n@|class |if __name__|$)"
        match = re.search(pattern, content, re.DOTALL)
        
        assert match is not None, "找不到 staff_complete_booking 函数"
        
        func_content = match.group(0)
        
        # V17.0修复：验证是否有ec_id和project_id过滤
        assert 'ec_id' in func_content, "预约完成接口缺少ec_id数据隔离"
        assert 'project_id' in func_content, "预约完成接口缺少project_id数据隔离"
        assert 'where +=' in func_content or 'WHERE' in func_content.upper(), "缺少SQL WHERE条件构建"

    def test_dashboard_stats_endpoint_exists(self):
        """测试仪表盘统计接口是否存在"""
        staff_app_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-staffH5', 'app.py'
        )
        
        with open(staff_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证V17.0新增的仪表盘统计接口
        assert 'staff_dashboard_stats' in content
        assert "api/staff/statistics/dashboard" in content

    def test_audit_logs_endpoint_exists(self):
        """测试操作日志查询接口是否存在"""
        staff_app_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-staffH5', 'app.py'
        )
        
        with open(staff_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证V17.0新增的操作日志接口
        assert 'staff_audit_logs' in content
        assert "api/staff/audit-logs" in content
        assert 'staff_audit_action_stats' in content


class TestHealthCheckEndpoint:
    """健康检查端点测试"""

    def test_user_h5_health_endpoint(self):
        """测试用户端健康检查端点"""
        user_app_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'app.py'
        )
        
        with open(user_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证基础健康检查
        assert "@app.route('/health')" in content
        # 验证V17.0详细健康检查
        assert 'health_detailed' in content
        assert "api/health/detailed" in content

    def test_staff_h5_health_endpoint(self):
        """测试员工端健康检查端点"""
        staff_app_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-staffH5', 'app.py'
        )
        
        with open(staff_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证基础健康检查
        assert "@app.route('/health')" in content
        # 验证V17.0详细健康检查
        assert 'health_detailed' in content
        assert "api/health/detailed" in content

    def test_admin_health_endpoint(self):
        """测试管理端健康检查端点"""
        admin_app_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'app.py'
        )
        
        with open(admin_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证基础健康检查
        assert "@app.route('/health')" in content
        # 验证V17.0详细健康检查
        assert 'health_detailed' in content
        assert "api/admin/health/detailed" in content


class TestV17Features:
    """V17.0功能完整性测试"""

    def test_v17_new_files(self):
        """测试V17.0新增文件"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        required_files = {
            '健康检查服务': 'business-common/health_check.py',
            '导出服务': 'business-common/export_service.py',
            'API文档生成器': 'business-common/api_docs_generator.py',
            'V17测试': 'tests/test_v17.py'
        }
        
        missing = []
        for name, path in required_files.items():
            full_path = os.path.join(project_root, path)
            if not os.path.exists(full_path):
                missing.append(name)
        
        if missing:
            pytest.fail(f"V17.0缺少文件: {', '.join(missing)}")

    def test_v17_staff_enhancements(self):
        """测试V17.0员工端增强功能"""
        staff_app_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-staffH5', 'app.py'
        )
        
        with open(staff_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # V17.0员工端增强功能列表
        features = [
            ('仪表盘统计', 'staff_dashboard_stats'),
            ('操作日志查询', 'staff_audit_logs'),
            ('操作类型统计', 'staff_audit_action_stats'),
            ('预约核销数据隔离', 'ec_id'),  # 在staff_complete_booking中
            ('审计日志记录', 'audit_log.log_action')
        ]
        
        missing_features = []
        for name, keyword in features:
            if keyword not in content:
                missing_features.append(name)
        
        if missing_features:
            pytest.fail(f"V17.0员工端缺少功能: {', '.join(missing_features)}")

    def test_v17_integration_summary(self):
        """V17.0功能总结验证"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 统计V17.0新增的路由
        staff_app_path = os.path.join(project_root, 'business-staffH5', 'app.py')
        user_app_path = os.path.join(project_root, 'business-userH5', 'app.py')
        admin_app_path = os.path.join(project_root, 'business-admin', 'app.py')
        
        new_routes = {
            'staff': [],
            'user': [],
            'admin': []
        }
        
        # 员工端新增路由
        with open(staff_app_path, 'r', encoding='utf-8') as f:
            staff_content = f.read()
            if 'staff_dashboard_stats' in staff_content:
                new_routes['staff'].append('GET /api/staff/statistics/dashboard')
            if 'staff_audit_logs' in staff_content:
                new_routes['staff'].append('GET /api/staff/audit-logs')
            if 'staff_audit_action_stats' in staff_content:
                new_routes['staff'].append('GET /api/staff/audit-logs/actions')
        
        # 用户端新增路由
        with open(user_app_path, 'r', encoding='utf-8') as f:
            user_content = f.read()
            if 'health_detailed' in user_content:
                new_routes['user'].append('GET /api/health/detailed')
        
        # 管理端新增路由
        with open(admin_app_path, 'r', encoding='utf-8') as f:
            admin_content = f.read()
            if 'health_detailed' in admin_content:
                new_routes['admin'].append('GET /api/admin/health/detailed')
        
        print("\n=== V17.0 新增API路由 ===")
        print(f"员工端: {len(new_routes['staff'])} 个")
        for route in new_routes['staff']:
            print(f"  - {route}")
        print(f"用户端: {len(new_routes['user'])} 个")
        for route in new_routes['user']:
            print(f"  - {route}")
        print(f"管理端: {len(new_routes['admin'])} 个")
        for route in new_routes['admin']:
            print(f"  - {route}")
        
        # 验证至少有新功能
        total_new = len(new_routes['staff']) + len(new_routes['user']) + len(new_routes['admin'])
        assert total_new > 0, "V17.0应该至少有新增功能"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
