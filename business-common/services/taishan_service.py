"""
Taishan Service
泰山城投社区商业 - 统一业务服务层
覆盖: 食堂、包间、饮品、场馆、洗车、洗衣、会员/积分/优惠券、社区服务
"""
import logging
import uuid
import json
from datetime import datetime, date
from typing import Dict, Any, Optional

from .base_service import BaseService
from ..repositories.cafeteria_repository import CafeteriaCategoryRepository, CafeteriaDishRepository, CafeteriaOrderRepository
from ..repositories.banquet_repository import BanquetRoomRepository, BanquetBookingRepository
from ..repositories.drink_repository import DrinkCategoryRepository, DrinkItemRepository, DrinkOrderRepository
from ..repositories.sports_repository import SportsVenueRepository, SportsBookingRepository
from ..repositories.carwash_laundry_repository import (CarwashServiceRepository, CarwashStationRepository,
                                                        CarwashOrderRepository, LaundryServiceRepository,
                                                        LaundryPriceRepository, LaundryOrderRepository)
from ..repositories.member_repository_v2 import (MemberLevelRepository, MemberRepository as MemberRepoV2,
                                                    PointsLogRepository, CouponTemplateRepository,
                                                    UserCouponRepository, ConsumptionLedgerRepository)
from ..repositories.community_repository import (CommunityCategoryRepository, CommunityServiceRepository,
                                                    CommunityActivityRepository, CommunityActivitySignupRepository,
                                                    CommunityPostRepository)

logger = logging.getLogger(__name__)


def _gen_fid():
    return str(uuid.uuid4())


def _gen_order_no(prefix='TS'):
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


class TaishanService(BaseService):
    """泰山城投统一业务服务"""

    SERVICE_NAME = 'TaishanService'

    def __init__(self):
        super().__init__()
        # 食堂
        self.cafeteria_cat_repo = CafeteriaCategoryRepository()
        self.cafeteria_dish_repo = CafeteriaDishRepository()
        self.cafeteria_order_repo = CafeteriaOrderRepository()
        # 包间
        self.banquet_room_repo = BanquetRoomRepository()
        self.banquet_booking_repo = BanquetBookingRepository()
        # 饮品
        self.drink_cat_repo = DrinkCategoryRepository()
        self.drink_item_repo = DrinkItemRepository()
        self.drink_order_repo = DrinkOrderRepository()
        # 场馆
        self.sports_venue_repo = SportsVenueRepository()
        self.sports_booking_repo = SportsBookingRepository()
        # 洗车洗衣
        self.carwash_svc_repo = CarwashServiceRepository()
        self.carwash_station_repo = CarwashStationRepository()
        self.carwash_order_repo = CarwashOrderRepository()
        self.laundry_svc_repo = LaundryServiceRepository()
        self.laundry_price_repo = LaundryPriceRepository()
        self.laundry_order_repo = LaundryOrderRepository()
        # 会员
        self.member_level_repo = MemberLevelRepository()
        self.member_repo = MemberRepoV2()
        self.points_log_repo = PointsLogRepository()
        self.coupon_tpl_repo = CouponTemplateRepository()
        self.user_coupon_repo = UserCouponRepository()
        self.ledger_repo = ConsumptionLedgerRepository()
        # 社区
        self.community_cat_repo = CommunityCategoryRepository()
        self.community_svc_repo = CommunityServiceRepository()
        self.community_act_repo = CommunityActivityRepository()
        self.community_signup_repo = CommunityActivitySignupRepository()
        self.community_post_repo = CommunityPostRepository()

    # ==================== 食堂 ====================

    def list_cafeteria_categories(self, ec_id=None):
        try:
            items = self.cafeteria_cat_repo.find_by_fields({'status': 1, 'deleted': 0, **({'ec_id': ec_id} if ec_id else {})}, limit=100)
            return self.success(items)
        except Exception as e:
            return self.error(str(e))

    def list_cafeteria_dishes(self, category_id=None, ec_id=None, project_id=None):
        try:
            if category_id:
                items = self.cafeteria_dish_repo.find_by_category(int(category_id))
            else:
                items = self.cafeteria_dish_repo.find_on_sale(ec_id, project_id)
            return self.success(items)
        except Exception as e:
            return self.error(str(e))

    def get_cafeteria_dish(self, dish_id):
        try:
            dish = self.cafeteria_dish_repo.find_by_id(dish_id)
            if not dish:
                return self.error('菜品不存在')
            return self.success(dish)
        except Exception as e:
            return self.error(str(e))

    def create_cafeteria_order(self, user_id, user_name, user_phone, data):
        try:
            items = data.get('items', [])
            if not items:
                return self.error('请选择菜品')
            total = sum(float(i.get('price', 0)) * int(i.get('quantity', 1)) for i in items)
            order_data = {
                'fid': _gen_fid(),
                'order_no': _gen_order_no('CF'),
                'user_id': user_id, 'user_name': user_name, 'user_phone': user_phone,
                'order_type': data.get('order_type', 'dine_in'),
                'table_no': data.get('table_no'),
                'items': json.dumps(items, ensure_ascii=False),
                'total_amount': total, 'actual_amount': total,
                'status': 'pending', 'pay_status': 0,
                'remark': data.get('remark'),
                'delivery_address': data.get('delivery_address'),
                'ec_id': data.get('ec_id'), 'project_id': data.get('project_id'),
            }
            oid = self.cafeteria_order_repo.insert(order_data)
            order_data['id'] = oid
            return self.success(order_data, '下单成功')
        except Exception as e:
            return self.error(str(e))

    def list_cafeteria_orders(self, user_id, status=None, page=1, page_size=20):
        try:
            return self.success(self.cafeteria_order_repo.find_by_user(user_id, status, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def get_cafeteria_order(self, order_id):
        try:
            order = self.cafeteria_order_repo.find_by_id(order_id)
            if not order:
                return self.error('订单不存在')
            return self.success(order)
        except Exception as e:
            return self.error(str(e))

    def update_cafeteria_order_status(self, order_id, status):
        try:
            return self.success({'affected': self.cafeteria_order_repo.update(order_id, {'status': status})})
        except Exception as e:
            return self.error(str(e))

    # ==================== 包间 ====================

    def list_banquet_rooms(self, ec_id=None):
        try:
            return self.success(self.banquet_room_repo.find_available(ec_id))
        except Exception as e:
            return self.error(str(e))

    def get_banquet_room(self, room_id):
        try:
            room = self.banquet_room_repo.find_by_id(room_id)
            if not room:
                return self.error('包间不存在')
            return self.success(room)
        except Exception as e:
            return self.error(str(e))

    def create_banquet_booking(self, user_id, user_name, user_phone, data):
        try:
            room = self.banquet_room_repo.find_by_id(data.get('room_id'))
            if not room:
                return self.error('包间不存在')
            if self.banquet_booking_repo.check_conflict(data['room_id'], data['booking_date'], data['start_time'], data['end_time']):
                return self.error('该时段已被预约')
            booking_data = {
                'fid': _gen_fid(),
                'booking_no': _gen_order_no('BK'),
                'room_id': data['room_id'], 'room_name': room.get('name'),
                'user_id': user_id, 'user_name': user_name, 'user_phone': user_phone,
                'booking_date': data['booking_date'],
                'start_time': data['start_time'], 'end_time': data['end_time'],
                'guest_count': data.get('guest_count', 0),
                'custom_request': data.get('custom_request'),
                'total_amount': float(room.get('price', 0)),
                'status': 'pending',
                'ec_id': data.get('ec_id'), 'project_id': data.get('project_id'),
            }
            bid = self.banquet_booking_repo.insert(booking_data)
            booking_data['id'] = bid
            return self.success(booking_data, '预约成功')
        except Exception as e:
            return self.error(str(e))

    def list_banquet_bookings(self, user_id, status=None, page=1, page_size=20):
        try:
            return self.success(self.banquet_booking_repo.find_by_user(user_id, status, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def update_banquet_booking_status(self, booking_id, status, remark=None):
        try:
            data = {'status': status}
            if remark:
                data['remark'] = remark
            return self.success({'affected': self.banquet_booking_repo.update(booking_id, data)})
        except Exception as e:
            return self.error(str(e))

    # ==================== 饮品 ====================

    def list_drink_categories(self, ec_id=None):
        try:
            return self.success(self.drink_cat_repo.find_by_fields({'status': 1, 'deleted': 0}, limit=100))
        except Exception as e:
            return self.error(str(e))

    def list_drink_items(self, category_id=None):
        try:
            if category_id:
                return self.success(self.drink_item_repo.find_by_category(int(category_id)))
            return self.success(self.drink_item_repo.find_by_fields({'status': 1, 'deleted': 0}, limit=200))
        except Exception as e:
            return self.error(str(e))

    def create_drink_order(self, user_id, user_name, user_phone, data):
        try:
            items = data.get('items', [])
            if not items:
                return self.error('请选择饮品')
            total = sum(float(i.get('price', 0)) * int(i.get('quantity', 1)) for i in items)
            order_data = {
                'fid': _gen_fid(), 'order_no': _gen_order_no('DK'),
                'user_id': user_id, 'user_name': user_name, 'user_phone': user_phone,
                'items': json.dumps(items, ensure_ascii=False),
                'total_amount': total, 'actual_amount': total,
                'status': 'pending', 'pay_status': 0,
                'delivery_type': data.get('delivery_type', 'self'),
                'delivery_address': data.get('delivery_address'),
                'remark': data.get('remark'),
                'ec_id': data.get('ec_id'), 'project_id': data.get('project_id'),
            }
            oid = self.drink_order_repo.insert(order_data)
            order_data['id'] = oid
            return self.success(order_data, '下单成功')
        except Exception as e:
            return self.error(str(e))

    def list_drink_orders(self, user_id, status=None, page=1, page_size=20):
        try:
            return self.success(self.drink_order_repo.find_by_user(user_id, status, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def update_drink_order_status(self, order_id, status):
        try:
            return self.success({'affected': self.drink_order_repo.update(order_id, {'status': status})})
        except Exception as e:
            return self.error(str(e))

    # ==================== 运动场馆 ====================

    def list_sports_venues(self, venue_type=None, ec_id=None):
        try:
            return self.success(self.sports_venue_repo.find_available(venue_type, ec_id))
        except Exception as e:
            return self.error(str(e))

    def get_sports_venue(self, venue_id):
        try:
            venue = self.sports_venue_repo.find_by_id(venue_id)
            if not venue:
                return self.error('场馆不存在')
            return self.success(venue)
        except Exception as e:
            return self.error(str(e))

    def create_sports_booking(self, user_id, user_name, user_phone, data):
        try:
            venue = self.sports_venue_repo.find_by_id(data.get('venue_id'))
            if not venue:
                return self.error('场馆不存在')
            if self.sports_booking_repo.check_conflict(data['venue_id'], data['booking_date'], data['start_time'], data['end_time']):
                return self.error('该时段已被预约')
            # 计算时长和金额
            sh, sm = map(int, data['start_time'].split(':'))
            eh, em = map(int, data['end_time'].split(':'))
            duration = (eh * 60 + em - sh * 60 - sm) / 60
            amount = round(float(venue.get('price_per_hour', 0)) * duration, 2)
            booking_data = {
                'fid': _gen_fid(), 'booking_no': _gen_order_no('SP'),
                'venue_id': data['venue_id'], 'venue_name': venue.get('name'),
                'user_id': user_id, 'user_name': user_name, 'user_phone': user_phone,
                'booking_date': data['booking_date'],
                'start_time': data['start_time'], 'end_time': data['end_time'],
                'duration_hours': duration, 'total_amount': amount,
                'status': 'pending', 'pay_status': 0,
                'remark': data.get('remark'),
                'ec_id': data.get('ec_id'), 'project_id': data.get('project_id'),
            }
            bid = self.sports_booking_repo.insert(booking_data)
            booking_data['id'] = bid
            return self.success(booking_data, '预约成功')
        except Exception as e:
            return self.error(str(e))

    def list_sports_bookings(self, user_id, status=None, page=1, page_size=20):
        try:
            return self.success(self.sports_booking_repo.find_by_user(user_id, status, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def update_sports_booking_status(self, booking_id, status):
        try:
            return self.success({'affected': self.sports_booking_repo.update(booking_id, {'status': status})})
        except Exception as e:
            return self.error(str(e))

    # ==================== 洗车 ====================

    def list_carwash_services(self):
        try:
            return self.success(self.carwash_svc_repo.find_by_fields({'status': 1, 'deleted': 0}, limit=50))
        except Exception as e:
            return self.error(str(e))

    def list_carwash_stations(self):
        try:
            return self.success(self.carwash_station_repo.find_by_fields({'deleted': 0}, limit=50))
        except Exception as e:
            return self.error(str(e))

    def create_carwash_order(self, user_id, user_name, user_phone, data):
        try:
            svc = self.carwash_svc_repo.find_by_id(data.get('service_id'))
            svc_name = svc.get('name', '') if svc else ''
            order_data = {
                'fid': _gen_fid(), 'order_no': _gen_order_no('CW'),
                'user_id': user_id, 'user_name': user_name, 'user_phone': user_phone,
                'car_no': data.get('car_no'),
                'service_id': data.get('service_id'), 'service_name': svc_name,
                'station_id': data.get('station_id'),
                'booking_time': data.get('booking_time'),
                'total_amount': float(svc.get('price', 0)) if svc else 0,
                'status': 'pending', 'pay_status': 0,
                'remark': data.get('remark'),
                'ec_id': data.get('ec_id'), 'project_id': data.get('project_id'),
            }
            oid = self.carwash_order_repo.insert(order_data)
            order_data['id'] = oid
            return self.success(order_data, '下单成功')
        except Exception as e:
            return self.error(str(e))

    def list_carwash_orders(self, user_id, status=None, page=1, page_size=20):
        try:
            return self.success(self.carwash_order_repo.find_by_user(user_id, status, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def update_carwash_order_status(self, order_id, status):
        try:
            return self.success({'affected': self.carwash_order_repo.update(order_id, {'status': status})})
        except Exception as e:
            return self.error(str(e))

    # ==================== 洗衣 ====================

    def list_laundry_services(self):
        try:
            return self.success(self.laundry_svc_repo.find_by_fields({'status': 1, 'deleted': 0}, limit=50))
        except Exception as e:
            return self.error(str(e))

    def list_laundry_prices(self, service_id=None):
        try:
            if service_id:
                return self.success(self.laundry_price_repo.find_by_service(int(service_id)))
            return self.success(self.laundry_price_repo.find_by_fields({'deleted': 0}, limit=200))
        except Exception as e:
            return self.error(str(e))

    def create_laundry_order(self, user_id, user_name, user_phone, data):
        try:
            items = data.get('items', [])
            if not items:
                return self.error('请选择衣物')
            total_count = sum(int(i.get('quantity', 1)) for i in items)
            total_amount = sum(float(i.get('price', 0)) * int(i.get('quantity', 1)) for i in items)
            order_data = {
                'fid': _gen_fid(), 'order_no': _gen_order_no('LY'),
                'user_id': user_id, 'user_name': user_name, 'user_phone': user_phone,
                'items': json.dumps(items, ensure_ascii=False),
                'total_count': total_count,
                'total_amount': total_amount, 'actual_amount': total_amount,
                'status': 'pending', 'pay_status': 0,
                'pickup_type': data.get('pickup_type', 'self'),
                'pickup_address': data.get('pickup_address'),
                'remark': data.get('remark'),
                'ec_id': data.get('ec_id'), 'project_id': data.get('project_id'),
            }
            oid = self.laundry_order_repo.insert(order_data)
            order_data['id'] = oid
            return self.success(order_data, '下单成功')
        except Exception as e:
            return self.error(str(e))

    def list_laundry_orders(self, user_id, status=None, page=1, page_size=20):
        try:
            return self.success(self.laundry_order_repo.find_by_user(user_id, status, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def update_laundry_order_status(self, order_id, status):
        try:
            return self.success({'affected': self.laundry_order_repo.update(order_id, {'status': status})})
        except Exception as e:
            return self.error(str(e))

    # ==================== 会员 ====================

    def get_or_create_member(self, user_id, user_name=None, user_phone=None, ec_id=None, project_id=None):
        try:
            member = self.member_repo.find_by_user(user_id, ec_id)
            if member:
                return self.success(member)
            mdata = {
                'fid': _gen_fid(), 'user_id': user_id,
                'user_name': user_name, 'user_phone': user_phone,
                'points': 0, 'total_points': 0, 'total_consumption': 0, 'balance': 0,
                'status': 1, 'ec_id': ec_id, 'project_id': project_id,
            }
            mid = self.member_repo.insert(mdata)
            mdata['id'] = mid
            return self.success(mdata)
        except Exception as e:
            return self.error(str(e))

    def get_member_info(self, user_id, ec_id=None):
        try:
            member = self.member_repo.find_by_user(user_id, ec_id)
            if not member:
                return self.error('未开通会员')
            return self.success(member)
        except Exception as e:
            return self.error(str(e))

    def list_points_logs(self, user_id, type_filter=None, page=1, page_size=20):
        try:
            return self.success(self.points_log_repo.find_by_user(user_id, type_filter, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def grant_points(self, user_id, points, source='manual', source_id=None, description=None, ec_id=None, project_id=None):
        try:
            member = self.member_repo.find_by_user(user_id, ec_id)
            if not member:
                return self.error('未开通会员')
            self.member_repo.add_points(member['id'], points)
            self.points_log_repo.insert({
                'fid': _gen_fid(), 'member_id': member['id'], 'user_id': user_id,
                'type': 'earn', 'points': points,
                'balance': member.get('points', 0) + points,
                'source': source, 'source_id': source_id,
                'description': description or f'获得{points}积分',
                'ec_id': ec_id, 'project_id': project_id,
            })
            return self.success(None, f'已发放{points}积分')
        except Exception as e:
            return self.error(str(e))

    # ==================== 优惠券 ====================

    def list_coupon_templates(self, ec_id=None):
        try:
            conditions = {'status': 1, 'deleted': 0}
            if ec_id:
                conditions['ec_id'] = ec_id
            return self.success(self.coupon_tpl_repo.find_by_fields(conditions, limit=100))
        except Exception as e:
            return self.error(str(e))

    def create_coupon_template(self, data):
        try:
            data['fid'] = _gen_fid()
            data.setdefault('issued_count', 0)
            data.setdefault('used_count', 0)
            tid = self.coupon_tpl_repo.insert(data)
            return self.success({'id': tid}, '创建成功')
        except Exception as e:
            return self.error(str(e))

    def issue_coupon(self, template_id, user_id, ec_id=None, project_id=None):
        try:
            tpl = self.coupon_tpl_repo.find_by_id(template_id)
            if not tpl:
                return self.error('优惠券模板不存在')
            if tpl.get('total_count', 0) > 0 and tpl.get('issued_count', 0) >= tpl['total_count']:
                return self.error('优惠券已发完')
            coupon_data = {
                'fid': _gen_fid(), 'template_id': template_id,
                'coupon_name': tpl.get('name'), 'coupon_type': tpl.get('type'),
                'coupon_value': tpl.get('value'), 'min_amount': tpl.get('min_amount', 0),
                'user_id': user_id, 'status': 0,
                'expire_time': tpl.get('end_time'),
                'ec_id': ec_id, 'project_id': project_id,
            }
            cid = self.user_coupon_repo.insert(coupon_data)
            self.coupon_tpl_repo.update(template_id, {'issued_count': tpl.get('issued_count', 0) + 1})
            return self.success({'id': cid}, '发放成功')
        except Exception as e:
            return self.error(str(e))

    def list_user_coupons(self, user_id, status=None, page=1, page_size=20):
        try:
            return self.success(self.user_coupon_repo.find_by_user(user_id, status, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def get_available_coupons(self, user_id):
        try:
            return self.success(self.user_coupon_repo.find_available_coupons(user_id))
        except Exception as e:
            return self.error(str(e))

    # ==================== 消费总账 ====================

    def list_consumption_ledger(self, user_id, module=None, page=1, page_size=20):
        try:
            return self.success(self.ledger_repo.find_by_user(user_id, module, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def get_consumption_summary(self, user_id):
        try:
            return self.success(self.ledger_repo.get_user_summary(user_id))
        except Exception as e:
            return self.error(str(e))

    # ==================== 社区服务 ====================

    def list_community_categories(self):
        try:
            return self.success(self.community_cat_repo.find_by_fields({'status': 1, 'deleted': 0}, limit=50))
        except Exception as e:
            return self.error(str(e))

    def list_community_services(self, category_id=None):
        try:
            if category_id:
                return self.success(self.community_svc_repo.find_by_category(int(category_id)))
            return self.success(self.community_svc_repo.find_by_fields({'status': 1, 'deleted': 0}, limit=200))
        except Exception as e:
            return self.error(str(e))

    def list_community_activities(self, ec_id=None, project_id=None):
        try:
            return self.success(self.community_act_repo.find_active(ec_id, project_id))
        except Exception as e:
            return self.error(str(e))

    def get_community_activity(self, activity_id):
        try:
            act = self.community_act_repo.find_by_id(activity_id)
            if not act:
                return self.error('活动不存在')
            return self.success(act)
        except Exception as e:
            return self.error(str(e))

    def sign_up_activity(self, activity_id, user_id, user_name=None, user_phone=None):
        try:
            act = self.community_act_repo.find_by_id(activity_id)
            if not act:
                return self.error('活动不存在')
            if act.get('status') != 1:
                return self.error('活动不在报名期')
            if self.community_signup_repo.check_signed_up(activity_id, user_id):
                return self.error('已报名')
            if act.get('max_participants', 0) > 0 and act.get('current_participants', 0) >= act['max_participants']:
                return self.error('名额已满')
            self.community_signup_repo.insert({
                'fid': _gen_fid(), 'activity_id': activity_id,
                'user_id': user_id, 'user_name': user_name, 'user_phone': user_phone,
                'status': 1, 'ec_id': act.get('ec_id'), 'project_id': act.get('project_id'),
            })
            self.community_act_repo.update(activity_id, {'current_participants': act.get('current_participants', 0) + 1})
            return self.success(None, '报名成功')
        except Exception as e:
            return self.error(str(e))

    def list_community_posts(self, post_type='idle', page=1, page_size=20):
        try:
            return self.success(self.community_post_repo.find_by_type(post_type, page, page_size))
        except Exception as e:
            return self.error(str(e))

    def create_community_post(self, user_id, user_name, data):
        try:
            pdata = {
                'fid': _gen_fid(), 'user_id': user_id, 'user_name': user_name,
                'type': data.get('type', 'idle'),
                'title': data.get('title', ''),
                'content': data.get('content'),
                'images': json.dumps(data.get('images', []), ensure_ascii=False) if data.get('images') else None,
                'price': data.get('price'),
                'contact_info': data.get('contact_info'),
                'status': 1,
                'ec_id': data.get('ec_id'), 'project_id': data.get('project_id'),
            }
            pid = self.community_post_repo.insert(pdata)
            pdata['id'] = pid
            return self.success(pdata, '发布成功')
        except Exception as e:
            return self.error(str(e))

    # ==================== 管理端统计 ====================

    def get_dashboard_stats(self, ec_id=None, project_id=None):
        """管理端首页统计"""
        try:
            stats = {}
            # 各模块订单数
            for name, repo in [
                ('cafeteria_orders', self.cafeteria_order_repo),
                ('drink_orders', self.drink_order_repo),
                ('carwash_orders', self.carwash_order_repo),
                ('laundry_orders', self.laundry_order_repo),
            ]:
                stats[name] = repo.count({'deleted': 0})
            # 预约数
            stats['banquet_bookings'] = self.banquet_booking_repo.count({'deleted': 0})
            stats['sports_bookings'] = self.sports_booking_repo.count({'deleted': 0})
            # 会员数
            stats['members'] = self.member_repo.count({'deleted': 0})
            # 活动数
            stats['activities'] = self.community_act_repo.count({'deleted': 0})
            return self.success(stats)
        except Exception as e:
            return self.error(str(e))

    # ==================== 管理端列表（带分页筛选） ====================

    def admin_list_orders(self, module, page=1, page_size=20, status=None, keyword=None):
        """管理端通用订单列表"""
        try:
            repo_map = {
                'cafeteria': self.cafeteria_order_repo,
                'drink': self.drink_order_repo,
                'carwash': self.carwash_order_repo,
                'laundry': self.laundry_order_repo,
            }
            repo = repo_map.get(module)
            if not repo:
                return self.error('无效模块')
            conditions = {'deleted': 0}
            if status:
                conditions['status'] = status
            return self.success(repo.find_page(page, page_size, conditions))
        except Exception as e:
            return self.error(str(e))

    def admin_list_bookings(self, module, page=1, page_size=20, status=None):
        try:
            repo_map = {
                'banquet': self.banquet_booking_repo,
                'sports': self.sports_booking_repo,
            }
            repo = repo_map.get(module)
            if not repo:
                return self.error('无效模块')
            conditions = {'deleted': 0}
            if status:
                conditions['status'] = status
            return self.success(repo.find_page(page, page_size, conditions))
        except Exception as e:
            return self.error(str(e))
