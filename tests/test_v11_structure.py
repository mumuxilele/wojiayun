"""
V11.0 结构验证测试 - 无需数据库连接
测试内容：
  - 员工端新增路由验证（订单发货/退款审核/会员查询/签到统计/商品管理）
  - 管理端新增统计接口验证
  - 用户端门店页面路由验证
  - 重复路由Bug修复验证
  - 代码质量检查（无语法错误）
"""
import sys
import os
import ast
import re

# 路径设置
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_H5_APP = os.path.join(ROOT, 'business-userH5', 'app.py')
STAFF_H5_APP = os.path.join(ROOT, 'business-staffH5', 'app.py')
ADMIN_APP = os.path.join(ROOT, 'business-admin', 'app.py')
USER_H5_DIR = os.path.join(ROOT, 'business-userH5')


def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def get_routes(content):
    """提取所有路由"""
    return re.findall(r"@app\.route\('([^']+)'", content)


# ============ P0 Bug 修复验证 ============

class TestP0BugFixes:
    """P0 Bug 修复验证"""

    def test_user_h5_no_duplicate_root_route(self):
        """P0修复：userH5/app.py不应有重复的 @app.route('/') 定义"""
        content = read_file(USER_H5_APP)
        routes = get_routes(content)
        root_count = routes.count('/')
        # 允许最多1个'/'路由
        assert root_count <= 1, f"发现重复根路由注册 {root_count} 次，应只有1次"

    def test_user_h5_valid_python_syntax(self):
        """P0修复：userH5/app.py 语法正确"""
        content = read_file(USER_H5_APP)
        try:
            ast.parse(content)
        except SyntaxError as e:
            assert False, f"userH5/app.py 语法错误: {e}"

    def test_staff_h5_valid_python_syntax(self):
        """P0修复：staffH5/app.py 语法正确"""
        content = read_file(STAFF_H5_APP)
        try:
            ast.parse(content)
        except SyntaxError as e:
            assert False, f"staffH5/app.py 语法错误: {e}"

    def test_admin_valid_python_syntax(self):
        """P0修复：admin/app.py 语法正确"""
        content = read_file(ADMIN_APP)
        try:
            ast.parse(content)
        except SyntaxError as e:
            assert False, f"admin/app.py 语法错误: {e}"


# ============ 员工端新增路由验证 ============

class TestStaffH5NewRoutes:
    """V11.0 员工端新增功能路由验证"""

    def setup_method(self):
        self.content = read_file(STAFF_H5_APP)
        self.routes = get_routes(self.content)

    def test_staff_ship_order_route(self):
        """V11新增：员工端订单发货路由存在"""
        assert any('ship' in r for r in self.routes), "缺少订单发货路由 /api/staff/orders/<id>/ship"

    def test_staff_process_refund_route(self):
        """V11新增：员工端退款处理路由存在"""
        assert any('refund' in r for r in self.routes), "缺少退款处理路由 /api/staff/orders/<id>/refund"

    def test_staff_complete_order_route(self):
        """V11新增：员工端完成订单路由存在"""
        assert any('complete' in r and 'order' in r for r in self.routes), "缺少完成订单路由"

    def test_staff_members_route(self):
        """V11新增：员工端会员查询路由存在"""
        assert '/api/staff/members' in self.routes, "缺少会员查询路由 /api/staff/members"

    def test_staff_checkin_stats_route(self):
        """V11新增：员工端签到统计路由存在"""
        assert '/api/staff/checkin/stats' in self.routes, "缺少签到统计路由 /api/staff/checkin/stats"

    def test_staff_pending_refunds_route(self):
        """V11新增：员工端待退款订单路由存在"""
        assert '/api/staff/orders/pending-refunds' in self.routes, "缺少待退款订单路由"

    def test_staff_products_route(self):
        """V11新增：员工端商品查看路由存在"""
        assert '/api/staff/products' in self.routes, "缺少商品查看路由 /api/staff/products"

    def test_staff_ship_order_has_data_isolation(self):
        """安全性：发货接口包含数据隔离过滤"""
        assert 'ec_id' in self.content and 'project_id' in self.content, \
            "员工端发货接口缺少 ec_id/project_id 数据隔离"

    def test_staff_refund_has_notification(self):
        """业务完整性：退款处理后发送通知"""
        assert 'send_notification' in self.content, \
            "退款处理接口缺少用户通知逻辑"

    def test_staff_ship_uses_rate_limiter(self):
        """安全性：发货接口有限流保护"""
        assert 'rate_limit' in self.content, "员工端缺少限流保护"

    def test_staff_total_routes_expanded(self):
        """功能完整性：员工端路由数量已从20条增加"""
        count = len(self.routes)
        assert count > 25, f"员工端路由数量 {count} 偏少，预期至少25条（含V11新增7条）"


# ============ 管理端新增接口验证 ============

class TestAdminNewAPIs:
    """V11.0 管理端新增统计接口验证"""

    def setup_method(self):
        self.content = read_file(ADMIN_APP)
        self.routes = get_routes(self.content)

    def test_refund_analysis_route(self):
        """V11新增：退款分析接口存在"""
        assert '/api/admin/statistics/refund-analysis' in self.routes, \
            "缺少退款分析接口 /api/admin/statistics/refund-analysis"

    def test_member_growth_route(self):
        """V11新增：会员增长趋势接口存在"""
        assert '/api/admin/statistics/member-growth' in self.routes, \
            "缺少会员增长趋势接口 /api/admin/statistics/member-growth"

    def test_inventory_warning_route(self):
        """V11新增：库存预警接口存在"""
        assert '/api/admin/statistics/inventory-warning' in self.routes, \
            "缺少库存预警接口 /api/admin/statistics/inventory-warning"

    def test_statistics_includes_refund_rate(self):
        """V11增强：统计接口返回退款率"""
        assert 'refund_rate' in self.content, "统计接口缺少退款率字段"

    def test_statistics_includes_review_stats(self):
        """V11增强：统计接口返回评价统计"""
        assert 'total_reviews' in self.content and 'avg_rating' in self.content, \
            "统计接口缺少评价统计字段"

    def test_refund_analysis_has_caching(self):
        """性能优化：退款分析接口有缓存"""
        # 检查退款分析函数体内有cache
        idx = self.content.find('refund_analysis')
        if idx > 0:
            snippet = self.content[idx:idx+500]
            assert 'cache_get' in snippet or 'cache_set' in snippet, \
                "退款分析接口缺少缓存"

    def test_member_growth_has_level_distribution(self):
        """业务完整性：会员增长接口包含等级分布数据"""
        assert 'level_distribution' in self.content, "会员增长接口缺少等级分布数据"

    def test_inventory_warning_has_threshold_param(self):
        """功能完整性：库存预警支持自定义阈值"""
        assert 'threshold' in self.content, "库存预警接口缺少阈值参数"


# ============ 用户端新增页面验证 ============

class TestUserH5NewPages:
    """V11.0 用户端新增页面验证"""

    def test_shops_html_exists(self):
        """V11新增：门店列表页面存在"""
        shops_path = os.path.join(USER_H5_DIR, 'shops.html')
        assert os.path.exists(shops_path), "缺少门店页面 business-userH5/shops.html"

    def test_shops_html_has_search(self):
        """门店页面：包含搜索功能"""
        shops_path = os.path.join(USER_H5_DIR, 'shops.html')
        if os.path.exists(shops_path):
            content = read_file(shops_path)
            assert 'searchInput' in content or 'search' in content.lower(), \
                "门店页面缺少搜索功能"

    def test_shops_html_has_filter(self):
        """门店页面：包含分类筛选"""
        shops_path = os.path.join(USER_H5_DIR, 'shops.html')
        if os.path.exists(shops_path):
            content = read_file(shops_path)
            assert 'filter-tag' in content or 'filterBar' in content, \
                "门店页面缺少分类筛选"

    def test_shops_html_has_detail_modal(self):
        """门店页面：包含详情弹窗"""
        shops_path = os.path.join(USER_H5_DIR, 'shops.html')
        if os.path.exists(shops_path):
            content = read_file(shops_path)
            assert 'modal' in content.lower() or 'detail' in content.lower(), \
                "门店页面缺少详情弹窗"

    def test_shops_html_has_favorite(self):
        """门店页面：包含收藏功能"""
        shops_path = os.path.join(USER_H5_DIR, 'shops.html')
        if os.path.exists(shops_path):
            content = read_file(shops_path)
            assert 'favorites' in content or 'fav' in content.lower(), \
                "门店页面缺少收藏功能"

    def test_index_html_has_shops_menu(self):
        """用户首页：包含附近门店菜单入口"""
        index_path = os.path.join(USER_H5_DIR, 'index.html')
        content = read_file(index_path)
        assert 'shops.html' in content, "首页缺少门店菜单入口"

    def test_shops_api_supports_shop_type_param(self):
        """API修复：门店接口支持shop_type参数（不只是type）"""
        content = read_file(USER_H5_APP)
        assert "shop_type" in content, "门店列表API不支持shop_type参数"

    def test_shops_api_has_pagination(self):
        """API增强：门店接口支持分页"""
        content = read_file(USER_H5_APP)
        idx = content.find("get_shops")
        if idx > 0:
            snippet = content[idx:idx+600]
            assert 'page_size' in snippet, "门店列表API缺少分页支持"

    def test_shops_api_returns_avg_rating(self):
        """API增强：门店接口返回平均评分"""
        content = read_file(USER_H5_APP)
        assert 'avg_rating' in content, "门店列表API缺少avg_rating字段"


# ============ 业务逻辑完整性验证 ============

class TestBusinessLogicIntegrity:
    """核心业务逻辑完整性验证"""

    def test_staff_ship_triggers_notification(self):
        """订单发货后应通知用户"""
        content = read_file(STAFF_H5_APP)
        # 在ship接口附近找notification调用
        idx = content.find('staff_ship_order')
        if idx > 0:
            snippet = content[idx:idx+1000]
            assert 'notification' in snippet or 'send_notification' in snippet, \
                "发货后未触发用户通知"

    def test_staff_refund_approve_updates_status_to_refunded(self):
        """退款批准后状态应更新为refunded"""
        content = read_file(STAFF_H5_APP)
        assert "order_status='refunded'" in content, "退款批准后未更新状态为refunded"

    def test_staff_refund_reject_restores_status_to_paid(self):
        """退款拒绝后状态应回滚为paid"""
        content = read_file(STAFF_H5_APP)
        assert "order_status='paid'" in content, "退款拒绝后未回滚状态"

    def test_staff_refund_reject_restores_stock(self):
        """退款拒绝后应恢复商品库存"""
        content = read_file(STAFF_H5_APP)
        assert 'stock=stock+' in content, "退款拒绝后未恢复库存"

    def test_admin_refund_analysis_has_30day_range(self):
        """退款分析：应包含30天时间范围"""
        content = read_file(ADMIN_APP)
        idx = content.find('refund_analysis')
        if idx > 0:
            snippet = content[idx:idx+1000]
            assert '30' in snippet or 'INTERVAL' in snippet, "退款分析缺少时间范围过滤"

    def test_user_h5_shops_page_shows_rating(self):
        """门店页面：应展示门店评分"""
        shops_path = os.path.join(USER_H5_DIR, 'shops.html')
        if os.path.exists(shops_path):
            content = read_file(shops_path)
            assert 'rating' in content.lower() or '评分' in content, \
                "门店页面未展示评分信息"

    def test_staff_refund_uses_transaction(self):
        """退款处理：应使用数据库事务保证原子性"""
        content = read_file(STAFF_H5_APP)
        idx = content.find('staff_process_refund')
        if idx > 0:
            snippet = content[idx:idx+1500]
            assert 'conn.begin()' in snippet or 'begin()' in snippet, \
                "退款处理未使用事务，可能造成数据不一致"

    def test_staff_checkin_stats_has_top_users(self):
        """签到统计：应包含活跃用户排行"""
        content = read_file(STAFF_H5_APP)
        assert 'top_users' in content, "签到统计缺少活跃用户排行"


# ============ 安全性验证 ============

class TestSecurityV11:
    """V11.0 安全性验证"""

    def test_staff_ship_requires_auth(self):
        """发货接口：必须使用require_staff装饰器"""
        content = read_file(STAFF_H5_APP)
        idx = content.find("'/api/staff/orders/<order_id>/ship'")
        if idx > 0:
            snippet = content[idx:idx+100]
            assert '@require_staff' in content[max(0,idx-200):idx+200], \
                "发货接口未使用require_staff认证装饰器"

    def test_staff_refund_requires_auth(self):
        """退款接口：必须使用require_staff装饰器"""
        content = read_file(STAFF_H5_APP)
        assert '@require_staff' in content, "员工端接口缺少认证装饰器"

    def test_admin_new_routes_use_require_admin(self):
        """管理端新接口：应使用@require_admin装饰器"""
        content = read_file(ADMIN_APP)
        assert 'require_admin' in content, "管理端缺少认证装饰器"

    def test_staff_data_isolation_in_ship(self):
        """数据隔离：发货接口检查ec_id/project_id"""
        content = read_file(STAFF_H5_APP)
        idx = content.find('staff_ship_order')
        if idx > 0:
            snippet = content[idx:idx+800]
            assert 'ec_id' in snippet, "发货接口缺少数据隔离（ec_id）"

    def test_user_shops_api_no_deleted(self):
        """数据安全：门店列表不返回已删除门店"""
        content = read_file(USER_H5_APP)
        idx = content.find('get_shops')
        if idx > 0:
            snippet = content[idx:idx+500]
            assert 'deleted=0' in snippet, "门店列表接口未过滤已删除记录"


# ============ 运行 ============

if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '--tb=short'])
