"""
订单状态流转校验模块 V13.0
防止非法状态转换，确保订单状态机符合预定义规则
"""
from enum import Enum
from typing import Optional, Dict, List, Tuple

class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = 'pending'       # 待支付
    PAID = 'paid'             # 已支付
    SHIPPED = 'shipped'       # 已发货
    COMPLETED = 'completed'   # 已完成
    CANCELLED = 'cancelled'   # 已取消
    REFUNDING = 'refunding'   # 退款中
    REFUNDED = 'refunded'      # 已退款

class OrderStatusTransition:
    """
    订单状态流转校验器
    
    合法流转规则：
    - pending → paid（支付后）
    - pending → cancelled（用户取消）
    - paid → shipped（发货后）
    - paid → refunding（申请退款）
    - shipped → completed（确认收货）
    - shipped → refunding（申请退款）
    - refunding → refunded（退款通过）
    - refunding → paid（退款拒绝，恢复支付状态）
    
    终态（不可流转）：cancelled, refunded, completed
    """
    
    # 状态流转规则：from_status -> [allowed_to_statuses]
    TRANSITIONS: Dict[str, List[str]] = {
        'pending': ['paid', 'cancelled'],
        'paid': ['shipped', 'refunding'],
        'shipped': ['completed', 'refunding'],
        'refunding': ['refunded', 'paid'],
        # 终态：不允许任何流转
        'cancelled': [],
        'refunded': [],
        'completed': [],
    }
    
    # 终态订单（不能修改状态）
    TERMINAL_STATUSES = {'cancelled', 'refunded', 'completed'}
    
    # 各状态可执行的操作
    STATUS_ACTIONS: Dict[str, List[str]] = {
        'pending': ['cancel'],           # 可取消
        'paid': ['ship', 'refund'],      # 可发货、可申请退款
        'shipped': ['complete', 'refund'],  # 可确认收货、可申请退款
        'refunding': ['approve_refund', 'reject_refund'],  # 可审核退款
    }
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> Tuple[bool, Optional[str]]:
        """
        检查状态流转是否合法
        
        Args:
            from_status: 当前状态
            to_status: 目标状态
            
        Returns:
            (是否允许, 错误信息)
        """
        # 状态存在性校验
        valid_statuses = {s.value for s in OrderStatus}
        
        if from_status not in valid_statuses:
            return False, f"无效的当前状态: {from_status}"
        
        if to_status not in valid_statuses:
            return False, f"无效的目标状态: {to_status}"
        
        # 终态检查
        if from_status in cls.TERMINAL_STATUSES:
            return False, f"订单已处于终态({cls._get_status_text(from_status)})，不能修改状态"
        
        # 流转规则检查
        allowed = cls.TRANSITIONS.get(from_status, [])
        if to_status not in allowed:
            return False, f"不允许从 {cls._get_status_text(from_status)} 直接流转到 {cls._get_status_text(to_status)}"
        
        return True, None
    
    @classmethod
    def validate_transition(cls, from_status: str, to_status: str) -> bool:
        """
        简化的校验方法，返回是否允许流转
        """
        allowed, _ = cls.can_transition(from_status, to_status)
        return allowed
    
    @classmethod
    def get_allowed_transitions(cls, current_status: str) -> List[str]:
        """
        获取当前状态允许的所有目标状态
        """
        return cls.TRANSITIONS.get(current_status, [])
    
    @classmethod
    def get_available_actions(cls, current_status: str) -> List[str]:
        """
        获取当前状态可执行的操作列表
        """
        return cls.STATUS_ACTIONS.get(current_status, [])
    
    @classmethod
    def action_to_status(cls, action: str) -> Optional[str]:
        """
        将操作映射到目标状态
        """
        action_map = {
            'cancel': 'cancelled',
            'ship': 'shipped',
            'refund': 'refunding',
            'complete': 'completed',
            'approve_refund': 'refunded',
            'reject_refund': 'paid',
            'pay': 'paid',
        }
        return action_map.get(action)
    
    @classmethod
    def can_execute_action(cls, current_status: str, action: str) -> Tuple[bool, Optional[str]]:
        """
        检查当前状态下是否可以执行某操作
        
        Args:
            current_status: 当前订单状态
            action: 操作类型 (cancel/ship/refund/complete/approve_refund/reject_refund)
            
        Returns:
            (是否允许, 错误信息)
        """
        available = cls.get_available_actions(current_status)
        if action not in available:
            return False, f"当前状态({cls._get_status_text(current_status)})不支持此操作"
        
        # 检查流转
        target_status = cls.action_to_status(action)
        if target_status:
            return cls.can_transition(current_status, target_status)
        
        return True, None
    
    @staticmethod
    def _get_status_text(status: str) -> str:
        """获取状态的中文描述"""
        status_texts = {
            'pending': '待支付',
            'paid': '已支付',
            'shipped': '已发货',
            'completed': '已完成',
            'cancelled': '已取消',
            'refunding': '退款中',
            'refunded': '已退款',
        }
        return status_texts.get(status, status)


class OrderStatusValidator:
    """
    订单状态校验器（便捷封装）
    用于在实际业务逻辑中进行状态校验
    """
    
    def __init__(self, current_status: str):
        self.current_status = current_status
    
    def can_change_to(self, target_status: str) -> bool:
        """检查是否可以变更为目标状态"""
        return OrderStatusTransition.validate_transition(self.current_status, target_status)
    
    def can_execute(self, action: str) -> bool:
        """检查是否可以执行某操作"""
        allowed, _ = OrderStatusTransition.can_execute_action(self.current_status, action)
        return allowed
    
    def get_error_message(self, action: str) -> str:
        """获取操作失败时的错误信息"""
        _, error = OrderStatusTransition.can_execute_action(self.current_status, action)
        return error or '未知错误'


# 便捷实例
order_status_validator = OrderStatusTransition
