"""
Repository 仓储层
封装数据访问逻辑，提供统一的 CRUD 接口
"""
from .base_repository import BaseRepository
from .application_repository import ApplicationRepository
from .order_repository import OrderRepository
from .product_repository import ProductRepository
from .user_repository import UserRepository

__all__ = [
    'BaseRepository',
    'ApplicationRepository', 
    'OrderRepository',
    'ProductRepository',
    'UserRepository'
]
