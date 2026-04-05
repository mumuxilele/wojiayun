#!/usr/bin/env python3
"""
V26.0 自动化测试套件
测试范围: 运营分析接口接入、运营看板真实数据、商品浏览/收藏计数埋点
"""
import os

import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_APP = os.path.join(PROJECT_ROOT, 'business-admin', 'app.py')
USER_APP = os.path.join(PROJECT_ROOT, 'business-userH5', 'app.py')
ANALYTICS_SERVICE = os.path.join(PROJECT_ROOT, 'business-common', 'analytics_service.py')
DATA_BOARD = os.path.join(PROJECT_ROOT, 'business-admin', 'data-board.html')
DASHBOARD = os.path.join(PROJECT_ROOT, 'business-admin', 'dashboard.html')


def read_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


class TestV26AnalyticsRoutes:
    def test_admin_routes_exist(self):
        content = read_text(ADMIN_APP)
        for route in [
            '/api/admin/statistics/overview',
            '/api/admin/statistics/trend',
            '/api/admin/products/top',
        ]:
            assert route in content, f'缺少路由: {route}'

    def test_admin_app_imports_analytics_service(self):
        content = read_text(ADMIN_APP)
        assert 'from business_common.analytics_service import analytics_service' in content

    def test_analytics_service_has_ratio_helper(self):
        content = read_text(ANALYTICS_SERVICE)
        assert 'def _calc_ratio' in content
        assert 'funnel["browse_rate"] = self._calc_ratio' in content
        assert 'funnel["cart_rate"] = self._calc_ratio' in content
        assert 'funnel["pay_rate"] = self._calc_ratio' in content


class TestV26UserBehaviorMetrics:
    def test_product_detail_bumps_view_count(self):
        content = read_text(USER_APP)
        assert "bump_product_counter(product_id, 'view_count', 1)" in content

    def test_favorite_flow_updates_favorite_count(self):
        content = read_text(USER_APP)
        assert "bump_product_counter(target_id, 'favorite_count', 1)" in content
        assert "bump_product_counter(target_id, 'favorite_count', -1)" in content
        assert 'def invalidate_user_cache' in content


class TestV26AdminPages:
    def test_data_board_uses_safe_query_separator(self):
        content = read_text(DATA_BOARD)
        assert "const separator = url.includes('?') ? '&' : '?'" in content

    def test_data_board_uses_real_funnel_data(self):
        content = read_text(DATA_BOARD)
        assert 'const funnel = overview.data?.funnel || {};' in content
        assert 'Math.round((overview.data?.visitors || 0) * 0.6)' not in content
        assert 'Math.round((overview.data?.visitors || 0) * 0.15)' not in content
        assert 'Math.round((overview.data?.visitors || 0) * 0.05)' not in content

    def test_dashboard_uses_real_trend_payload(self):
        content = read_text(DASHBOARD)
        assert 'const trendPayload = trendRes.data.data || {};' in content
        assert "const trend = Array.isArray(data) ? data : (data.trend || []);" in content
        assert 'Math.floor(Math.random() * 30)' not in content
        assert 'Math.floor(Math.random() * 5000)' not in content


class TestV26CodeQuality:
    @pytest.mark.parametrize('path', [ADMIN_APP, USER_APP, ANALYTICS_SERVICE])
    def test_python_files_compile(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, path, 'exec')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
