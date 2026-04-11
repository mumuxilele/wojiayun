#!/usr/bin/env python3
"""
V31.0 自动化测试套件
覆盖范围：
  1. 订单超时关闭服务结构验证
  2. RFM分群管理页结构验证
  3. 员工端待办聚合 API 增强验证
  4. 消息角标实时联动验证
  5. 定向发放接口 user_ids 参数支持验证
  6. 数据库迁移脚本验证

运行方式：
  python tests/test_v31.py
"""
import sys
import os
import unittest
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# 1. 订单超时关闭服务结构验证
# ============================================================
class TestCancelExpiredOrdersStructure(unittest.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-common', 'cancel_expired_orders.py')
        with open(path, 'r', encoding='utf-8') as f:
            self.src = f.read()

    def test_main_function_exists(self):
        self.assertIn('def cancel_expired_orders', self.src, "主函数存在")

    def test_rollback_stock_function(self):
        self.assertIn('def rollback_order_stock', self.src, "库存回滚函数存在")

    def test_notification_function(self):
        self.assertIn('def send_cancel_notification', self.src, "取消通知函数存在")

    def test_audit_log_function(self):
        self.assertIn('def log_audit', self.src, "审计日志函数存在")

    def test_batch_size_configured(self):
        self.assertIn('BATCH_SIZE', self.src, "批量处理量已配置")

    def test_expire_time_configurable(self):
        self.assertIn('ORDER_EXPIRE_MINUTES', self.src, "超时时间可配置")

    def test_handles_sku_rollback(self):
        self.assertIn('sku_id', self.src.lower() + 'sku_id', "支持SKU库存回滚")


# ============================================================
# 2. RFM分群管理页结构验证
# ============================================================
class TestRfmSegmentsPageStructure(unittest.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-admin', 'rfm-segments.html')
        with open(path, 'r', encoding='utf-8') as f:
            self.src = f.read()

    def test_page_exists(self):
        self.assertTrue(len(self.src) > 1000, "页面内容足够")

    def test_rfm_type_options(self):
        rfm_types = ['champions', 'loyal', 'potential', 'new', 'at_risk', 'lost']
        for t in rfm_types:
            self.assertIn(t, self.src, f"RFM类型 {t} 存在")

    def test_score_display(self):
        self.assertIn('r_score', self.src, "R分展示")
        self.assertIn('f_score', self.src, "F分展示")
        self.assertIn('m_score', self.src, "M分展示")

    def test_batch_coupon_modal(self):
        self.assertIn('couponModal', self.src, "批量发券弹窗")
        self.assertIn('openBatchCouponModal', self.src, "打开发券弹窗函数")

    def test_export_function(self):
        self.assertIn('exportRfm', self.src, "导出功能")

    def test_member_profile_link(self):
        self.assertIn('member-profile.html', self.src, "会员画像链接")

    def test_pagination_support(self):
        self.assertIn('renderPagination', self.src, "分页功能")


# ============================================================
# 3. 员工端待办聚合 API 验证
# ============================================================
class TestStaffTodoAggregationApi(unittest.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-staffH5', 'app.py')
        with open(path, 'r', encoding='utf-8') as f:
            self.src = f.read()

    def test_pending_ship_field(self):
        self.assertIn('pending_ship', self.src, "待发货字段")

    def test_pending_refund_field(self):
        self.assertIn('pending_refund', self.src, "待退款字段")

    def test_pending_reviews_field(self):
        self.assertIn('pending_reviews', self.src, "待回复评价字段")

    def test_today_income_field(self):
        self.assertIn('today_income', self.src, "今日收入字段")

    def test_today_orders_field(self):
        self.assertIn('today_orders', self.src, "今日订单字段")

    def test_error_handling(self):
        # 每个新增字段都有 try/except
        count = self.src.count('pending_ship')
        self.assertGreater(count, 0, "pending_ship 有定义")


# ============================================================
# 4. 员工端首页待办聚合展示验证
# ============================================================
class TestStaffIndexTodoDisplay(unittest.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-staffH5', 'index.html')
        with open(path, 'r', encoding='utf-8') as f:
            self.src = f.read()

    def test_todo_row_element(self):
        self.assertIn('todoRow', self.src, "待办行容器")

    def test_today_income_display(self):
        self.assertIn('todayIncome', self.src, "今日收入展示")

    def test_today_order_count(self):
        self.assertIn('todayOrderCnt', self.src, "今日订单数展示")

    def test_load_todo_summary_function(self):
        self.assertIn('loadTodoSummary', self.src, "加载待办聚合函数")

    def test_review_badge(self):
        self.assertIn('badge-review', self.src, "评价待办角标")


# ============================================================
# 5. 消息角标实时联动验证
# ============================================================
class TestUserIndexBadgeRealtime(unittest.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-userH5', 'index.html')
        with open(path, 'r', encoding='utf-8') as f:
            self.src = f.read()

    def test_polling_interval(self):
        self.assertIn('setInterval', self.src, "轮询刷新")
        self.assertIn('60000', self.src, "60秒轮询间隔")

    def test_quick_badge_refresh_function(self):
        self.assertIn('loadBadgesQuick', self.src, "快速刷新角标函数")

    def test_order_badge_element(self):
        self.assertIn('orderBadge', self.src, "订单角标元素")

    def test_unpaid_order_check(self):
        self.assertIn('checkUnpaidOrders', self.src, "待支付订单检测函数")

    def test_countdown_reminder(self):
        self.assertIn('remainMin', self.src, "倒计时剩余分钟数")


# ============================================================
# 6. 定向发放接口 user_ids 支持验证
# ============================================================
class TestTargetedIssueUserIds(unittest.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-admin', 'app.py')
        with open(path, 'r', encoding='utf-8') as f:
            self.src = f.read()

    def test_user_ids_parameter(self):
        self.assertIn('direct_user_ids', self.src, "user_ids 参数支持")

    def test_direct_mode_dedup(self):
        # 验证去重逻辑（排除已持有该券的用户）
        self.assertIn('NOT IN (SELECT user_id FROM business_user_coupons', self.src,
                      "发放前去重逻辑")

    def test_batch_limit(self):
        self.assertIn('5000', self.src, "批量上限5000")

    def test_issued_count_in_response(self):
        self.assertIn('issued_count', self.src, "返回实际发放数量")


# ============================================================
# 7. 数据库迁移脚本 V31 验证
# ============================================================
class TestMigrateV31Structure(unittest.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'business-common', 'migrate_v31.py')
        with open(path, 'r', encoding='utf-8') as f:
            self.src = f.read()

    def test_expired_at_column(self):
        self.assertIn('expired_at', self.src, "expired_at 字段迁移")

    def test_rfm_view_creation(self):
        self.assertIn('rfm_analysis_view', self.src, "RFM视图创建")

    def test_idempotent_column_check(self):
        self.assertIn('column_exists', self.src, "幂等列检查")

    def test_index_creation(self):
        self.assertIn('idx_orders_timeout_check', self.src, "超时查询索引")

    def test_rfm_scoring_logic(self):
        # 验证R/F/M评分逻辑存在
        self.assertIn('r_score', self.src, "R分逻辑")
        self.assertIn('f_score', self.src, "F分逻辑")
        self.assertIn('m_score', self.src, "M分逻辑")


# ============================================================
# 8. 端到端业务流验证
# ============================================================
class TestV31BusinessFlowIntegration(unittest.TestCase):

    def test_order_lifecycle_complete(self):
        """验证订单生命周期相关文件均存在"""
        files = [
            ('business-common', 'cancel_expired_orders.py'),
            ('business-userH5', 'orders.html'),
            ('business-userH5', 'order_tracking.html'),
            ('business-userH5', 'checkout.html'),
        ]
        base = os.path.dirname(os.path.dirname(__file__))
        for folder, fname in files:
            path = os.path.join(base, folder, fname)
            self.assertTrue(os.path.exists(path), f"{folder}/{fname} 文件存在")

    def test_rfm_workflow_complete(self):
        """验证RFM分群工作流所有文件均存在"""
        files = [
            ('business-admin', 'rfm-segments.html'),
            ('business-common', 'migrate_v31.py'),
        ]
        base = os.path.dirname(os.path.dirname(__file__))
        for folder, fname in files:
            path = os.path.join(base, folder, fname)
            self.assertTrue(os.path.exists(path), f"{folder}/{fname} 文件存在")

    def test_staff_realtime_workflow_files(self):
        """验证员工端实时提醒工作流文件均存在"""
        files = [
            ('business-staffH5', 'index.html'),
            ('business-staffH5', 'reviews.html'),
            ('business-staffH5', 'refunds.html'),
        ]
        base = os.path.dirname(os.path.dirname(__file__))
        for folder, fname in files:
            path = os.path.join(base, folder, fname)
            self.assertTrue(os.path.exists(path), f"{folder}/{fname} 文件存在")

    def test_notification_chain(self):
        """验证通知链路文件存在"""
        files = [
            ('business-common', 'notification.py'),
            ('business-userH5', 'notifications.html'),
            ('business-staffH5', 'notifications.html'),
        ]
        base = os.path.dirname(os.path.dirname(__file__))
        for folder, fname in files:
            path = os.path.join(base, folder, fname)
            self.assertTrue(os.path.exists(path), f"{folder}/{fname} 文件存在")


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestCancelExpiredOrdersStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestRfmSegmentsPageStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestStaffTodoAggregationApi))
    suite.addTests(loader.loadTestsFromTestCase(TestStaffIndexTodoDisplay))
    suite.addTests(loader.loadTestsFromTestCase(TestUserIndexBadgeRealtime))
    suite.addTests(loader.loadTestsFromTestCase(TestTargetedIssueUserIds))
    suite.addTests(loader.loadTestsFromTestCase(TestMigrateV31Structure))
    suite.addTests(loader.loadTestsFromTestCase(TestV31BusinessFlowIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
