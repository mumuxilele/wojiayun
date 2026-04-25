"""
Repository 仓储层
封装数据访问逻辑，提供统一的 CRUD 接口
"""
from .base_repository import BaseRepository
from .application_repository import ApplicationRepository
from .order_repository import OrderRepository
from .order_item_repository import OrderItemRepository
from .product_repository import ProductRepository
from .user_repository import UserRepository
from .stats_repository import StatsRepository
from .shop_repository import ShopRepository
from .member_repository import MemberRepository
from .booking_repository import BookingRepository

__all__ = [
    'BaseRepository',
    'ApplicationRepository',
    'OrderRepository',
    'OrderItemRepository',
    'ProductRepository',
    'UserRepository',
    'StatsRepository',
    'ShopRepository',
    'MemberRepository',
    'BookingRepository',
]
