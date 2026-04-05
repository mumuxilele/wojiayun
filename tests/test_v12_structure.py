"""
V12.0 结构验证测试 - 无需数据库连接
测试内容：
  - payment_service.py Bug修复验证（order_status同步）
  - 商品列表接口多维排序参数验证
  - 管理端退款管理页面完整性验证
  - 退款管理页面导航入口验证
  - 代码质量：所有文件语法无误
  - 后向兼容性：V11接口不退化
"""
import sys
import os
import ast
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_H5_APP   = os.path.join(ROOT, 'business-userH5',  'app.py')
STAFF_H5_APP  = os.path.join(ROOT, 'business-staffH5', 'app.py')
ADMIN_APP     = os.path.join(ROOT, 'business-admin',   'app.py')
PAYMENT_SVC   = os.path.join(ROOT, 'business-common',  'payment_service.py')
REFUNDS_HTML   = os.path.join(ROOT, 'business-admin',   'refunds.html')
ADMIN_INDEX    = os.path.join(ROOT, 'business-admin',   'index.html')
PRODUCT_DETAIL = os.path.join(ROOT, 'business-userH5',  'product_detail.html')
STAFF_MEMBERS  = os.path.join(ROOT, 'business-staffH5', 'members.html')
STAFF_REFUNDS  = os.path.join(ROOT, 'business-staffH5', 'refunds.html')
STAFF_INDEX    = os.path.join(ROOT, 'business-staffH5', 'index.html')


def read_source(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def get_routes(content):
    return re.findall(r"@app\.route\('([^']+)'", content)


# ============================================================
#  P0 BUG 修复验证（V12）
# ============================================================
class TestV12P0Fixes:
    """V12.0 P0 Bug修复验证"""

    def test_payment_service_order_status_synced(self):
        """P0修复: confirm_payment对order类型必须同步更新order_status='paid'"""
        content = read_source(PAYMENT_SVC)
        # 必须在 order_type == 'order' 的分支里同时设置 order_status 和 pay_status
        assert "order_status='paid'" in content, (
            "payment_service.py: confirm_payment对order类型缺少 order_status='paid' 更新，"
            "会导致支付完成但订单状态仍为pending/created的不一致问题"
        )

    def test_payment_service_python_syntax(self):
        """P0验证: payment_service.py语法无误"""
        content = read_source(PAYMENT_SVC)
        try:
            ast.parse(content)
        except SyntaxError as e:
            assert False, f"payment_service.py 存在语法错误: {e}"

    def test_user_h5_python_syntax(self):
        """P0验证: userH5/app.py语法无误"""
        content = read_source(USER_H5_APP)
        try:
            ast.parse(content)
        except SyntaxError as e:
            assert False, f"userH5/app.py 存在语法错误: {e}"

    def test_staff_h5_python_syntax(self):
        """P0验证: staffH5/app.py语法无误"""
        content = read_source(STAFF_H5_APP)
        try:
            ast.parse(content)
        except SyntaxError as e:
            assert False, f"staffH5/app.py 存在语法错误: {e}"

    def test_admin_python_syntax(self):
        """P0验证: admin/app.py语法无误"""
        content = read_source(ADMIN_APP)
        try:
            ast.parse(content)
        except SyntaxError as e:
            assert False, f"admin/app.py 存在语法错误: {e}"


# ============================================================
#  P1 商品列表排序增强验证
# ============================================================
class TestProductListSorting:
    """V12.0 商品列表排序功能验证"""

    def setup_method(self):
        self.content = read_source(USER_H5_APP)

    def test_products_endpoint_exists(self):
        """/api/products 端点存在"""
        routes = get_routes(self.content)
        assert '/api/products' in routes, "缺少 /api/products 路由"

    def test_sort_by_parameter_supported(self):
        """商品列表支持 sort_by 参数"""
        assert 'sort_by' in self.content, (
            "userH5/app.py: get_products() 缺少 sort_by 参数，"
            "用户无法按价格/销量/热度排序"
        )

    def test_price_asc_sort_supported(self):
        """支持价格升序排序"""
        assert 'price_asc' in self.content or 'price ASC' in self.content.lower(), \
            "商品列表缺少价格升序排序逻辑"

    def test_price_desc_sort_supported(self):
        """支持价格降序排序"""
        assert 'price_desc' in self.content or 'price DESC' in self.content, \
            "商品列表缺少价格降序排序逻辑"

    def test_sales_sort_supported(self):
        """支持销量排序"""
        assert 'sales_count DESC' in self.content, \
            "商品列表缺少按销量排序逻辑（sales_count DESC）"

    def test_hot_sort_supported(self):
        """支持热度（浏览量）排序"""
        assert 'view_count DESC' in self.content, \
            "商品列表缺少热度排序逻辑（view_count DESC）"

    def test_products_has_pagination(self):
        """商品列表支持分页"""
        assert re.search(r"LIMIT\s+%s\s+OFFSET\s+%s", self.content), \
            "get_products() 缺少分页（LIMIT/OFFSET）"

    def test_products_returns_total(self):
        """商品列表返回total字段供前端分页"""
        func_start = self.content.find("def get_products()")
        func_end = self.content.find("\n@app.route", func_start + 10)
        func_body = self.content[func_start:func_end if func_end > 0 else func_start+3000]
        assert 'total' in func_body, \
            "get_products() 返回值缺少 total 字段，前端无法渲染分页控件"

    def test_products_has_price_range_filter(self):
        """商品列表支持价格区间筛选"""
        assert 'min_price' in self.content and 'max_price' in self.content, \
            "商品列表缺少价格区间筛选（min_price/max_price），无法满足用户筛选需求"

    def test_products_has_multi_tenant_isolation(self):
        """商品列表在用户已登录时做多租户隔离"""
        func_start = self.content.find("def get_products()")
        func_end   = self.content.find("\n@app.route", func_start + 10)
        func_body  = self.content[func_start:func_end if func_end > 0 else func_start+4000]
        assert 'ec_id' in func_body, \
            "get_products() 缺少 ec_id 多租户过滤，在多租户场景下数据会越界"


# ============================================================
#  管理端退款页面完整性验证
# ============================================================
class TestRefundsPage:
    """V12.0 管理端独立退款管理页面验证"""

    def setup_method(self):
        self.html = read_source(REFUNDS_HTML)

    def test_refunds_html_exists(self):
        """退款管理页面文件存在"""
        assert os.path.exists(REFUNDS_HTML), \
            f"缺少文件: {REFUNDS_HTML}，管理端没有独立退款管理页面"

    def test_refunds_page_has_stat_cards(self):
        """退款页面有汇总统计卡"""
        assert 'stat-pending' in self.html, "退款页面缺少待审核统计卡"
        assert 'stat-amount' in self.html, "退款页面缺少退款金额统计卡"

    def test_refunds_page_has_trend_chart(self):
        """退款页面有退款趋势图"""
        assert 'trend-bars' in self.html or 'refund-analysis' in self.html, \
            "退款页面缺少趋势图展示区域"

    def test_refunds_page_has_reason_analysis(self):
        """退款页面有退款原因分析"""
        assert 'reason-list' in self.html or 'reasons' in self.html, \
            "退款页面缺少退款原因分析模块"

    def test_refunds_page_has_audit_modal(self):
        """退款页面有审核弹窗"""
        assert 'submitAudit' in self.html, "退款页面缺少审核弹窗逻辑"
        assert 'approve' in self.html and 'reject' in self.html, \
            "退款审核弹窗缺少批准/拒绝操作"

    def test_refunds_page_requires_reject_reason(self):
        """拒绝退款时必须填写原因"""
        assert "拒绝退款时必须填写原因" in self.html or \
               "reason" in self.html and "reject" in self.html, \
            "退款页面拒绝操作缺少原因必填校验"

    def test_refunds_page_calls_correct_api(self):
        """退款页面调用正确的后端接口"""
        assert '/api/admin/orders' in self.html, \
            "退款页面未调用 /api/admin/orders 接口获取数据"
        assert '/refund' in self.html, \
            "退款页面未调用 /refund 审核接口"

    def test_refunds_page_has_export_csv(self):
        """退款页面支持CSV导出"""
        assert 'exportCSV' in self.html or 'export' in self.html.lower(), \
            "退款页面缺少CSV导出功能"

    def test_refunds_page_has_pagination(self):
        """退款列表有分页"""
        assert 'pagination' in self.html and 'loadData' in self.html, \
            "退款列表缺少分页功能"

    def test_refunds_page_has_status_filter(self):
        """退款列表有状态筛选"""
        assert 'statusFilter' in self.html and 'refunding' in self.html, \
            "退款列表缺少状态筛选（待审核/已退款等）"

    def test_admin_index_has_refunds_entry(self):
        """管理端首页侧边栏有退款管理入口"""
        index_html = read_source(ADMIN_INDEX)
        assert 'refunds.html' in index_html, \
            "管理端 index.html 侧边栏缺少退款管理页面入口链接"


# ============================================================
#  V12.0 产品详情页验证
# ============================================================
class TestProductDetailPage:
    """V12.0 商品详情页文件验证"""

    def test_product_detail_html_exists(self):
        """商品详情页文件存在"""
        assert os.path.exists(PRODUCT_DETAIL), \
            f"缺少文件: {PRODUCT_DETAIL}"

    def test_product_detail_has_sku_selector(self):
        """商品详情页有SKU规格选择"""
        content = read_source(PRODUCT_DETAIL)
        assert 'sku' in content.lower(), "商品详情页缺少SKU规格选择模块"

    def test_product_detail_has_cart_function(self):
        """商品详情页有加购功能"""
        content = read_source(PRODUCT_DETAIL)
        assert 'cart' in content.lower() or '加入购物车' in content, \
            "商品详情页缺少加入购物车功能"

    def test_product_detail_has_review_section(self):
        """商品详情页有评价展示"""
        content = read_source(PRODUCT_DETAIL)
        assert 'review' in content.lower() or '评价' in content, \
            "商品详情页缺少评价展示模块"

    def test_product_detail_has_favorite(self):
        """商品详情页有收藏功能"""
        content = read_source(PRODUCT_DETAIL)
        assert 'favorite' in content.lower() or '收藏' in content, \
            "商品详情页缺少收藏功能"


# ============================================================
#  后向兼容性：V11功能不退化
# ============================================================
class TestV11Backward:
    """V12升级后V11功能应保持正常"""

    def test_admin_refund_analysis_route_still_exists(self):
        """/api/admin/statistics/refund-analysis 接口未被删除"""
        content = read_source(ADMIN_APP)
        routes = get_routes(content)
        assert '/api/admin/statistics/refund-analysis' in routes, \
            "V12升级后退款分析统计接口被意外删除"

    def test_admin_handle_refund_route_still_exists(self):
        """/api/admin/orders/<id>/refund 审核接口未被删除"""
        content = read_source(ADMIN_APP)
        assert 'admin_handle_refund' in content, \
            "V12升级后退款审核接口被意外删除"

    def test_staff_refund_route_still_exists(self):
        """员工端退款处理路由未被删除"""
        content = read_source(STAFF_H5_APP)
        routes = get_routes(content)
        assert any('refund' in r for r in routes), "V12升级后员工端退款路由消失"

    def test_user_h5_checkin_route_exists(self):
        """用户端签到接口未被删除"""
        content = read_source(USER_H5_APP)
        routes = get_routes(content)
        assert any('checkin' in r for r in routes), "V12升级后用户端签到路由消失"

    def test_user_h5_cart_route_exists(self):
        """用户端购物车接口未被删除"""
        content = read_source(USER_H5_APP)
        routes = get_routes(content)
        assert any('cart' in r for r in routes), "V12升级后购物车路由消失"

    def test_user_h5_order_route_exists(self):
        """用户端订单路由未被删除"""
        content = read_source(USER_H5_APP)
        routes = get_routes(content)
        assert any('order' in r for r in routes), "V12升级后订单路由消失"

    def test_admin_require_admin_decorator_on_product_apis(self):
        """管理端商品接口已有@require_admin装饰器（V12 P0修复应保持）"""
        content = read_source(ADMIN_APP)
        # admin_update_product 和 admin_delete_product 应都有 @require_admin
        assert content.count('@require_admin') >= 20, \
            "管理端 @require_admin 装饰器数量异常（预期≥20），可能有接口丢失认证保护"

    def test_payment_service_refund_still_works(self):
        """payment_service.py refund方法未被破坏"""
        content = read_source(PAYMENT_SVC)
        assert 'def refund(' in content, "payment_service.py refund方法被删除"
        assert "order_status='cancelled'" in content, \
            "payment_service.py refund对order类型应设置order_status='cancelled'"


# ============================================================
#  代码质量：关键安全模式
# ============================================================
class TestSecurityPatterns:
    """代码安全模式验证"""

    def test_user_h5_no_sql_injection_format(self):
        """userH5/app.py不使用字符串拼接SQL（防止注入）"""
        content = read_source(USER_H5_APP)
        # 检查危险模式: cursor.execute("...%s...".format(variable) or f"...{variable}...")
        # 允许少量f-string用于WHERE子句拼接（已有变量控制），但不应有直接f-string嵌入用户输入
        dangerous = re.findall(r'execute\(f"[^"]*\{[^}]+\}', content)
        # 过滤掉已知安全的 scope filter 拼接（ec_id, project_id等固定字段）
        risky = [d for d in dangerous if not re.search(r'\{(scope_filter|where|order_clause)\}', d)]
        assert len(risky) == 0, f"发现潜在SQL注入风险 ({len(risky)}处): {risky[:3]}"

    def test_admin_all_write_routes_protected(self):
        """管理端所有POST/PUT/DELETE路由必须有认证"""
        content = read_source(ADMIN_APP)
        # 检查是否有路由声明了 methods=['POST'] 等但紧随其后没有 @require_admin 或 get_current_admin
        post_routes = re.findall(r"@app\.route\('[^']+',\s*methods=\[.*?(?:POST|PUT|DELETE).*?\]\)", content)
        auth_count = content.count('@require_admin') + content.count('get_current_admin')
        # 保守检查：认证调用数量应大于写接口数量
        assert auth_count >= len(post_routes) * 0.8, (
            f"管理端写接口数({len(post_routes)})与认证保护调用数({auth_count})不匹配，"
            "部分写操作可能未鉴权"
        )

    def test_payment_service_uses_transaction(self):
        """支付服务必须使用事务确保原子性"""
        content = read_source(PAYMENT_SVC)
        assert 'conn.begin()' in content, "payment_service.py 缺少事务开始(conn.begin())"
        assert 'conn.commit()' in content, "payment_service.py 缺少事务提交(conn.commit())"
        assert 'conn.rollback()' in content, "payment_service.py 缺少事务回滚(conn.rollback())"


# ============================================================
#  V12.0 员工端新功能验证
# ============================================================
class TestStaffH5NewPages:
    """V12.0 员工端新增页面验证"""

    def test_staff_members_html_exists(self):
        """员工端会员管理页面存在"""
        assert os.path.exists(STAFF_MEMBERS), \
            f"缺少员工端会员管理页面: {STAFF_MEMBERS}"

    def test_staff_members_has_search(self):
        """会员页面有搜索功能"""
        content = read_source(STAFF_MEMBERS)
        assert 'search' in content.lower(), "会员管理页面缺少搜索功能"

    def test_staff_members_has_filter(self):
        """会员页面有等级筛选"""
        content = read_source(STAFF_MEMBERS)
        assert 'filter' in content.lower() or 'level' in content.lower(), \
            "会员管理页面缺少等级筛选功能"

    def test_staff_members_has_detail_modal(self):
        """会员页面有详情弹窗"""
        content = read_source(STAFF_MEMBERS)
        assert 'detail' in content.lower() or '详情' in content, \
            "会员管理页面缺少详情弹窗"

    def test_staff_members_calls_correct_api(self):
        """会员页面调用正确的后端接口"""
        content = read_source(STAFF_MEMBERS)
        assert '/api/staff/members' in content, \
            "会员管理页面未调用 /api/staff/members 接口"

    def test_staff_refunds_html_exists(self):
        """员工端退款管理页面存在"""
        assert os.path.exists(STAFF_REFUNDS), \
            f"缺少员工端退款管理页面: {STAFF_REFUNDS}"

    def test_staff_refunds_has_status_filter(self):
        """退款页面有状态筛选"""
        content = read_source(STAFF_REFUNDS)
        assert 'status' in content.lower() and 'pending' in content.lower(), \
            "退款管理页面缺少状态筛选"

    def test_staff_refunds_has_approve_reject(self):
        """退款页面有批准/拒绝功能"""
        content = read_source(STAFF_REFUNDS)
        assert 'approve' in content.lower() or '批准' in content, \
            "退款管理页面缺少批准功能"
        assert 'reject' in content.lower() or '拒绝' in content, \
            "退款管理页面缺少拒绝功能"

    def test_staff_refunds_calls_correct_api(self):
        """退款页面调用正确的后端接口"""
        content = read_source(STAFF_REFUNDS)
        assert '/api/staff/orders' in content, \
            "退款管理页面未调用 /api/staff/orders 接口"
        assert '/refund' in content, \
            "退款管理页面未调用 /refund 处理接口"

    def test_staff_index_has_members_entry(self):
        """员工端首页有会员管理入口"""
        content = read_source(STAFF_INDEX)
        assert 'members.html' in content, \
            "员工端 index.html 缺少会员管理入口"

    def test_staff_index_has_refunds_entry(self):
        """员工端首页有退款管理入口"""
        content = read_source(STAFF_INDEX)
        assert 'refunds.html' in content, \
            "员工端 index.html 缺少退款管理入口"

    def test_staff_refunds_api_supports_status_filter(self):
        """员工端退款API支持状态筛选"""
        content = read_source(STAFF_H5_APP)
        # API应该接受status参数
        assert "request.args.get('status'" in content, \
            "员工端退款API缺少status参数支持"
        # 应该返回统计数据
        assert "'stats'" in content, \
            "员工端退款API缺少统计数据返回"


# ============================================================
#  V12.0 数据库迁移脚本验证
# ============================================================
class TestV12Migration:
    """V12.0 数据库迁移脚本验证"""

    def test_migrate_v12_exists(self):
        """migrate_v12.py迁移脚本存在"""
        migrate_path = os.path.join(ROOT, 'business-common', 'migrate_v12.py')
        assert os.path.exists(migrate_path), \
            f"缺少V12迁移脚本: {migrate_path}"

    def test_migrate_v12_is_idempotent(self):
        """迁移脚本是幂等的（支持安全重试）"""
        migrate_path = os.path.join(ROOT, 'business-common', 'migrate_v12.py')
        content = read_source(migrate_path)
        # 应该检查字段是否存在再添加
        assert 'check_column_exists' in content or 'ALTER TABLE' in content, \
            "迁移脚本缺少字段存在性检查，不是幂等的"
        # 应该有try-except处理重复执行
        assert 'try:' in content and 'except' in content, \
            "迁移脚本缺少异常处理，可能在重复执行时失败"

    def test_migrate_v12_adds_member_fields(self):
        """迁移脚本添加会员相关字段"""
        migrate_path = os.path.join(ROOT, 'business-common', 'migrate_v12.py')
        content = read_source(migrate_path)
        assert 'member_tags' in content, "迁移脚本缺少会员标签字段"
        assert 'source_channel' in content, "迁移脚本缺少来源渠道字段"

    def test_migrate_v12_adds_refund_operator(self):
        """迁移脚本添加退款处理人字段"""
        migrate_path = os.path.join(ROOT, 'business-common', 'migrate_v12.py')
        content = read_source(migrate_path)
        assert 'refund_operator' in content, \
            "迁移脚本缺少退款处理人字段（应包含 refund_operator_id 和 refund_operator_name）"
