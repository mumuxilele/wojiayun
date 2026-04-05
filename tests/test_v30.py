#!/usr/bin/env python3
"""
V30.0 自动化测试
测试内容：
  1. 结算确认页后端参数校验（checkout 流程）
  2. 物流追踪接口（order_tracking）
  3. 员工端评价管理（列表、统计、回复、删除）
  4. 管理端会员画像接口
  5. 优惠券定向发放（预估人数、定向发放）
  6. 迁移脚本幂等性验证
"""
import sys, os, json, re, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# 1. 结构验证（无数据库依赖）
# ============================================================

class TestCheckoutPageStructure(unittest.TestCase):
    """验证 checkout.html 页面结构"""

    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.html_path = os.path.join(base, 'business-userH5', 'checkout.html')

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.html_path), "checkout.html 文件不存在")

    def test_addr_selection(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('openAddrSheet', content, "应有收货地址选择函数")
        self.assertIn('addrContent', content, "应有地址展示区域")

    def test_coupon_selection(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('openCouponSheet', content, "应有优惠券选择函数")
        self.assertIn('recalcAmount', content, "应有价格重算函数")

    def test_submit_order(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('submitOrder', content, "应有提交订单函数")
        self.assertIn('/api/user/orders', content, "应调用下单接口")

    def test_supports_cart_and_direct_buy(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('cart_ids', content, "应支持购物车下单")
        self.assertIn('directProductId', content, "应支持直接购买")


class TestOrderTrackingStructure(unittest.TestCase):
    """验证 order_tracking.html 页面结构"""

    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.html_path = os.path.join(base, 'business-userH5', 'order_tracking.html')

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.html_path), "order_tracking.html 文件不存在")

    def test_status_map(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for status in ['shipped', 'completed', 'cancelled']:
            self.assertIn(status, content, f"应包含 {status} 状态映射")

    def test_logistics_api_call(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('/api/user/orders/', content, "应调用订单接口")
        self.assertIn('/logistics', content, "应调用物流接口")

    def test_timeline_rendering(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('timeline', content, "应有时间线样式")
        self.assertIn('traces', content, "应渲染物流轨迹")

    def test_copy_tracking_no(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('copyText', content, "应有复制快递单号功能")


class TestStaffReviewsStructure(unittest.TestCase):
    """验证员工端 reviews.html 页面结构"""

    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.html_path = os.path.join(base, 'business-staffH5', 'reviews.html')

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.html_path), "reviews.html 文件不存在")

    def test_statistics_section(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('statTotal', content, "应有总评价数统计")
        self.assertIn('statAvg', content, "应有平均评分统计")
        self.assertIn('statUnreplied', content, "应有待回复数统计")

    def test_filter_functions(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('filterByStatus', content, "应有状态过滤函数")
        self.assertIn('loadReviews', content, "应有加载评价函数")

    def test_reply_modal(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('openReplyModal', content, "应有打开回复弹窗函数")
        self.assertIn('submitReply', content, "应有提交回复函数")
        self.assertIn('/api/staff/reviews/', content, "应调用评价API")

    def test_rating_distribution(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('star-bar', content, "应有评分分布条形图")
        self.assertIn('rating_distribution', content, "应处理评分分布数据")


class TestMemberProfileStructure(unittest.TestCase):
    """验证管理端 member-profile.html 页面结构"""

    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.html_path = os.path.join(base, 'business-admin', 'member-profile.html')

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.html_path), "member-profile.html 文件不存在")

    def test_echarts_integration(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('echarts', content, "应集成 ECharts")
        self.assertIn('renderConsumeChart', content, "应有消费趋势图")
        self.assertIn('renderCategoryChart', content, "应有品类偏好图")

    def test_member_info_sections(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for key in ['order_stats', 'points_stats', 'checkin_stats', 'achievements', 'tags', 'recently_viewed']:
            self.assertIn(key, content, f"应包含 {key} 数据段")

    def test_api_call(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('/api/admin/users/', content, "应调用会员画像API")
        self.assertIn('/profile', content, "应调用 /profile 端点")

    def test_level_badges(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for lv in ['bronze', 'silver', 'gold', 'platinum', 'diamond']:
            self.assertIn(lv, content, f"应包含 {lv} 等级映射")


# ============================================================
# 2. 后端接口结构验证
# ============================================================

class TestAdminBackendV30Structure(unittest.TestCase):
    """验证管理端后端 V30.0 新增接口"""

    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.app_path = os.path.join(base, 'business-admin', 'app.py')
        with open(self.app_path, 'r', encoding='utf-8') as f:
            self.content = f.read()

    def test_member_profile_route(self):
        self.assertIn("'/api/admin/users/<int:user_id>/profile'", self.content,
                      "应有会员画像接口路由")

    def test_profile_includes_order_stats(self):
        self.assertIn('order_stats', self.content, "画像接口应返回订单统计")

    def test_profile_includes_checkin(self):
        self.assertIn('checkin_stats', self.content, "画像接口应返回签到统计")

    def test_targeted_coupon_route(self):
        self.assertIn("'/api/admin/coupons/<coupon_id>/targeted-issue'", self.content,
                      "应有定向发放接口路由")

    def test_target_preview_route(self):
        self.assertIn("'/api/admin/coupons/target-preview'", self.content,
                      "应有预估人数接口路由")

    def test_targeted_coupon_level_filter(self):
        self.assertIn('level_list', self.content, "定向发放应支持等级筛选")

    def test_targeted_coupon_consume_filter(self):
        self.assertIn('min_total_consume', self.content, "定向发放应支持消费区间筛选")

    def test_targeted_coupon_streak_filter(self):
        self.assertIn('min_checkin_streak', self.content, "定向发放应支持签到活跃度筛选")

    def test_targeted_coupon_inactive_filter(self):
        self.assertIn('inactive_days', self.content, "定向发放应支持沉睡用户筛选")

    def test_send_notification_on_grant(self):
        self.assertIn('send_notification', self.content, "定向发放应推送站内通知")


class TestStaffBackendV30Structure(unittest.TestCase):
    """验证员工端后端评价管理接口"""

    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.app_path = os.path.join(base, 'business-staffH5', 'app.py')
        with open(self.app_path, 'r', encoding='utf-8') as f:
            self.content = f.read()

    def test_reviews_list_route(self):
        self.assertIn("'/api/staff/reviews'", self.content, "应有评价列表接口")

    def test_reviews_reply_route(self):
        self.assertIn("'/api/staff/reviews/<int:review_id>/reply'", self.content, "应有评价回复接口")

    def test_reviews_statistics_route(self):
        self.assertIn("'/api/staff/reviews/statistics'", self.content, "应有评价统计接口")

    def test_reviews_delete_route(self):
        self.assertIn("'/api/staff/reviews/<int:review_id>'", self.content, "应有删除评价接口")

    def test_reply_sends_notification(self):
        self.assertIn('send_notification', self.content, "回复评价应通知用户")

    def test_reviews_filter_by_rating(self):
        self.assertIn("rating = request.args.get('rating'", self.content, "应支持按评分过滤")


class TestUserBackendV30Structure(unittest.TestCase):
    """验证用户端后端物流追踪接口"""

    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.app_path = os.path.join(base, 'business-userH5', 'app.py')
        with open(self.app_path, 'r', encoding='utf-8') as f:
            self.content = f.read()

    def test_logistics_route_exists(self):
        self.assertIn("'/api/user/orders/<int:order_id>/logistics'", self.content,
                      "应有订单物流查询接口")

    def test_checkout_order_create(self):
        self.assertIn("'/api/user/orders'", self.content, "应有下单接口")
        self.assertIn("address_id", self.content, "下单应支持地址ID")

    def test_cart_route_exists(self):
        self.assertIn("'/api/user/cart'", self.content, "应有购物车接口")

    def test_addresses_route_exists(self):
        self.assertIn("addresses", self.content, "应有收货地址接口")


# ============================================================
# 3. 迁移脚本验证
# ============================================================

class TestMigrateV30Structure(unittest.TestCase):
    """验证 V30.0 迁移脚本"""

    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.script_path = os.path.join(base, 'business-common', 'migrate_v30.py')

    def test_script_exists(self):
        self.assertTrue(os.path.exists(self.script_path), "migrate_v30.py 文件不存在")

    def test_idempotent_check(self):
        with open(self.script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('check_column_exists', content, "迁移脚本应先检查字段是否存在")
        self.assertIn('check_table_exists', content, "迁移脚本应先检查表是否存在")

    def test_new_tables_defined(self):
        with open(self.script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('business_coupon_issue_tasks', content, "应创建优惠券发放任务记录表")
        self.assertIn('business_member_achievements', content, "应建立成就徽章表")

    def test_coupon_expire_days_migration(self):
        with open(self.script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('expire_days', content, "应补充 expire_days 字段")


# ============================================================
# 4. 产品连通性测试（业务流程）
# ============================================================

class TestV30BusinessFlow(unittest.TestCase):
    """V30.0 业务流程连通性测试"""

    def test_checkout_cart_to_order_flow(self):
        """验证购物车->结算->下单的完整流程参数传递"""
        # cart.html 应向 checkout.html 传递 cart_ids
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cart_path = os.path.join(base, 'business-userH5', 'cart.html')
        with open(cart_path, 'r', encoding='utf-8') as f:
            cart_content = f.read()
        # V30.0 修改：checkout 函数应跳转 checkout.html
        self.assertIn('checkout.html', cart_content, "cart.html 应跳转到 checkout.html")
        self.assertIn('cart_ids', cart_content, "cart.html 应传递 cart_ids 参数")

    def test_orders_page_logistics_link(self):
        """验证订单页有物流追踪入口"""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        orders_path = os.path.join(base, 'business-userH5', 'orders.html')
        with open(orders_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('order_tracking.html', content, "订单页应有物流追踪链接")
        self.assertIn('查看物流', content, "应有「查看物流」按钮文字")

    def test_staff_index_has_reviews_entry(self):
        """验证员工端首页有评价管理入口"""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        idx_path = os.path.join(base, 'business-staffH5', 'index.html')
        with open(idx_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('reviews.html', content, "员工端首页应有评价管理入口")
        self.assertIn('评价管理', content, "应有评价管理文字")

    def test_admin_users_has_profile_link(self):
        """验证管理端会员列表有画像入口"""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        users_path = os.path.join(base, 'business-admin', 'users.html')
        with open(users_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('member-profile.html', content, "管理端会员列表应有画像链接")
        self.assertIn('画像', content, "应有「画像」入口文字")

    def test_coupons_page_has_targeted_issue(self):
        """验证优惠券页有定向发放入口"""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        coupons_path = os.path.join(base, 'business-admin', 'coupons.html')
        with open(coupons_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('targetedModal', content, "应有定向发放弹窗")
        self.assertIn('openTargetedModal', content, "应有打开定向发放弹窗函数")
        self.assertIn('预估覆盖人数', content, "应有预估人数功能")
        self.assertIn('level_list', content, "应有等级筛选")


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestCheckoutPageStructure,
        TestOrderTrackingStructure,
        TestStaffReviewsStructure,
        TestMemberProfileStructure,
        TestAdminBackendV30Structure,
        TestStaffBackendV30Structure,
        TestUserBackendV30Structure,
        TestMigrateV30Structure,
        TestV30BusinessFlow,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
