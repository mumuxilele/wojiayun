"""
Banquet 包间实体
对应表: ts_banquet_room, ts_banquet_booking
"""
from .base_model import BaseModel


class BanquetRoom(BaseModel):
    TABLE_NAME = 'ts_banquet_room'
    PRIMARY_KEY = 'id'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.name = kwargs.get('name', '')
        self.image = kwargs.get('image')
        self.images = kwargs.get('images')
        self.capacity = int(kwargs.get('capacity', 10))
        self.price = float(kwargs.get('price', 0))
        self.min_consumption = float(kwargs.get('min_consumption', 0))
        self.facilities = kwargs.get('facilities')
        self.description = kwargs.get('description')
        self.status = int(kwargs.get('status', 1))
        self.sort_order = int(kwargs.get('sort_order', 0))
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.deleted = int(kwargs.get('deleted', 0))
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid, 'name': self.name,
            'image': self.image, 'images': self.images,
            'capacity': self.capacity, 'price': self.price,
            'min_consumption': self.min_consumption,
            'facilities': self.facilities, 'description': self.description,
            'status': self.status, 'sort_order': self.sort_order,
            'created_at': str(self.created_at) if self.created_at else None,
        }


class BanquetBooking(BaseModel):
    TABLE_NAME = 'ts_banquet_booking'
    PRIMARY_KEY = 'id'

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REJECTED = 'rejected'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.booking_no = kwargs.get('booking_no', '')
        self.room_id = kwargs.get('room_id', 0)
        self.room_name = kwargs.get('room_name')
        self.user_id = kwargs.get('user_id', '')
        self.user_name = kwargs.get('user_name')
        self.user_phone = kwargs.get('user_phone')
        self.booking_date = kwargs.get('booking_date')
        self.start_time = kwargs.get('start_time', '')
        self.end_time = kwargs.get('end_time', '')
        self.guest_count = int(kwargs.get('guest_count', 0))
        self.custom_request = kwargs.get('custom_request')
        self.total_amount = float(kwargs.get('total_amount', 0))
        self.status = kwargs.get('status', self.STATUS_PENDING)
        self.remark = kwargs.get('remark')
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.deleted = int(kwargs.get('deleted', 0))
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid, 'booking_no': self.booking_no,
            'room_id': self.room_id, 'room_name': self.room_name,
            'user_id': self.user_id, 'user_name': self.user_name,
            'user_phone': self.user_phone,
            'booking_date': str(self.booking_date) if self.booking_date else None,
            'start_time': self.start_time, 'end_time': self.end_time,
            'guest_count': self.guest_count,
            'custom_request': self.custom_request,
            'total_amount': self.total_amount, 'status': self.status,
            'remark': self.remark,
            'created_at': str(self.created_at) if self.created_at else None,
        }
