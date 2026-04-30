"""
Sports 场馆实体
对应表: ts_sports_venue, ts_sports_booking
"""
from .base_model import BaseModel


class SportsVenue(BaseModel):
    TABLE_NAME = 'ts_sports_venue'
    PRIMARY_KEY = 'id'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.name = kwargs.get('name', '')
        self.type = kwargs.get('type', '')
        self.image = kwargs.get('image')
        self.images = kwargs.get('images')
        self.capacity = int(kwargs.get('capacity', 1))
        self.price_per_hour = float(kwargs.get('price_per_hour', 0))
        self.description = kwargs.get('description')
        self.facilities = kwargs.get('facilities')
        self.open_time = kwargs.get('open_time', '08:00')
        self.close_time = kwargs.get('close_time', '22:00')
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
            'type': self.type, 'image': self.image, 'images': self.images,
            'capacity': self.capacity, 'price_per_hour': self.price_per_hour,
            'description': self.description, 'facilities': self.facilities,
            'open_time': self.open_time, 'close_time': self.close_time,
            'status': self.status, 'sort_order': self.sort_order,
            'created_at': str(self.created_at) if self.created_at else None,
        }


class SportsBooking(BaseModel):
    TABLE_NAME = 'ts_sports_booking'
    PRIMARY_KEY = 'id'

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_USING = 'using'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.booking_no = kwargs.get('booking_no', '')
        self.venue_id = kwargs.get('venue_id', 0)
        self.venue_name = kwargs.get('venue_name')
        self.user_id = kwargs.get('user_id', '')
        self.user_name = kwargs.get('user_name')
        self.user_phone = kwargs.get('user_phone')
        self.booking_date = kwargs.get('booking_date')
        self.start_time = kwargs.get('start_time', '')
        self.end_time = kwargs.get('end_time', '')
        self.duration_hours = float(kwargs.get('duration_hours', 1))
        self.total_amount = float(kwargs.get('total_amount', 0))
        self.status = kwargs.get('status', self.STATUS_PENDING)
        self.pay_status = int(kwargs.get('pay_status', 0))
        self.qr_code = kwargs.get('qr_code')
        self.check_in_time = kwargs.get('check_in_time')
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
            'venue_id': self.venue_id, 'venue_name': self.venue_name,
            'user_id': self.user_id, 'user_name': self.user_name,
            'booking_date': str(self.booking_date) if self.booking_date else None,
            'start_time': self.start_time, 'end_time': self.end_time,
            'duration_hours': self.duration_hours,
            'total_amount': self.total_amount, 'status': self.status,
            'pay_status': self.pay_status, 'qr_code': self.qr_code,
            'check_in_time': str(self.check_in_time) if self.check_in_time else None,
            'remark': self.remark,
            'created_at': str(self.created_at) if self.created_at else None,
        }
