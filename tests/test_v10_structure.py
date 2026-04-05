"""
V10.0 结构验证测试
纯文件结构/代码内容验证，无需数据库连接

运行方式：
  cd wojiayun
  python -m pytest tests/test_v10_structure.py -v --tb=short
"""
import os
import pytest

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(rel_path):
    """读取项目文件内容"""
    full = os.path.join(ROOT, rel_path)
    with open(full, 'r', encoding='utf-8') as f:
        return f.read()


def file_exists(rel_path):
    return os.path.exists(os.path.join(ROOT, rel_path))


# ============================================================
# V10 - 用户端优惠券页面
# ============================================================
class TestV10MyCouponsPage:
    """用户端优惠券页面"""

    def test_my_coupons_html_exists(self):
        """my_coupons.html 文件应存在"""
        assert file_exists('business-userH5/my_coupons.html'), \
            "business-userH5/my_coupons.html 不存在"

    def test_my_coupons_has_tab_structure(self):
        """优惠券页面应有 Tab 结构"""
        content = read_file('business-userH5/my_coupons.html')
        assert 'tab' in content.lower(), "优惠券页面缺少 Tab 结构"

    def test_my_coupons_has_exchange_feature(self):
        """优惠券页面应支持积分兑换"""
        content = read_file('business-userH5/my_coupons.html')
        assert 'exchange' in content.lower() or '兑换' in content, \
            "优惠券页面缺少积分兑换功能"

    def test_my_coupons_api_integration(self):
        """优惠券页面应对接 coupons API"""
        content = read_file('business-userH5/my_coupons.html')
        assert '/api/user/coupons' in content or '/api/coupons' in content, \
            "优惠券页面未对接优惠券 API"

    def test_index_has_coupon_entry(self):
        """首页应有优惠券入口"""
        content = read_file('business-userH5/index.html')
        assert 'coupon' in content.lower() or '优惠券' in content, \
            "首页缺少优惠券菜单入口"


# ============================================================
# V10 - 用户端订单中心
# ============================================================
class TestV10OrdersPage:
    """用户端订单中心"""

    def test_orders_html_exists(self):
        """orders.html 文件应存在"""
        assert file_exists('business-userH5/orders.html'), \
            "business-userH5/orders.html 不存在"

    def test_orders_has_refund_feature(self):
        """订单页面应支持退款申请"""
        content = read_file('business-userH5/orders.html')
        assert 'refund' in content.lower() or '退款' in content, \
            "订单页面缺少退款功能"

    def test_orders_has_confirm_receipt(self):
        """订单页面应支持确认收货"""
        content = read_file('business-userH5/orders.html')
        assert 'confirm' in content.lower() or '确认收货' in content, \
            "订单页面缺少确认收货功能"

    def test_orders_has_status_filter(self):
        """订单页面应有状态筛选"""
        content = read_file('business-userH5/orders.html')
        assert 'shipped' in content or '已发货' in content or 'tab' in content.lower(), \
            "订单页面缺少状态筛选"

    def test_orders_has_order_detail_api(self):
        """订单页面应请求订单详情 API"""
        content = read_file('business-userH5/orders.html')
        assert '/api/user/orders' in content, \
            "订单页面未对接订单 API"


# ============================================================
# V10 - 用户端会员中心
# ============================================================
class TestV10MemberPage:
    """用户端会员中心"""

    def test_member_html_exists(self):
        """member.html 文件应存在"""
        assert file_exists('business-userH5/member.html'), \
            "business-userH5/member.html 不存在"

    def test_member_has_points_display(self):
        """会员中心应展示积分"""
        content = read_file('business-userH5/member.html')
        assert 'points' in content.lower() or '积分' in content, \
            "会员中心缺少积分展示"

    def test_member_has_level_display(self):
        """会员中心应展示会员等级"""
        content = read_file('business-userH5/member.html')
        assert 'level' in content.lower() or '等级' in content, \
            "会员中心缺少等级展示"

    def test_member_has_checkin_entry(self):
        """会员中心应有签到入口"""
        content = read_file('business-userH5/member.html')
        assert 'checkin' in content.lower() or '签到' in content, \
            "会员中心缺少签到入口"

    def test_member_api_integration(self):
        """会员中心应对接会员信息 API"""
        content = read_file('business-userH5/member.html')
        assert '/api/user/member' in content, \
            "会员中心未对接会员 API"

    def test_member_has_address_entry(self):
        """会员中心应有地址管理入口"""
        content = read_file('business-userH5/member.html')
        assert 'address' in content.lower() or '地址' in content, \
            "会员中心缺少地址管理入口"

    def test_index_has_member_entry(self):
        """首页应有会员中心入口"""
        content = read_file('business-userH5/index.html')
        assert 'member' in content.lower() or '会员' in content, \
            "首页缺少会员中心菜单入口"


# ============================================================
# V10 - 管理端商品管理
# ============================================================
class TestV10AdminProducts:
    """管理端商品管理页面"""

    def test_admin_products_html_exists(self):
        """管理端 products.html 应存在"""
        assert file_exists('business-admin/products.html'), \
            "business-admin/products.html 不存在"

    def test_admin_products_has_crud(self):
        """商品管理页应支持增删改查"""
        content = read_file('business-admin/products.html')
        assert 'saveProduct' in content or 'save_product' in content or \
               ('新增' in content and '编辑' in content), \
            "商品管理页缺少 CRUD 操作"

    def test_admin_products_has_status_toggle(self):
        """商品管理页应支持上下架"""
        content = read_file('business-admin/products.html')
        assert 'toggleStatus' in content or 'inactive' in content or '下架' in content, \
            "商品管理页缺少上下架功能"

    def test_admin_products_api_integration(self):
        """商品管理页应对接管理端 API"""
        content = read_file('business-admin/products.html')
        assert '/api/admin/products' in content, \
            "商品管理页未对接管理端 API"

    def test_admin_index_has_products_menu(self):
        """管理端首页侧边栏应有商品管理菜单"""
        content = read_file('business-admin/index.html')
        assert 'products' in content.lower() or '商品管理' in content, \
            "管理端侧边栏缺少商品管理菜单"

    def test_admin_app_has_product_detail_api(self):
        """管理端 app.py 应有商品详情接口"""
        content = read_file('business-admin/app.py')
        assert 'admin_get_product' in content or \
               ("'/api/admin/products/<" in content and "methods=['GET']" in content), \
            "管理端缺少商品详情 GET 接口"

    def test_admin_app_has_product_update_api(self):
        """管理端 app.py 应有商品更新接口"""
        content = read_file('business-admin/app.py')
        assert '/api/admin/products' in content and 'PUT' in content, \
            "管理端缺少商品更新 PUT 接口"


# ============================================================
# V10 - 管理端统计增强
# ============================================================
class TestV10StatisticsEnhancement:
    """管理端统计看板增强"""

    def test_admin_app_has_checkin_stats(self):
        """管理端统计接口应包含签到数据"""
        content = read_file('business-admin/app.py')
        assert 'today_checkins' in content or 'checkin' in content, \
            "管理端统计缺少签到数据字段"

    def test_admin_app_has_coupon_stats(self):
        """管理端统计接口应包含优惠券数据"""
        content = read_file('business-admin/app.py')
        assert 'used_coupons' in content or 'total_active_coupons' in content, \
            "管理端统计缺少优惠券数据字段"

    def test_admin_app_has_stock_warning(self):
        """管理端统计接口应包含库存预警"""
        content = read_file('business-admin/app.py')
        assert 'low_stock' in content or 'stock' in content, \
            "管理端统计缺少库存预警字段"

    def test_statistics_html_has_new_metrics(self):
        """统计页面应展示新增指标"""
        content = read_file('business-admin/statistics.html')
        assert ('checkin' in content.lower() or '签到' in content) or \
               ('coupon' in content.lower() or '优惠券' in content), \
            "统计页面未展示签到/优惠券指标"


# ============================================================
# V10 - 数据库迁移脚本
# ============================================================
class TestV10DatabaseMigration:
    """V10 数据库迁移脚本"""

    def test_migrate_v10_exists(self):
        """migrate_v10.py 迁移脚本应存在"""
        assert file_exists('business-common/migrate_v10.py'), \
            "business-common/migrate_v10.py 不存在"

    def test_migrate_v10_has_cart_table(self):
        """迁移脚本应包含购物车表"""
        content = read_file('business-common/migrate_v10.py')
        assert 'business_cart' in content, \
            "迁移脚本未包含购物车表 (business_cart)"

    def test_migrate_v10_has_index_optimization(self):
        """迁移脚本应包含索引优化"""
        content = read_file('business-common/migrate_v10.py')
        assert 'CREATE INDEX' in content or 'safe_create_index' in content, \
            "迁移脚本未包含索引优化"

    def test_migrate_v10_is_idempotent(self):
        """迁移脚本应有幂等保护"""
        content = read_file('business-common/migrate_v10.py')
        assert 'IF NOT EXISTS' in content or 'safe_alter' in content or \
               'except' in content.lower(), \
            "迁移脚本缺少幂等保护机制"

    def test_migrate_v10_has_product_fields(self):
        """迁移脚本应包含商品字段扩展"""
        content = read_file('business-common/migrate_v10.py')
        assert 'original_price' in content or 'sort_order' in content, \
            "迁移脚本未包含商品字段扩展"


# ============================================================
# V10 - 整体架构完整性
# ============================================================
class TestV10Architecture:
    """V10 架构完整性检查"""

    def test_user_h5_key_pages_exist(self):
        """用户端关键页面应齐全"""
        pages = [
            'business-userH5/index.html',
            'business-userH5/orders.html',
            'business-userH5/member.html',
            'business-userH5/my_coupons.html',
            'business-userH5/checkin.html',
            'business-userH5/products.html',
        ]
        missing = [p for p in pages if not file_exists(p)]
        assert not missing, f"用户端缺少页面: {missing}"

    def test_staff_h5_key_pages_exist(self):
        """员工端关键页面应齐全"""
        pages = [
            'business-staffH5/index.html',
            'business-staffH5/bookings.html',
        ]
        missing = [p for p in pages if not file_exists(p)]
        assert not missing, f"员工端缺少页面: {missing}"

    def test_admin_key_pages_exist(self):
        """管理端关键页面应齐全"""
        pages = [
            'business-admin/index.html',
            'business-admin/statistics.html',
            'business-admin/products.html',
        ]
        missing = [p for p in pages if not file_exists(p)]
        assert not missing, f"管理端缺少页面: {missing}"

    def test_common_services_exist(self):
        """公共服务文件应齐全"""
        files = [
            'business-common/migrate_v10.py',
            'business-common/cancel_expired_bookings.py',
            'business-common/cache_service.py',
        ]
        missing = [f for f in files if not file_exists(f)]
        assert not missing, f"公共服务缺少文件: {missing}"

    def test_three_backends_exist(self):
        """三端后端服务应存在"""
        backends = [
            'business-userH5/app.py',
            'business-staffH5/app.py',
            'business-admin/app.py',
        ]
        missing = [b for b in backends if not file_exists(b)]
        assert not missing, f"缺少后端服务: {missing}"


# ============================================================
# V10.1 - 员工端增强
# ============================================================
class TestV10StaffEnhancement:
    """员工端增强测试"""

    def test_staff_index_has_booking_entry(self):
        """员工端首页应有预约管理入口"""
        content = read_file('business-staffH5/index.html')
        assert 'bookings.html' in content, \
            "员工端首页缺少预约管理入口"

    def test_staff_index_has_verify_entry(self):
        """员工端首页应有核销站入口"""
        content = read_file('business-staffH5/index.html')
        assert 'verify' in content.lower() or '核销' in content, \
            "员工端首页缺少核销站入口"

    def test_staff_order_list_has_ship_action(self):
        """员工端订单页应支持发货操作"""
        content = read_file('business-staffH5/order_list.html')
        assert 'ship' in content.lower() or '发货' in content, \
            "员工端订单页缺少发货功能"

    def test_staff_order_list_has_refund_review(self):
        """员工端订单页应支持退款审核"""
        content = read_file('business-staffH5/order_list.html')
        assert 'refund' in content.lower() or '退款' in content, \
            "员工端订单页缺少退款审核功能"

    def test_staff_order_list_has_shipped_status(self):
        """员工端订单页应有已发货状态筛选"""
        content = read_file('business-staffH5/order_list.html')
        assert 'shipped' in content, \
            "员工端订单页缺少已发货状态筛选"


# ============================================================
# V10.1 - 管理端概览修复
# ============================================================
class TestV10AdminDashboardFix:
    """管理端概览页修复验证"""

    def test_admin_index_uses_correct_member_field(self):
        """管理端概览应使用 total_members 而非 total_applications 作为用户数"""
        content = read_file('business-admin/index.html')
        assert 'total_members' in content or 'active_users_7d' in content, \
            "管理端概览仍使用错误的 total_applications 作为活跃用户数"

    def test_admin_app_has_total_members(self):
        """管理端统计 API 应返回 total_members 字段"""
        content = read_file('business-admin/app.py')
        assert 'total_members' in content, \
            "管理端统计 API 缺少 total_members 字段"
