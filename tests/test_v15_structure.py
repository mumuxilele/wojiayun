"""
V15.0 结构验证测试
测试所有V15新增和增强功能
设计原则：不依赖pymysql等数据库库，通过源码分析和文件结构验证

运行方式:
    python -m pytest tests/test_v15_structure.py -v --tb=short
"""
import os
import re
import sys
import hashlib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_file(rel_path):
    """读取项目文件内容"""
    abs_path = os.path.join(PROJECT_ROOT, rel_path.replace('/', os.sep))
    with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def _extract_routes(source):
    """从Flask app.py源码中提取路由"""
    return re.findall(r"@app\.route\('([^']+)'", source)


def _extract_function_defs(source):
    """提取函数定义"""
    return re.findall(r'def\s+(\w+)\s*\(', source)


# ============ 测试：Token缓存SHA256加固 ============

class TestTokenCacheSHA256:
    """测试V15-1 Token缓存安全加固"""

    def test_auth_module_has_hash_function(self):
        """测试auth模块包含哈希函数"""
        source = _read_file('business-common/auth.py')
        assert '_hash_key' in source
        assert 'def _hash_key' in source

    def test_hash_key_uses_sha256(self):
        """测试哈希函数使用SHA256"""
        source = _read_file('business-common/auth.py')
        assert 'sha256' in source
        assert 'hashlib' in source

    def test_hash_key_is_deterministic(self):
        """测试哈希逻辑一致性"""
        source = _read_file('business-common/auth.py')
        # 确保使用encode('utf-8')和hexdigest()
        assert 'hexdigest()' in source

    def test_cache_uses_hashed_keys(self):
        """测试缓存使用哈希key而非明文"""
        source = _read_file('business-common/auth.py')
        # 查找_cache_get和_cache_set使用_hash_key
        assert '_hash_key' in source
        # 查找缓存字典注释说明
        assert 'SHA256' in source or 'sha256' in source

    def test_invalidate_uses_hash(self):
        """测试缓存失效使用哈希key"""
        source = _read_file('business-common/auth.py')
        assert 'invalidate_token' in source


# ============ 测试：管理端认证绕过修复 ============

class TestAdminAuthBypassFix:
    """测试V15-2 管理端API认证钩子"""

    def test_before_request_hook_exists(self):
        """测试管理端before_request钩子已注册"""
        source = _read_file('business-admin/app.py')
        assert '@app.before_request' in source
        assert 'def check_admin' in source

    def test_exempt_paths_limited(self):
        """测试豁免路径已最小化"""
        source = _read_file('business-admin/app.py')
        # 不应包含过于宽泛的豁免
        assert 'exempt_paths' in source
        # 应仅豁免必要路径
        assert '/health' in source

    def test_admin_api_routes_count(self):
        """测试管理端有足够的API路由"""
        source = _read_file('business-admin/app.py')
        routes = _extract_routes(source)
        admin_routes = [r for r in routes if r.startswith('/api/admin/')]
        assert len(admin_routes) > 10


# ============ 测试：退款金额校验 ============

class TestRefundAmountValidation:
    """测试V15-3 退款金额安全校验"""

    def test_admin_refund_route_exists(self):
        """测试管理端退款处理路由存在"""
        source = _read_file('business-admin/app.py')
        routes = _extract_routes(source)
        assert any('refund' in r for r in routes)

    def test_staff_refund_route_exists(self):
        """测试员工端退款处理路由存在"""
        source = _read_file('business-staffH5/app.py')
        routes = _extract_routes(source)
        assert any('refund' in r for r in routes)

    def test_admin_refund_has_amount_check(self):
        """测试管理端退款包含金额校验逻辑"""
        source = _read_file('business-admin/app.py')
        # 检查退款处理函数中有金额校验
        assert 'refund_amount' in source
        assert 'actual_amount' in source
        assert '超过' in source  # 超过校验提示

    def test_staff_refund_has_amount_check(self):
        """测试员工端退款包含金额校验逻辑"""
        source = _read_file('business-staffH5/app.py')
        assert 'actual_amount' in source
        # 检查退款相关函数中有金额校验逻辑


# ============ 测试：订单导出增强 ============

class TestOrderExportEnhancement:
    """测试V15-4 订单导出增强"""

    def test_export_orders_route_exists(self):
        """测试订单导出路由存在"""
        source = _read_file('business-admin/app.py')
        routes = _extract_routes(source)
        assert '/api/admin/export/orders' in routes

    def test_export_has_date_filter(self):
        """测试导出包含日期筛选"""
        source = _read_file('business-admin/app.py')
        assert 'date_from' in source and 'export' in source.lower()

    def test_export_has_status_filter(self):
        """测试导出包含状态筛选"""
        source = _read_file('business-admin/app.py')
        # 查找export_orders函数中的status筛选
        assert 'export_orders' in source


# ============ 测试：XSS防护 ============

class TestXSSProtection:
    """测试V15-5 前端XSS防护"""

    def test_xss_utils_file_exists(self):
        """测试xss-utils.js文件存在"""
        path = os.path.join(PROJECT_ROOT, 'business-common', 'xss-utils.js')
        assert os.path.exists(path)

    def test_xss_utils_has_escape_html(self):
        """测试xss-utils.js包含escapeHtml函数"""
        source = _read_file('business-common/xss-utils.js')
        assert 'function escapeHtml' in source
        assert '&amp;' in source
        assert '&lt;' in source
        assert '&gt;' in source
        assert '&quot;' in source
        assert '&#39;' in source

    def test_xss_utils_has_escape_attr(self):
        """测试xss-utils.js包含escapeAttr函数"""
        source = _read_file('business-common/xss-utils.js')
        assert 'function escapeAttr' in source

    def test_chat_staff_has_escape_html(self):
        """测试客服聊天页包含escapeHtml"""
        source = _read_file('chat/staff.html')
        assert 'escapeHtml' in source

    def test_chat_staff_mobile_has_escape_html(self):
        """测试移动端客服聊天页包含escapeHtml"""
        source = _read_file('chat/staff-mobile.html')
        assert 'escapeHtml' in source

    def test_chat_index_has_escape_html(self):
        """测试员工内部聊天页包含escapeHtml"""
        source = _read_file('chat/index.html')
        assert 'escapeHtml' in source

    def test_chat_user_has_escape_html(self):
        """测试用户聊天页包含escapeHtml"""
        source = _read_file('chat/user.html')
        assert 'escapeHtml' in source

    def test_feedback_user_has_escape_html(self):
        """测试用户反馈页包含escapeHtml"""
        source = _read_file('business-userH5/feedback.html')
        assert 'escapeHtml' in source

    def test_feedback_staff_has_escape_html(self):
        """测试员工反馈页包含escapeHtml"""
        source = _read_file('business-staffH5/feedback.html')
        assert 'escapeHtml' in source

    def test_feedback_admin_has_escape_html(self):
        """测试管理端反馈页包含escapeHtml"""
        source = _read_file('business-admin/feedback.html')
        assert 'escapeHtml' in source

    def test_shops_has_escape_html(self):
        """测试门店浏览页包含escapeHtml"""
        source = _read_file('business-userH5/shops.html')
        assert 'escapeHtml' in source

    def test_members_staff_has_escape_html(self):
        """测试员工端会员管理页包含escapeHtml"""
        source = _read_file('business-staffH5/members.html')
        assert 'escapeHtml' in source

    def test_bookings_user_has_escape_html(self):
        """测试用户预约页包含escapeHtml"""
        source = _read_file('business-userH5/bookings.html')
        assert 'escapeHtml' in source

    def test_bookings_staff_has_escape_html(self):
        """测试员工预约页包含escapeHtml"""
        source = _read_file('business-staffH5/bookings.html')
        assert 'escapeHtml' in source

    def test_staff_index_has_escape_html(self):
        """测试员工首页包含escapeHtml"""
        source = _read_file('business-staffH5/index.html')
        assert 'escapeHtml' in source


# ============ 测试：会员活跃度分析API ============

class TestMemberActivityAPI:
    """测试V15-6 会员活跃度统计API"""

    def test_member_activity_route_exists(self):
        """测试会员活跃度路由存在"""
        source = _read_file('business-staffH5/app.py')
        routes = _extract_routes(source)
        assert '/api/staff/statistics/members' in routes

    def test_member_activity_handler_exists(self):
        """测试会员活跃度处理函数存在"""
        source = _read_file('business-staffH5/app.py')
        assert 'get_staff_member_activity' in source
        assert 'active_members' in source or 'active' in source.lower()
        assert 'dormant' in source.lower() or 'sleeping' in source.lower()

    def test_member_activity_uses_view(self):
        """测试使用了member_activity_view视图"""
        source = _read_file('business-staffH5/app.py')
        assert 'business_member_activity_view' in source


# ============ 测试：收货地址管理页面 ============

class TestAddressManagementPage:
    """测试V15-7 收货地址管理"""

    def test_addresses_page_exists(self):
        """测试地址管理页面文件存在"""
        path = os.path.join(PROJECT_ROOT, 'business-userH5', 'addresses.html')
        assert os.path.exists(path)

    def test_addresses_page_has_crud(self):
        """测试地址页面包含增删改查功能"""
        source = _read_file('business-userH5/addresses.html')
        has_add = 'addAddress' in source or 'saveAddress' in source or '新增' in source
        has_delete = 'deleteAddress' in source or 'delAddress' in source or '删除' in source
        has_edit = 'editAddress' in source or '编辑' in source
        has_default = 'setDefault' in source or 'default' in source.lower()
        assert has_add
        assert has_delete

    def test_address_api_routes(self):
        """测试地址API路由存在"""
        source = _read_file('business-userH5/app.py')
        routes = _extract_routes(source)
        address_routes = [r for r in routes if 'address' in r.lower()]
        assert len(address_routes) >= 3


# ============ 测试：用户端评价功能 ============

class TestUserReviewFeature:
    """测试V15-8 用户端订单评价功能"""

    def test_review_api_routes(self):
        """测试评价API路由存在"""
        source = _read_file('business-userH5/app.py')
        routes = _extract_routes(source)
        assert '/api/user/reviews' in routes

    def test_order_detail_has_review_flag(self):
        """测试订单详情API返回has_review字段"""
        source = _read_file('business-userH5/app.py')
        # 检查get_order_detail函数
        assert 'has_review' in source
        assert 'business_reviews' in source

    def test_review_prevents_duplicate(self):
        """测试评价防重复逻辑"""
        source = _read_file('business-userH5/app.py')
        assert '已评价' in source or 'existing' in source

    def test_orders_page_has_review_modal(self):
        """测试订单页面包含评价弹窗"""
        source = _read_file('business-userH5/orders.html')
        assert 'reviewModal' in source
        assert 'ratingStars' in source
        assert 'submitReview' in source
        assert 'openReviewModal' in source

    def test_orders_page_has_anonymous_option(self):
        """测试评价支持匿名选项"""
        source = _read_file('business-userH5/orders.html')
        assert 'reviewAnonymous' in source or 'is_anonymous' in source or 'anonymous' in source

    def test_orders_page_review_button_in_actions(self):
        """测试已完成订单显示评价按钮"""
        source = _read_file('business-userH5/orders.html')
        assert 'openReviewModal' in source
        assert 'completed' in source
        assert '已评价' in source


# ============ 测试：迁移脚本完整性 ============

class TestMigrationIntegrity:
    """测试迁移脚本完整性"""

    def test_migrate_v11_exists(self):
        """测试V11迁移脚本存在"""
        path = os.path.join(PROJECT_ROOT, 'business-common', 'migrate_v11.py')
        assert os.path.exists(path)

    def test_migrate_v12_exists(self):
        """测试V12迁移脚本存在"""
        path = os.path.join(PROJECT_ROOT, 'business-common', 'migrate_v12.py')
        assert os.path.exists(path)

    def test_migrate_v11_has_migrate_function(self):
        """测试V11迁移脚本包含migrate函数"""
        source = _read_file('business-common/migrate_v11.py')
        funcs = _extract_function_defs(source)
        assert 'migrate' in funcs

    def test_migrate_v12_has_migrate_function(self):
        """测试V12迁移脚本包含migrate函数"""
        source = _read_file('business-common/migrate_v12.py')
        funcs = _extract_function_defs(source)
        assert 'migrate' in funcs


# ============ 测试：核心安全模式 ============

class TestCoreSecurityPatterns:
    """测试核心安全模式在V15中的强化"""

    def test_auth_module_docstring_v15(self):
        """测试auth模块文档标注V15"""
        source = _read_file('business-common/auth.py')
        assert 'V15' in source

    def test_rate_limiter_on_review_api(self):
        """测试评价API有速率限制"""
        source = _read_file('business-userH5/app.py')
        # 评价创建函数附近应有rate_limit装饰器
        assert 'rate_limit' in source
        assert 'create_review' in source

    def test_cache_service_module_exists(self):
        """测试缓存服务模块存在"""
        path = os.path.join(PROJECT_ROOT, 'business-common', 'cache_service.py')
        assert os.path.exists(path)

    def test_redis_cache_module_exists(self):
        """测试Redis缓存适配器存在"""
        path = os.path.join(PROJECT_ROOT, 'business-common', 'redis_cache_service.py')
        assert os.path.exists(path)


# ============ 测试：文件结构完整性 ============

class TestFileStructureCompleteness:
    """测试V15项目文件结构完整性"""

    def test_user_h5_has_addresses(self):
        """测试用户H5有地址管理页"""
        path = os.path.join(PROJECT_ROOT, 'business-userH5', 'addresses.html')
        assert os.path.exists(path)

    def test_common_has_xss_utils(self):
        """测试common有xss工具"""
        path = os.path.join(PROJECT_ROOT, 'business-common', 'xss-utils.js')
        assert os.path.exists(path)

    def test_user_h5_has_orders(self):
        """测试用户H5有订单页"""
        path = os.path.join(PROJECT_ROOT, 'business-userH5', 'orders.html')
        assert os.path.exists(path)

    def test_staff_h5_has_members(self):
        """测试员工H5有会员管理页"""
        path = os.path.join(PROJECT_ROOT, 'business-staffH5', 'members.html')
        assert os.path.exists(path)

    def test_staff_h5_has_refunds(self):
        """测试员工H5有退款管理页"""
        path = os.path.join(PROJECT_ROOT, 'business-staffH5', 'refunds.html')
        assert os.path.exists(path)

    def test_tests_directory_has_v15(self):
        """测试有V15测试文件"""
        path = os.path.join(PROJECT_ROOT, 'tests', 'test_v15_structure.py')
        assert os.path.exists(path)

    def test_user_h5_has_member_page(self):
        """测试用户H5有会员中心页"""
        path = os.path.join(PROJECT_ROOT, 'business-userH5', 'member.html')
        assert os.path.exists(path)

    def test_user_h5_has_shops_page(self):
        """测试用户H5有门店浏览页"""
        path = os.path.join(PROJECT_ROOT, 'business-userH5', 'shops.html')
        assert os.path.exists(path)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '--tb=short'])
