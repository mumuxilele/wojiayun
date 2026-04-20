"""
Order 实体
对应表: business_orders
"""
from typing import Optional, List, Dict, Any
import json
from .base_model import BaseModel


class Order(BaseModel):
    """订单实体"""
    
    TABLE_NAME = 'business_orders'
    PRIMARY_KEY = 'id'
    
    # 状态常量
    STATUS_PENDING_PAYMENT = 'pending_payment'  # 待付款
    STATUS_PAID = 'paid'                        # 已付款
    STATUS_SHIPPED = 'shipped'                  # 已发货
    STATUS_COMPLETED = 'completed'              # 已完成
    STATUS_CANCELLED = 'cancelled'              # 已取消
    STATUS_REFUNDING = 'refunding'              # 退款中
    STATUS_REFUNDED = 'refunded'                # 已退款
    
    def __init__(self, **kwargs):
        # 主键
        self.id: int = kwargs.get('id', 0)
        self.fid: Optional[str] = kwargs.get('fid')
        
        # 订单编号
        self.order_no: str = kwargs.get('order_no', '')
        
        # 用户信息
        self.user_id: str = kwargs.get('user_id', '')
        self.user_name: str = kwargs.get('user_name', '')
        self.user_phone: str = kwargs.get('user_phone', '')
        
        # 企业信息
        self.ec_id: Optional[str] = kwargs.get('ec_id')
        self.project_id: Optional[str] = kwargs.get('project_id')
        
        # 订单金额
        self.total_amount: float = float(kwargs.get('total_amount', 0))
        self.actual_amount: float = float(kwargs.get('actual_amount', 0))
        self.discount_amount: float = float(kwargs.get('discount_amount', 0))
        
        # 状态
        self.status: str = kwargs.get('status', self.STATUS_PENDING_PAYMENT)
        self.pay_status: int = kwargs.get('pay_status', 0)  # 0-未支付, 1-已支付
        
        # 收货信息
        self.receiver_name: Optional[str] = kwargs.get('receiver_name')
        self.receiver_phone: Optional[str] = kwargs.get('receiver_phone')
        self.receiver_address: Optional[str] = kwargs.get('receiver_address')
        
        # 订单商品
        self.items: Optional[List] = kwargs.get('items')
        if isinstance(self.items, str):
            try:
                self.items = json.loads(self.items)
            except:
                self.items = []
        
        # 备注
        self.remark: Optional[str] = kwargs.get('remark')
        self.user_remark: Optional[str] = kwargs.get('user_remark')
        
        # 时间
        self.pay_time = kwargs.get('pay_time')
        self.ship_time = kwargs.get('ship_time')
        self.complete_time = kwargs.get('complete_time')
        
        # 软删除
        self.deleted: int = kwargs.get('deleted', 0)
        
        # 时间戳
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        
        super().__init__(**kwargs)
    
    @property
    def status_text(self) -> str:
        """状态中文描述"""
        status_map = {
            self.STATUS_PENDING_PAYMENT: '待付款',
            self.STATUS_PAID: '已付款',
            self.STATUS_SHIPPED: '已发货',
            self.STATUS_COMPLETED: '已完成',
            self.STATUS_CANCELLED: '已取消',
            self.STATUS_REFUNDING: '退款中',
            self.STATUS_REFUNDED: '已退款'
        }
        return status_map.get(self.status, '未知')
    
    @property
    def is_paid(self) -> bool:
        """是否已支付"""
        return self.pay_status == 1
    
    @property
    def can_cancel(self) -> bool:
        """是否可以取消"""
        return self.status in [self.STATUS_PENDING_PAYMENT] and self.deleted == 0
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'fid': self.fid,
            'order_no': self.order_no,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_phone': self.user_phone,
            'ec_id': self.ec_id,
            'project_id': self.project_id,
            'total_amount': self.total_amount,
            'actual_amount': self.actual_amount,
            'discount_amount': self.discount_amount,
            'status': self.status,
            'status_text': self.status_text,
            'pay_status': self.pay_status,
            'is_paid': self.is_paid,
            'receiver_name': self.receiver_name,
            'receiver_phone': self.receiver_phone,
            'receiver_address': self.receiver_address,
            'items': self.items,
            'remark': self.remark,
            'can_cancel': self.can_cancel,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None
        }
