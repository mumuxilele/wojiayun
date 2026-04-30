"""
Model 实体层
定义系统的核心数据实体
"""
from .user import User
from .application import Application
from .order import Order
from .product import Product
from .cafeteria import CafeteriaDish, CafeteriaOrder
from .banquet import BanquetRoom, BanquetBooking
from .drink import DrinkItem, DrinkOrder
from .sports import SportsVenue, SportsBooking
from .carwash_laundry import CarwashOrder, LaundryOrder
from .member import Member, CouponTemplate, UserCoupon
from .community import CommunityService, CommunityActivity, CommunityPost

__all__ = [
    'User', 'Application', 'Order', 'Product',
    'CafeteriaDish', 'CafeteriaOrder',
    'BanquetRoom', 'BanquetBooking',
    'DrinkItem', 'DrinkOrder',
    'SportsVenue', 'SportsBooking',
    'CarwashOrder', 'LaundryOrder',
    'Member', 'CouponTemplate', 'UserCoupon',
    'CommunityService', 'CommunityActivity', 'CommunityPost',
]
