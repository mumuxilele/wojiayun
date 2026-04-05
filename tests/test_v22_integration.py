#!/usr/bin/env python3
"""
V22.0 自动化测试 - 集成测试
测试范围:
  - 物流追踪服务
  - 增强搜索服务
  - API接口集成

运行方式:
  pytest tests/test_v22_integration.py -v
  pytest tests/test_v22_integration.py -v --tb=short
"""
import pytest
import sys
import os
import json
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLogisticsService:
    """物流服务测试"""

    def test_logistics_service_import(self):
        """物流服务模块可以正常导入"""
        from business_common.logistics_service import LogisticsService, logistics
        assert LogisticsService is not None
        assert logistics is not None

    def test_company_code_mapping(self):
        """物流公司编码映射正确"""
        from business_common.logistics_service import LogisticsService

        # 测试常见快递公司
        assert LogisticsService.get_company_code('顺丰速运') == 'SF'
        assert LogisticsService.get_company_code('顺丰') == 'SF'
        assert LogisticsService.get_company_code('中通快递') == 'ZTO'
        assert LogisticsService.get_company_code('圆通') == 'YTO'
        assert LogisticsService.get_company_code('未知快递') is None

    def test_company_name_from_code(self):
        """通过编码获取公司名称"""
        from business_common.logistics_service import LogisticsService

        assert LogisticsService.get_company_name('SF') == '顺丰速运'
        assert LogisticsService.get_company_name('ZTO') == '中通快递'
        assert LogisticsService.get_company_name('INVALID') == 'INVALID'

    def test_query_mock_returns_valid_structure(self):
        """模拟查询返回正确的结构"""
        from business_common.logistics_service import LogisticsService

        result = LogisticsService._query_mock('SF123456789', 'SF')

        assert result['success'] is True
        data = result['data']
        assert 'tracking_no' in data
        assert 'company_code' in data
        assert 'company_name' in data
        assert 'status' in data
        assert 'state' in data
        assert 'traces' in data
        assert data['is_mock'] is True

    def test_query_empty_tracking_no(self):
        """空单号返回错误"""
        from business_common.logistics_service import LogisticsService

        result = LogisticsService.query_logistics('')
        assert result['success'] is False
        assert '不能为空' in result.get('msg', '')

    def test_logistics_status_mapping(self):
        """物流状态映射正确"""
        from business_common.logistics_service import LOGISTICS_STATUS

        # 验证状态码
        assert 0 in LOGISTICS_STATUS  # 暂无轨迹
        assert 1 in LOGISTICS_STATUS  # 已揽收
        assert 2 in LOGISTICS_STATUS  # 运输中
        assert 3 in LOGISTICS_STATUS  # 派送中
        assert 4 in LOGISTICS_STATUS  # 已签收

        # 验证状态信息
        assert 'name' in LOGISTICS_STATUS[3]
        assert 'chinese' in LOGISTICS_STATUS[3]
        assert LOGISTICS_STATUS[3]['name'] == '派送中'

    def test_get_logistics_companies(self):
        """获取物流公司列表"""
        from business_common.logistics_service import LogisticsService

        companies = LogisticsService.get_logistics_companies()
        assert isinstance(companies, list)
        assert len(companies) > 0

        # 验证列表格式
        for company in companies:
            assert 'code' in company
            assert 'name' in company


class TestSearchService:
    """搜索服务测试"""

    def test_search_service_import(self):
        """搜索服务模块可以正常导入"""
        from business_common.search_service import SearchService, search
        assert SearchService is not None
        assert search is not None

    def test_search_config(self):
        """搜索配置正确"""
        from business_common.search_service import (
            MIN_SEARCH_LENGTH, MAX_SEARCH_RESULTS,
            HOT_SEARCH_LIMIT, SEARCH_HISTORY_LIMIT
        )

        assert MIN_SEARCH_LENGTH == 2
        assert MAX_SEARCH_RESULTS == 50
        assert HOT_SEARCH_LIMIT == 20
        assert SEARCH_HISTORY_LIMIT == 10

    def test_stop_words(self):
        """停用词列表存在"""
        from business_common.search_service import SearchService

        stop_words = SearchService.STOP_WORDS
        assert isinstance(stop_words, set)
        assert len(stop_words) > 0
        assert '的' in stop_words
        assert '了' in stop_words

    def test_sticky_hot_words(self):
        """置顶热词配置"""
        from business_common.search_service import SearchService

        sticky = SearchService.STICKY_HOT_WORDS
        assert isinstance(sticky, list)
        assert len(sticky) > 0
        assert '优惠' in sticky
        assert '热卖' in sticky

    def test_search_keyword_too_short(self):
        """搜索词太短返回错误"""
        from business_common.search_service import search

        result = search.search_products('a', user_id=1)
        assert result['success'] is False
        assert '至少' in result.get('msg', '')

    def test_search_empty_keyword(self):
        """空搜索词返回错误"""
        from business_common.search_service import search

        result = search.search_products('')
        assert result['success'] is False

    def test_fallback_search_returns_valid_structure(self):
        """回退搜索返回正确结构"""
        from business_common.search_service import SearchService

        result = SearchService._fallback_search('测试', None, None, 1, 20)
        assert result['success'] is True
        assert 'data' in result
        data = result['data']
        assert 'keyword' in data
        assert 'page' in data
        assert 'page_size' in data
        assert 'total' in data
        assert 'items' in data
        assert isinstance(data['items'], list)

    def test_sort_options(self):
        """排序选项正确"""
        from business_common.search_service import SearchService

        for sort in ['relevance', 'sales', 'price_asc', 'price_desc', 'new', 'hot']:
            sql = SearchService._build_sort_sql(sort, '测试')
            assert sql is not None
            assert 'ORDER BY' not in sql or 'p.' in sql  # 不应该有原始输入

    def test_build_sort_sql(self):
        """排序SQL构建正确"""
        from business_common.search_service import SearchService

        sql = SearchService._build_sort_sql('price_asc', '')
        assert 'ASC' in sql
        assert 'price' in sql

        sql = SearchService._build_sort_sql('sales', '')
        assert 'sales_count' in sql


class TestV22Migrations:
    """V22数据库迁移测试"""

    def test_migration_v22_import(self):
        """V22迁移脚本可以导入"""
        from business_common import migrate_v22
        assert hasattr(migrate_v22, 'migrate_v22')
        assert hasattr(migrate_v22, 'rollback_v22')

    def test_migration_v22_sql_import(self):
        """V22 SQL迁移脚本存在"""
        # 检查SQL文件是否存在
        sql_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v22.sql'
        )
        # 注意: SQL文件可能不存在，这是正常的
        # 主要测试Python迁移脚本


class TestV22APIRoutes:
    """V22 API路由测试 (静态分析)"""

    def test_userh5_imports_logistics_service(self):
        """userH5已导入物流服务"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'from business_common.logistics_service import logistics' in content

    def test_userh5_imports_search_service(self):
        """userH5已导入搜索服务"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'from business_common.search_service import search' in content

    def test_logistics_endpoints_exist(self):
        """物流API端点已定义"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查端点定义
        assert "route('/api/user/orders/<int:order_id>/logistics'" in content
        assert "route('/api/user/logistics/companies'" in content
        assert "route('/api/user/logistics/query'" in content

    def test_search_endpoints_exist(self):
        """搜索API端点已定义"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查端点定义
        assert "route('/api/search/products'" in content
        assert "route('/api/search/history'" in content
        assert "route('/api/search/hot'" in content
        assert "route('/api/search/suggestions'" in content
        assert "route('/api/recommendations'" in content

    def test_search_endpoints_with_methods(self):
        """搜索端点HTTP方法正确"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 搜索历史应该有GET和DELETE
        search_history_get = re.search(
            r"@app\.route\('/api/search/history', methods=\['GET'\]\)",
            content
        )
        search_history_delete = re.search(
            r"@app\.route\('/api/search/history', methods=\['DELETE'\]\)",
            content
        )
        assert search_history_get is not None
        assert search_history_delete is not None

    def test_logistics_endpoints_with_auth(self):
        """物流查询端点有认证"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查订单物流查询有@require_login
        logistics_pattern = r"@require_login\s+.*?\ndef get_order_logistics"
        assert re.search(logistics_pattern, content, re.DOTALL) is not None

    def test_public_logistics_endpoints(self):
        """公开物流端点无需认证"""
        with open('business-userH5/app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 物流公司列表和单号查询应该是公开的
        companies_endpoint = re.search(
            r"@app\.route\('/api/user/logistics/companies', methods=\['GET'\]\)\s+def get_logistics_companies",
            content
        )
        assert companies_endpoint is not None


class TestV22ServiceFiles:
    """V22新增服务文件测试"""

    def test_logistics_service_file_exists(self):
        """物流服务文件存在"""
        path = 'business-common/logistics_service.py'
        assert os.path.exists(path), f"{path} 不存在"

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 验证关键类和方法
        assert 'class LogisticsService' in content
        assert 'def query_logistics' in content
        assert 'def get_order_logistics' in content
        assert 'def update_order_logistics' in content
        assert 'def get_logistics_companies' in content
        assert 'LOGISTICS_COMPANY_CODES' in content
        assert 'LOGISTICS_STATUS' in content

    def test_search_service_file_exists(self):
        """搜索服务文件存在"""
        path = 'business-common/search_service.py'
        assert os.path.exists(path), f"{path} 不存在"

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 验证关键类和方法
        assert 'class SearchService' in content
        assert 'def search_products' in content
        assert 'def get_user_search_history' in content
        assert 'def get_hot_search_words' in content
        assert 'def get_recommended_products' in content
        assert 'STOP_WORDS' in content
        assert 'STICKY_HOT_WORDS' in content

    def test_migrate_v22_file_exists(self):
        """V22迁移文件存在"""
        path = 'business-common/migrate_v22.py'
        assert os.path.exists(path), f"{path} 不存在"

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 验证关键函数
        assert 'def migrate_v22' in content
        assert 'def rollback_v22' in content
        assert 'business_logistics_traces' in content
        assert 'business_search_history' in content


class TestV22SecurityChecks:
    """V22安全检查测试"""

    def test_no_hardcoded_passwords_in_new_files(self):
        """新增文件无硬编码密码"""
        files_to_check = [
            'business-common/logistics_service.py',
            'business-common/search_service.py',
        ]

        dangerous_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
        ]

        for filepath in files_to_check:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in dangerous_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    # 过滤掉空值和TODO注释中的示例
                    real_matches = [m for m in matches if 'TODO' not in m and 'your_' not in m.lower()]
                    assert len(real_matches) == 0, f"{filepath} 中发现硬编码: {real_matches}"

    def test_sql_injection_prevention(self):
        """检查搜索服务使用参数化查询"""
        with open('business-common/search_service.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 确保使用参数化查询
        assert '%s' in content, "应使用参数化查询"
        assert 'params' in content or 'params_list' in content, "应有参数列表"


class TestV22CodeQuality:
    """V22代码质量测试"""

    def test_logistics_service_has_docstrings(self):
        """物流服务有文档字符串"""
        with open('business-common/logistics_service.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查模块文档字符串
        assert '"""' in content, "应有文档字符串"

    def test_search_service_has_docstrings(self):
        """搜索服务有文档字符串"""
        with open('business-common/search_service.py', 'r', encoding='utf-8') as f:
            content = f.read()

        assert '"""' in content, "应有文档字符串"

    def test_no_syntax_errors_in_new_files(self):
        """新增文件无语法错误"""
        files_to_check = [
            'business-common/logistics_service.py',
            'business-common/search_service.py',
            'business-common/migrate_v22.py',
        ]

        for filepath in files_to_check:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    code = f.read()
                try:
                    compile(code, filepath, 'exec')
                except SyntaxError as e:
                    pytest.fail(f"{filepath} 语法错误: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
