"""
Carwash/Laundry 洗车洗衣实体
"""
from .base_model import BaseModel


class CarwashOrder(BaseModel):
    TABLE_NAME = 'ts_carwash_order'
    PRIMARY_KEY = 'id'

    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_WASHING = 'washing'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.order_no = kwargs.get('order_no', '')
        self.user_id = kwargs.get('user_id', '')
        self.user_name = kwargs.get('user_name')
        self.user_phone = kwargs.get('user_phone')
        self.car_no = kwargs.get('car_no')
        self.service_id = kwargs.get('service_id')
        self.service_name = kwargs.get('service_name')
        self.station_id = kwargs.get('station_id')
        self.station_name = kwargs.get('station_name')
        self.booking_time = kwargs.get('booking_time')
        self.total_amount = float(kwargs.get('total_amount', 0))
        self.status = kwargs.get('status', self.STATUS_PENDING)
        self.pay_status = int(kwargs.get('pay_status', 0))
        self.qr_code = kwargs.get('qr_code')
        self.remark = kwargs.get('remark')
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.deleted = int(kwargs.get('deleted', 0))
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid, 'order_no': self.order_no,
            'user_id': self.user_id, 'user_name': self.user_name,
            'car_no': self.car_no, 'service_name': self.service_name,
            'station_name': self.station_name,
            'booking_time': str(self.booking_time) if self.booking_time else None,
            'total_amount': self.total_amount, 'status': self.status,
            'pay_status': self.pay_status,
            'created_at': str(self.created_at) if self.created_at else None,
        }


class LaundryOrder(BaseModel):
    TABLE_NAME = 'ts_laundry_order'
    PRIMARY_KEY = 'id'

    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_WASHING = 'washing'
    STATUS_DELIVERED = 'delivered'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.order_no = kwargs.get('order_no', '')
        self.user_id = kwargs.get('user_id', '')
        self.user_name = kwargs.get('user_name')
        self.user_phone = kwargs.get('user_phone')
        self.items = kwargs.get('items', [])
        self.total_count = int(kwargs.get('total_count', 0))
        self.total_amount = float(kwargs.get('total_amount', 0))
        self.actual_amount = float(kwargs.get('actual_amount', 0))
        self.status = kwargs.get('status', self.STATUS_PENDING)
        self.pay_status = int(kwargs.get('pay_status', 0))
        self.pickup_type = kwargs.get('pickup_type', 'self')
        self.pickup_address = kwargs.get('pickup_address')
        self.pickup_time = kwargs.get('pickup_time')
        self.delivery_time = kwargs.get('delivery_time')
        self.qr_code = kwargs.get('qr_code')
        self.remark = kwargs.get('remark')
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.deleted = int(kwargs.get('deleted', 0))
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid, 'order_no': self.order_no,
            'user_id': self.user_id, 'user_name': self.user_name,
            'items': self.items, 'total_count': self.total_count,
            'total_amount': self.total_amount, 'actual_amount': self.actual_amount,
            'status': self.status, 'pay_status': self.pay_status,
            'pickup_type': self.pickup_type,
            'pickup_address': self.pickup_address,
            'pickup_time': str(self.pickup_time) if self.pickup_time else None,
            'delivery_time': str(self.delivery_time) if self.delivery_time else None,
            'created_at': str(self.created_at) if self.created_at else None,
        }
