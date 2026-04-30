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
from .cafeteria_repository import CafeteriaCategoryRepository, CafeteriaDishRepository, CafeteriaOrderRepository
from .banquet_repository import BanquetRoomRepository, BanquetBookingRepository
from .drink_repository import DrinkCategoryRepository, DrinkItemRepository, DrinkOrderRepository
from .sports_repository import SportsVenueRepository, SportsBookingRepository
from .carwash_laundry_repository import (CarwashServiceRepository, CarwashStationRepository,
                                          CarwashOrderRepository, LaundryServiceRepository,
                                          LaundryPriceRepository, LaundryOrderRepository)
from .member_repository_v2 import (MemberLevelRepository, MemberRepository as MemberRepositoryV2,
                                    PointsLogRepository, CouponTemplateRepository,
                                    UserCouponRepository, ConsumptionLedgerRepository)
from .community_repository import (CommunityCategoryRepository, CommunityServiceRepository,
                                    CommunityActivityRepository, CommunityActivitySignupRepository,
                                    CommunityPostRepository)

__all__ = [
    'BaseRepository',
    'ApplicationRepository', 'OrderRepository', 'OrderItemRepository',
    'ProductRepository', 'UserRepository', 'StatsRepository',
    'ShopRepository', 'MemberRepository', 'BookingRepository',
    'CafeteriaCategoryRepository', 'CafeteriaDishRepository', 'CafeteriaOrderRepository',
    'BanquetRoomRepository', 'BanquetBookingRepository',
    'DrinkCategoryRepository', 'DrinkItemRepository', 'DrinkOrderRepository',
    'SportsVenueRepository', 'SportsBookingRepository',
    'CarwashServiceRepository', 'CarwashStationRepository', 'CarwashOrderRepository',
    'LaundryServiceRepository', 'LaundryPriceRepository', 'LaundryOrderRepository',
    'MemberLevelRepository', 'MemberRepositoryV2', 'PointsLogRepository',
    'CouponTemplateRepository', 'UserCouponRepository', 'ConsumptionLedgerRepository',
    'CommunityCategoryRepository', 'CommunityServiceRepository',
    'CommunityActivityRepository', 'CommunityActivitySignupRepository',
    'CommunityPostRepository',
]
