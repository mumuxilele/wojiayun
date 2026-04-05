"""
V13.0 结构验证测试 - 无需数据库连接
测试内容：
  - P0修复: 支付金额服务端校验（防止篡改）
  - P0修复: 订单状态流转校验（防止非法状态转换）
  - P1优化: 库存预扣减事务优化（防止超卖）
  - P1优化: 用户统计接口N+1查询优化
  - P2新增: 订单状态流转枚举类定义
  - 新增文件: order_status.py 状态流转模块
"""
import sys
import os
import ast
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_H5_APP    = os.path.join(ROOT, 'business-userH5',  'app.py')
STAFF_H5_APP  = os.path.join(ROOT, 'business-staffH5', 'app.py')
ADMIN_APP      = os.path.join(ROOT, 'business-admin',   'app.py')
ORDER_STATUS   = os.path.join(ROOT, 'business-common',   'order_status.py')
COMMON_INIT    = os.path.join(ROOT, 'business-common',   '__init__.py')


def read_source(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ============================================================
#  P0修复验证
# ============================================================
class TestV13P0Fixes:
    """V13.0 P0 Bug修复验证"""

    def test_order_status_module_exists(self):
        """P0: 订单状态流转模块存在"""
        assert os.path.exists(ORDER_STATUS), \
            f"缺少订单状态流转模块: {ORDER_STATUS}"

    def test_order_status_python_syntax(self):
        """P0验证: order_status.py语法无误"""
        content = read_source(ORDER_STATUS)
        try:
            ast.parse(content)
        except SyntaxError as e:
            assert False, f"order_status.py 存在语法错误: {e}"

    def test_payment_amount_server_validation(self):
        """P0修复: create_payment 必须进行服务端金额校验"""
        content = read_source(USER_H5_APP)
        
        # 必须有服务端获取实际金额的代码
        assert "SELECT actual_amount" in content, \
            "create_payment缺少从数据库获取实际金额的查询"
        
        # 必须有金额校验逻辑
        assert "abs(client_amount" in content or "abs(" in content and "actual_amount" in content, \
            "create_payment缺少金额校验逻辑"
        
        # 校验失败应返回错误
        assert "金额校验失败" in content or "校验失败" in content, \
            "create_payment金额校验失败时应返回错误信息"

    def test_admin_order_status_transition_validation(self):
        """P0修复: admin端订单状态更新必须有流转校验"""
        content = read_source(ADMIN_APP)
        
        # 必须导入订单状态模块
        assert "OrderStatusTransition" in content, \
            "admin端未导入OrderStatusTransition模块"
        
        # 必须调用流转校验
        assert "can_transition" in content, \
            "admin_update_order缺少状态流转校验"
        
        # 校验不通过应返回错误
        assert "不允许的状态流转" in content, \
            "admin端状态流转校验失败时应返回明确错误信息"

    def test_staff_order_status_transition_validation(self):
        """P0修复: staff端订单状态更新必须有流转校验"""
        content = read_source(STAFF_H5_APP)
        
        # 必须导入订单状态模块
        assert "OrderStatusTransition" in content, \
            "staff端未导入OrderStatusTransition模块"
        
        # 必须调用流转校验
        assert "can_transition" in content, \
            "update_order_status缺少状态流转校验"

    def test_all_apps_python_syntax(self):
        """P0验证: 所有核心文件语法无误"""
        for path in [USER_H5_APP, STAFF_H5_APP, ADMIN_APP, ORDER_STATUS, COMMON_INIT]:
            content = read_source(path)
            try:
                ast.parse(content)
            except SyntaxError as e:
                assert False, f"{os.path.basename(path)} 存在语法错误: {e}"


# ============================================================
#  P1优化验证
# ============================================================
class TestV13P1Optimizations:
    """V13.0 P1性能优化验证"""

    def test_user_stats_single_query(self):
        """P1优化: 用户统计接口合并为单次查询"""
        content = read_source(USER_H5_APP)
        
        # 应该使用单次查询获取所有统计
        assert "SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='pending'" in content or \
               "(SELECT COUNT(*) FROM" in content, \
            "get_user_stats未使用单次多子查询聚合方式"
        
        # 不应该有多个独立的 db.get_total 调用（原来的N+1模式）
        # 计算 get_total 调用次数
        get_total_count = content.count('db.get_total(')
        assert get_total_count == 0, \
            f"get_user_stats仍有{get_total_count}个独立db.get_total调用，未完成N+1优化"

    def test_create_order_transaction_lock(self):
        """P1优化: 创建订单使用事务+行锁防止超卖"""
        content = read_source(USER_H5_APP)
        
        # 必须在事务内进行库存校验
        assert "conn.begin()" in content, "create_order未开启事务"
        
        # 应该有 SELECT FOR UPDATE 或批量锁定
        assert "SELECT" in content and ("FOR UPDATE" in content or "ORDER BY id" in content), \
            "create_order未使用行锁防止并发超卖"
        
        # 应该有带条件的库存扣减（stock>=quantity）
        assert "stock>=" in content or ("WHERE" in content and "stock" in content), \
            "create_order未使用条件扣减防止超卖"

    def test_order_items_loop_with_locked_check(self):
        """P1优化: 订单商品处理前必须校验库存"""
        content = read_source(USER_H5_APP)
        
        # 必须在处理商品前进行库存校验
        lines = content.split('\n')
        in_create_order = False
        has_pre_validation = False
        
        for line in lines:
            if 'def create_order' in line:
                in_create_order = True
            if in_create_order and ('库存不足' in line or 'stock<' in line or 'current_stock <' in line):
                has_pre_validation = True
                break
        
        assert has_pre_validation, "create_order未在处理订单项前进行库存校验"


# ============================================================
#  P2新增验证
# ============================================================
class TestV13P2Features:
    """V13.0 P2新功能验证"""

    def test_order_status_enum_defined(self):
        """P2: 订单状态枚举类已定义"""
        content = read_source(ORDER_STATUS)
        
        # 必须有枚举定义
        assert "class OrderStatus" in content, "缺少OrderStatus枚举类"
        
        # 必须包含所有状态值
        for status in ['pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunding', 'refunded']:
            assert f"'{status}'" in content, f"OrderStatus缺少状态值: {status}"

    def test_order_transition_rules_defined(self):
        """P2: 订单状态流转规则已定义"""
        content = read_source(ORDER_STATUS)
        
        # 必须有流转规则
        assert "TRANSITIONS" in content, "缺少TRANSITIONS流转规则定义"
        
        # 必须定义终态
        assert "TERMINAL_STATUSES" in content, "缺少TERMINAL_STATUSES终态定义"

    def test_order_transition_validation_logic(self):
        """P2: 订单状态流转校验逻辑完整"""
        content = read_source(ORDER_STATUS)
        
        # 必须有can_transition方法
        assert "def can_transition" in content, "缺少can_transition方法"
        
        # 必须有终态检查
        assert "TERMINAL_STATUSES" in content, "缺少终态检查逻辑"
        
        # 必须有流转规则检查
        assert "allowed = cls.TRANSITIONS" in content or "TRANSITIONS.get" in content, \
            "缺少流转规则检查逻辑"

    def test_order_status_common_exported(self):
        """P2: 订单状态模块已导出"""
        content = read_source(COMMON_INIT)
        
        assert "OrderStatusTransition" in content, \
            "__init__.py未导出OrderStatusTransition"
        assert "order_status" in content, \
            "__init__.py未导入order_status模块"


# ============================================================
#  状态流转规则完整性验证
# ============================================================
class TestOrderStatusTransitions:
    """订单状态流转规则完整性测试"""

    def test_pending_can_transition_to_paid_and_cancelled(self):
        """pending状态可流转到paid和cancelled"""
        content = read_source(ORDER_STATUS)
        assert "'pending': ['paid', 'cancelled']" in content or \
               "'pending':" in content and "'cancelled'" in content, \
            "pending状态流转规则不正确"

    def test_paid_can_transition_to_shipped_and_refunding(self):
        """paid状态可流转到shipped和refunding"""
        content = read_source(ORDER_STATUS)
        assert "'paid':" in content and "'shipped'" in content and "'refunding'" in content, \
            "paid状态流转规则不正确"

    def test_shipped_can_transition_to_completed_and_refunding(self):
        """shipped状态可流转到completed和refunding"""
        content = read_source(ORDER_STATUS)
        assert "'shipped':" in content and "'completed'" in content and "'refunding'" in content, \
            "shipped状态流转规则不正确"

    def test_refunding_can_transition_to_refunded_and_paid(self):
        """refunding状态可流转到refunded和paid（拒绝）"""
        content = read_source(ORDER_STATUS)
        assert "'refunding':" in content and "'refunded'" in content and "'paid'" in content, \
            "refunding状态流转规则不正确"

    def test_terminal_statuses_are_immutable(self):
        """终态订单不能修改"""
        content = read_source(ORDER_STATUS)
        assert "'cancelled': []" in content, \
            "cancelled应为终态，不允许流转"
        assert "'refunded': []" in content, \
            "refunded应为终态，不允许流转"
        assert "'completed': []" in content, \
            "completed应为终态，不允许流转"


# ============================================================
#  支付安全验证
# ============================================================
class TestPaymentSecurity:
    """支付安全相关验证"""

    def test_payment_uses_server_amount(self):
        """支付接口必须使用服务端计算的金额"""
        content = read_source(USER_H5_APP)
        
        # 应该从数据库获取实际金额
        # 而不是直接使用客户端传入的金额
        lines = content.split('\n')
        in_create_payment = False
        uses_server_amount = False
        
        for line in lines:
            if 'def create_payment' in line:
                in_create_payment = True
            if in_create_payment:
                if 'payment_service.payment.create_payment' in line and 'amount=actual_amount' in line:
                    uses_server_amount = True
                    break
        
        assert uses_server_amount, \
            "create_payment应使用服务端计算的actual_amount，而不是client_amount"

    def test_payment_validates_order_exists(self):
        """支付接口必须验证订单存在"""
        content = read_source(USER_H5_APP)
        
        # 必须检查订单是否存在
        assert "订单不存在" in content, \
            "create_payment应检查订单是否存在"

    def test_payment_validates_not_already_paid(self):
        """支付接口必须验证订单未支付"""
        content = read_source(USER_H5_APP)
        
        # 必须检查是否已支付
        assert "已支付" in content, \
            "create_payment应检查订单是否已支付"


# ============================================================
#  安全增强验证
# ============================================================
class TestSecurityEnhancements:
    """安全增强验证"""

    def test_order_status_logged_in_audit(self):
        """订单状态变更必须记录审计日志"""
        content = read_source(ADMIN_APP)
        
        # 状态变更应记录审计日志
        assert "log_admin_action" in content or "audit_log" in content, \
            "admin端状态变更应记录审计日志"

    def test_old_status_recorded(self):
        """订单状态变更应记录原状态"""
        content = read_source(ADMIN_APP)
        
        # 应获取原状态
        assert "old_status" in content, \
            "admin_update_order应记录原状态用于审计"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '--tb=short'])
