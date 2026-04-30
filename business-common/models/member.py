"""
Member/Points/Coupon 会员积分优惠券实体
"""
from .base_model import BaseModel


class Member(BaseModel):
    TABLE_NAME = 'ts_member'
    PRIMARY_KEY = 'id'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.user_id = kwargs.get('user_id', '')
        self.user_name = kwargs.get('user_name')
        self.user_phone = kwargs.get('user_phone')
        self.level_id = kwargs.get('level_id')
        self.level_name = kwargs.get('level_name')
        self.points = int(kwargs.get('points', 0))
        self.total_points = int(kwargs.get('total_points', 0))
        self.total_consumption = float(kwargs.get('total_consumption', 0))
        self.balance = float(kwargs.get('balance', 0))
        self.card_no = kwargs.get('card_no')
        self.status = int(kwargs.get('status', 1))
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.deleted = int(kwargs.get('deleted', 0))
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid,
            'user_id': self.user_id, 'user_name': self.user_name,
            'user_phone': self.user_phone,
            'level_id': self.level_id, 'level_name': self.level_name,
            'points': self.points, 'total_points': self.total_points,
            'total_consumption': self.total_consumption,
            'balance': self.balance, 'card_no': self.card_no,
            'status': self.status,
            'created_at': str(self.created_at) if self.created_at else None,
        }


class CouponTemplate(BaseModel):
    TABLE_NAME = 'ts_coupon_template'
    PRIMARY_KEY = 'id'

    TYPE_FIXED = 'fixed'       # 满减
    TYPE_DISCOUNT = 'discount'  # 折扣
    TYPE_CASH = 'cash'          # 代金券

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.name = kwargs.get('name', '')
        self.type = kwargs.get('type', self.TYPE_FIXED)
        self.value = float(kwargs.get('value', 0))
        self.min_amount = float(kwargs.get('min_amount', 0))
        self.total_count = int(kwargs.get('total_count', 0))
        self.issued_count = int(kwargs.get('issued_count', 0))
        self.used_count = int(kwargs.get('used_count', 0))
        self.applicable_scope = kwargs.get('applicable_scope', 'all')
        self.scope_ids = kwargs.get('scope_ids')
        self.start_time = kwargs.get('start_time')
        self.end_time = kwargs.get('end_time')
        self.status = int(kwargs.get('status', 1))
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.deleted = int(kwargs.get('deleted', 0))
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid, 'name': self.name,
            'type': self.type, 'value': self.value,
            'min_amount': self.min_amount,
            'total_count': self.total_count,
            'issued_count': self.issued_count,
            'used_count': self.used_count,
            'applicable_scope': self.applicable_scope,
            'scope_ids': self.scope_ids,
            'start_time': str(self.start_time) if self.start_time else None,
            'end_time': str(self.end_time) if self.end_time else None,
            'status': self.status,
            'created_at': str(self.created_at) if self.created_at else None,
        }


class UserCoupon(BaseModel):
    TABLE_NAME = 'ts_user_coupon'
    PRIMARY_KEY = 'id'

    STATUS_UNUSED = 0
    STATUS_USED = 1
    STATUS_EXPIRED = 2

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.template_id = kwargs.get('template_id', 0)
        self.coupon_name = kwargs.get('coupon_name')
        self.coupon_type = kwargs.get('coupon_type')
        self.coupon_value = float(kwargs.get('coupon_value', 0)) if kwargs.get('coupon_value') else 0
        self.min_amount = float(kwargs.get('min_amount', 0))
        self.user_id = kwargs.get('user_id', '')
        self.status = int(kwargs.get('status', 0))
        self.used_order_id = kwargs.get('used_order_id')
        self.used_time = kwargs.get('used_time')
        self.expire_time = kwargs.get('expire_time')
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.created_at = kwargs.get('created_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid,
            'template_id': self.template_id,
            'coupon_name': self.coupon_name,
            'coupon_type': self.coupon_type,
            'coupon_value': self.coupon_value,
            'min_amount': self.min_amount,
            'user_id': self.user_id, 'status': self.status,
            'used_time': str(self.used_time) if self.used_time else None,
            'expire_time': str(self.expire_time) if self.expire_time else None,
            'created_at': str(self.created_at) if self.created_at else None,
        }
