"""
Drink 饮品实体
对应表: ts_drink_item, ts_drink_order
"""
from .base_model import BaseModel


class DrinkItem(BaseModel):
    TABLE_NAME = 'ts_drink_item'
    PRIMARY_KEY = 'id'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.category_id = kwargs.get('category_id', 0)
        self.name = kwargs.get('name', '')
        self.image = kwargs.get('image')
        self.price = float(kwargs.get('price', 0))
        self.original_price = float(kwargs.get('original_price', 0)) if kwargs.get('original_price') else None
        self.description = kwargs.get('description')
        self.specs = kwargs.get('specs')
        self.stock = int(kwargs.get('stock', 0))
        self.sales = int(kwargs.get('sales', 0))
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
            'id': self.id, 'fid': self.fid,
            'category_id': self.category_id, 'name': self.name,
            'image': self.image, 'price': self.price,
            'original_price': self.original_price,
            'description': self.description, 'specs': self.specs,
            'stock': self.stock, 'sales': self.sales,
            'status': self.status, 'sort_order': self.sort_order,
            'created_at': str(self.created_at) if self.created_at else None,
        }


class DrinkOrder(BaseModel):
    TABLE_NAME = 'ts_drink_order'
    PRIMARY_KEY = 'id'

    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_MAKING = 'making'
    STATUS_DELIVERING = 'delivering'
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
        self.total_amount = float(kwargs.get('total_amount', 0))
        self.actual_amount = float(kwargs.get('actual_amount', 0))
        self.status = kwargs.get('status', self.STATUS_PENDING)
        self.pay_status = int(kwargs.get('pay_status', 0))
        self.delivery_type = kwargs.get('delivery_type', 'self')
        self.delivery_address = kwargs.get('delivery_address')
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
            'items': self.items, 'total_amount': self.total_amount,
            'actual_amount': self.actual_amount, 'status': self.status,
            'pay_status': self.pay_status,
            'delivery_type': self.delivery_type,
            'delivery_address': self.delivery_address,
            'remark': self.remark,
            'created_at': str(self.created_at) if self.created_at else None,
        }
