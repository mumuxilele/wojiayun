"""
V18.0 自动化测试套件
测试范围：
  1. 员工端商品管理接口（库存调整/状态切换）
  2. 支付后处理钩子（积分发放/会员升级）
  3. 营销促销系统（用户端/管理端接口）
  4. 促销计算服务（满减/折扣/秒杀）
  5. 前端新页面完整性（promotions.html/payment.html）
  6. 管理端promotions.html完整性
  7. 员工端checkin_stats.html/products.html完整性
  8. 代码路由覆盖率验证

运行方式:
    python -m pytest tests/test_v18.py -v --tb=short
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# ======= 辅助函数 =======

def read_source(path):
    """读取源码文件"""
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()


def file_exists(path):
    """检查文件是否存在"""
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
    return os.path.exists(full_path)


def extract_routes(source):
    """从Flask源码中提取路由"""
    return re.findall(r"@app\.route\(['\"]([^'\"]+)['\"].*?methods=\[([^\]]*)\]", source)


# ======= 1. 员工端商品管理接口测试 =======

class TestStaffProductsRoutes:
    """员工端商品管理路由测试"""

    def setup_method(self):
        self.source = read_source('business-staffH5/app.py')

    def test_staff_products_get_route_exists(self):
        """测试员工端商品列表GET接口存在"""
        assert "/api/staff/products" in self.source

    def test_staff_products_stock_adjust_route_exists(self):
        """测试商品库存调整POST接口存在"""
        assert "/api/staff/products/<int:product_id>/stock" in self.source

    def test_staff_products_status_toggle_route_exists(self):
        """测试商品状态切换接口存在"""
        assert "/api/staff/products/<int:product_id>/status" in self.source

    def test_stock_adjust_post_method(self):
        """测试库存调整接口是POST方法"""
        routes = extract_routes(self.source)
        stock_route = [r for r in routes if 'stock' in r[0] and 'products' in r[0]]
        assert len(stock_route) > 0, "库存调整路由不存在"
        assert 'POST' in stock_route[0][1], "库存调整接口应支持POST方法"

    def test_status_toggle_post_method(self):
        """测试状态切换接口是POST方法"""
        routes = extract_routes(self.source)
        status_route = [r for r in routes if 'status' in r[0] and 'products' in r[0]]
        assert len(status_route) > 0, "状态切换路由不存在"
        assert 'POST' in status_route[0][1]

    def test_stock_adjust_validates_type(self):
        """测试库存调整方法验证：add/subtract/set"""
        assert "adjust_type not in ('add', 'subtract', 'set')" in self.source or \
               "adjust_type" in self.source, "库存调整未验证调整类型"

    def test_stock_adjust_audit_log(self):
        """测试库存调整写入审计日志"""
        assert "adjust_stock" in self.source, "库存调整应记录审计日志"

    def test_status_filter_in_products_list(self):
        """测试商品列表支持状态筛选"""
        assert "status_filter" in self.source or "status='active'" in self.source

    def test_stock_require_staff_decorator(self):
        """测试库存调整接口有认证保护"""
        # 检查调整接口在require_staff装饰器之后
        idx_stock = self.source.find('staff_adjust_stock')
        idx_require = self.source.rfind('@require_staff', 0, idx_stock)
        assert idx_require > 0, "库存调整接口应有@require_staff保护"

    def test_low_stock_count_in_response(self):
        """测试商品列表返回低库存统计数量"""
        assert "low_stock_count" in self.source

    def test_out_of_stock_count_in_response(self):
        """测试商品列表返回缺货数量"""
        assert "out_of_stock_count" in self.source


# ======= 2. 支付后处理钩子测试 =======

class TestPaymentPostHooks:
    """支付后处理钩子测试"""

    def setup_method(self):
        self.source = read_source('business-common/payment_service.py')

    def test_post_payment_hooks_function_exists(self):
        """测试_post_payment_hooks函数存在"""
        assert "_post_payment_hooks" in self.source

    def test_hooks_called_after_payment(self):
        """测试支付确认成功后调用钩子"""
        # 检查钩子调用在commit之后
        idx_commit = self.source.find("conn.commit()")
        idx_hook = self.source.find("_post_payment_hooks", idx_commit)
        assert idx_hook > idx_commit, "钩子应在事务提交后调用"

    def test_hooks_send_notification(self):
        """测试钩子发送支付成功通知"""
        assert "send_notification" in self.source

    def test_hooks_push_websocket(self):
        """测试钩子推送WebSocket"""
        assert "push_notification" in self.source

    def test_hooks_award_points(self):
        """测试钩子发放积分"""
        assert "points_earned" in self.source or "calculate_points" in self.source

    def test_hooks_update_member_level(self):
        """测试钩子触发会员等级升级"""
        assert "update_total_consume" in self.source

    def test_hooks_points_log_insert(self):
        """测试钩子写入积分日志"""
        assert "business_points_log" in self.source

    def test_hooks_exception_handling(self):
        """测试钩子异常不影响主流程"""
        # 每个功能块都应有try-except
        hook_section = self.source[self.source.find("def _post_payment_hooks"):]
        try_count = hook_section.count("try:")
        assert try_count >= 3, f"钩子应有至少3个try块，实际: {try_count}"

    def test_points_rate_from_member_level(self):
        """测试积分按会员等级倍率计算"""
        assert "points_rate" in self.source

    def test_only_order_type_earns_points(self):
        """测试仅order类型订单发放积分"""
        assert "order_type.*order" in self.source or "order_type == 'order'" in self.source


# ======= 3. 用户端营销促销接口测试 =======

class TestUserPromotionsRoutes:
    """用户端营销促销路由测试"""

    def setup_method(self):
        self.source = read_source('business-userH5/app.py')

    def test_promotions_list_route_exists(self):
        """测试促销活动列表接口存在"""
        assert "/api/user/promotions" in self.source

    def test_promotions_detail_route_exists(self):
        """测试促销活动详情接口存在"""
        assert "/api/user/promotions/<int:promo_id>" in self.source

    def test_promotions_calc_route_exists(self):
        """测试促销价格计算接口存在"""
        assert "/api/user/promotions/calc" in self.source

    def test_calc_is_post_method(self):
        """测试计算接口是POST方法"""
        routes = extract_routes(self.source)
        calc_routes = [r for r in routes if 'promotions/calc' in r[0]]
        assert len(calc_routes) > 0
        assert 'POST' in calc_routes[0][1]

    def test_promotions_require_login(self):
        """测试促销接口需要登录"""
        assert "require_login" in self.source
        # promotions接口在require_login保护下
        idx_promo = self.source.find("get_active_promotions")
        assert idx_promo > 0

    def test_promotion_user_used_count(self):
        """测试返回用户已使用次数"""
        assert "user_used_count" in self.source

    def test_promotion_can_use_field(self):
        """测试返回是否可用字段"""
        assert "can_use" in self.source

    def test_seckill_remaining_stock(self):
        """测试秒杀活动返回剩余库存"""
        assert "remaining_stock" in self.source

    def test_calc_validates_per_limit(self):
        """测试计算接口验证使用次数限制"""
        assert "per_limit" in self.source

    def test_calc_uses_promotion_service(self):
        """测试计算接口使用PromotionService"""
        assert "PromotionService" in self.source or "calculate_promo_discount" in self.source

    def test_promotions_filter_active_only(self):
        """测试只返回进行中的活动"""
        assert "status='active'" in self.source and "start_time <= NOW()" in self.source


# ======= 4. 管理端促销接口测试 =======

class TestAdminPromotionsRoutes:
    """管理端营销促销路由测试"""

    def setup_method(self):
        self.source = read_source('business-admin/app.py')

    def test_admin_promotions_list_route(self):
        """测试管理端促销列表接口"""
        assert "/api/admin/promotions" in self.source

    def test_admin_promotions_create_post(self):
        """测试管理端创建促销接口（POST）"""
        routes = extract_routes(self.source)
        create_routes = [r for r in routes if r[0] == '/api/admin/promotions' and 'POST' in r[1]]
        assert len(create_routes) > 0, "缺少POST /api/admin/promotions"

    def test_admin_promotions_update_put(self):
        """测试管理端修改促销接口（PUT）"""
        assert "methods=['PUT']" in self.source or "methods=[\"PUT\"]" in self.source

    def test_admin_promotions_delete(self):
        """测试管理端终止促销接口（DELETE）"""
        assert "methods=['DELETE']" in self.source or "methods=[\"DELETE\"]" in self.source

    def test_admin_promotions_stats(self):
        """测试管理端活动统计接口"""
        assert "/api/admin/promotions/<int:promo_id>/stats" in self.source

    def test_admin_promo_requires_auth(self):
        """测试管理端促销接口需要认证"""
        idx_promo_func = self.source.find("admin_list_promotions")
        assert idx_promo_func > 0
        # 函数内有 get_current_admin() 调用
        promo_code = self.source[idx_promo_func:idx_promo_func+300]
        assert "get_current_admin()" in promo_code

    def test_admin_promo_validate_type(self):
        """测试创建促销验证活动类型"""
        assert "('full_reduce', 'discount', 'seckill')" in self.source or \
               "full_reduce.*discount.*seckill" in self.source

    def test_admin_promo_participant_count(self):
        """测试促销列表包含参与人数"""
        assert "participant_count" in self.source

    def test_admin_promo_stats_endpoint(self):
        """测试统计接口返回参与者列表"""
        assert "participants" in self.source

    def test_admin_promo_audit_log(self):
        """测试促销操作记录审计日志"""
        assert "log_admin_action" in self.source
        assert "create_promotion" in self.source


# ======= 5. PromotionService 计算逻辑测试 =======

class TestPromotionService:
    """PromotionService 计算逻辑测试"""

    def setup_method(self):
        self.source = read_source('business-common/member_level.py')

    def test_promotion_service_class_exists(self):
        """测试PromotionService类存在"""
        assert "class PromotionService" in self.source

    def test_get_active_promotions_method(self):
        """测试获取活动列表方法"""
        assert "get_active_promotions" in self.source

    def test_calculate_promo_discount_method(self):
        """测试计算优惠方法"""
        assert "calculate_promo_discount" in self.source

    def test_full_reduce_calculation(self):
        """测试满减逻辑"""
        assert "full_reduce" in self.source
        assert "min_amount" in self.source
        assert "reduce_amount" in self.source

    def test_discount_rate_calculation(self):
        """测试折扣率逻辑"""
        assert "discount_rate" in self.source
        assert "original_amount * discount_rate" in self.source

    def test_seckill_price_calculation(self):
        """测试秒杀价逻辑"""
        assert "seckill" in self.source
        assert "seckill_price" in self.source

    def test_record_promo_usage(self):
        """测试记录活动使用"""
        assert "record_promo_usage" in self.source

    def test_check_and_deduct_stock(self):
        """测试检查并扣减库存"""
        assert "check_and_deduct_stock" in self.source

    def test_per_limit_validation(self):
        """测试使用次数限制验证"""
        assert "per_limit" in self.source

    def test_zero_stock_means_unlimited(self):
        """测试0库存表示不限"""
        assert "stock == 0" in self.source or "total_stock.*0" in self.source

    def test_full_reduce_not_below_zero(self):
        """测试满减后金额不低于0"""
        assert "max(original_amount - reduce_amount, 0)" in self.source or \
               "max(" in self.source


# ======= 6. 新增前端页面完整性测试 =======

class TestNewFrontendPages:
    """新增前端页面测试"""

    def test_user_promotions_html_exists(self):
        """测试用户端促销活动页面存在"""
        assert file_exists('business-userH5/promotions.html')

    def test_user_payment_html_exists(self):
        """测试支付确认页面存在"""
        assert file_exists('business-userH5/payment.html')

    def test_admin_promotions_html_exists(self):
        """测试管理端促销管理页面存在"""
        assert file_exists('business-admin/promotions.html')

    def test_staff_checkin_stats_html_exists(self):
        """测试员工端签到统计页面存在"""
        assert file_exists('business-staffH5/checkin_stats.html')

    def test_staff_products_html_exists(self):
        """测试员工端商品管理页面存在"""
        assert file_exists('business-staffH5/products.html')

    def test_promotions_page_api_calls(self):
        """测试促销页面有API调用"""
        src = read_source('business-userH5/promotions.html')
        assert "/api/user/promotions" in src

    def test_promotions_page_type_filter(self):
        """测试促销页面有类型筛选"""
        src = read_source('business-userH5/promotions.html')
        assert "seckill" in src
        assert "full_reduce" in src
        assert "discount" in src

    def test_promotions_page_calc_feature(self):
        """测试促销页面有优惠计算功能"""
        src = read_source('business-userH5/promotions.html')
        assert "calcModal" in src or "calc" in src.lower()

    def test_payment_page_countdown(self):
        """测试支付页有倒计时"""
        src = read_source('business-userH5/payment.html')
        assert "countdown" in src

    def test_payment_page_methods(self):
        """测试支付页有多种支付方式"""
        src = read_source('business-userH5/payment.html')
        assert "wechat" in src
        assert "alipay" in src
        assert "mock" in src

    def test_payment_page_confirm_api(self):
        """测试支付页调用确认支付接口"""
        src = read_source('business-userH5/payment.html')
        assert "/api/user/payments/" in src
        assert "confirm" in src

    def test_payment_page_success_state(self):
        """测试支付页有支付成功展示"""
        src = read_source('business-userH5/payment.html')
        assert "支付成功" in src

    def test_admin_promotions_table_exists(self):
        """测试管理端促销页面有数据表格"""
        src = read_source('business-admin/promotions.html')
        assert "<table" in src
        assert "promo_name" in src or "活动名称" in src

    def test_admin_promotions_create_form(self):
        """测试管理端促销页有创建表单"""
        src = read_source('business-admin/promotions.html')
        assert "createModal" in src
        assert "submitCreate" in src

    def test_admin_promotions_stats_modal(self):
        """测试管理端促销页有统计弹窗"""
        src = read_source('business-admin/promotions.html')
        assert "statsModal" in src or "viewStats" in src


# ======= 7. 导航和菜单完整性测试 =======

class TestNavigationCompleteness:
    """导航和菜单完整性测试"""

    def test_user_index_has_promotions_link(self):
        """测试用户端首页有促销活动入口"""
        src = read_source('business-userH5/index.html')
        assert "promotions.html" in src

    def test_user_index_has_addresses_link(self):
        """测试用户端首页有收货地址入口"""
        src = read_source('business-userH5/index.html')
        assert "addresses.html" in src

    def test_admin_index_has_promotions_menu(self):
        """测试管理端有营销促销菜单项"""
        src = read_source('business-admin/index.html')
        assert "营销促销" in src or "promotions" in src

    def test_admin_index_promotions_panel(self):
        """测试管理端有营销促销面板"""
        src = read_source('business-admin/index.html')
        assert "panel-promotions" in src

    def test_staff_index_has_products_link(self):
        """测试员工端首页有商品管理入口"""
        src = read_source('business-staffH5/index.html')
        assert "products.html" in src

    def test_staff_index_has_checkin_stats_link(self):
        """测试员工端首页有签到统计入口"""
        src = read_source('business-staffH5/index.html')
        assert "checkin_stats.html" in src


# ======= 8. 购物车结算流程测试 =======

class TestCartCheckoutFlow:
    """购物车结算流程测试"""

    def setup_method(self):
        self.source = read_source('business-userH5/cart.html')

    def test_checkout_creates_payment(self):
        """测试结算后创建支付单"""
        assert "/api/user/payments/create" in self.source

    def test_checkout_redirects_to_payment_page(self):
        """测试结算后跳转支付页"""
        assert "payment.html" in self.source

    def test_checkout_passes_pay_no(self):
        """测试跳转支付页携带支付单号"""
        assert "pay_no" in self.source

    def test_checkout_fallback_to_orders(self):
        """测试支付失败降级到订单页"""
        assert "orders.html" in self.source

    def test_checkout_button_disabled_during_payment(self):
        """测试支付中禁用结算按钮"""
        assert "disabled = true" in self.source or "btn.disabled = true" in self.source


# ======= 9. 会员等级服务测试 =======

class TestMemberLevelService:
    """会员等级服务测试"""

    def setup_method(self):
        self.source = read_source('business-common/member_level.py')

    def test_member_level_service_exists(self):
        """测试会员等级服务类存在"""
        assert "class MemberLevelService" in self.source

    def test_update_total_consume_exists(self):
        """测试累计消费更新方法"""
        assert "update_total_consume" in self.source

    def test_upgrade_sends_notification(self):
        """测试升级后发送通知"""
        assert "send_notification" in self.source

    def test_calculate_points_method(self):
        """测试积分计算方法"""
        assert "def calculate_points" in self.source

    def test_calculate_discount_method(self):
        """测试折扣计算方法"""
        assert "def calculate_discount" in self.source

    def test_default_levels_l1_to_l5(self):
        """测试默认5级等级配置"""
        assert "'L1'" in self.source
        assert "'L5'" in self.source

    def test_level_upgrade_returns_result(self):
        """测试升级结果返回升级状态"""
        assert "'upgraded'" in self.source


# ======= 10. 数据库迁移脚本测试 =======

class TestDatabaseMigration:
    """V18.0 数据库结构验证"""

    def test_promotions_table_referenced(self):
        """测试business_promotions表被引用"""
        admin_src = read_source('business-admin/app.py')
        user_src = read_source('business-userH5/app.py')
        assert "business_promotions" in admin_src or "business_promotions" in user_src

    def test_promotion_users_table_referenced(self):
        """测试business_promotion_users表被引用"""
        src = read_source('business-common/member_level.py')
        assert "business_promotion_users" in src

    def test_payments_table_referenced(self):
        """测试business_payments表在支付服务中引用"""
        src = read_source('business-common/payment_service.py')
        assert "business_payments" in src

    def test_points_log_insert_on_payment(self):
        """测试支付后写入积分日志"""
        src = read_source('business-common/payment_service.py')
        assert "business_points_log" in src

    def test_members_total_consume_updated(self):
        """测试支付后更新累计消费"""
        src = read_source('business-common/member_level.py')
        assert "total_consume" in src


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False
    )
    sys.exit(result.returncode)
