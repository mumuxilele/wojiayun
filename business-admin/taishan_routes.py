"""
泰山城投 - 管理端路由
覆盖: 全模块管理、数据统计、优惠券管理、会员管理、内容管理
"""
from flask import Blueprint, request, jsonify
from functools import wraps
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import auth
from business_common.services.taishan_service import TaishanService

taishan_admin_bp = Blueprint('taishan_admin', __name__)


def get_current_admin():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_staff(token, isdev) if token else None


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_admin()
        if not user:
            return jsonify({'success': False, 'msg': '请使用管理员账号登录'})
        return f(user, *args, **kwargs)
    return decorated


def _page_args():
    return int(request.args.get('page', 1)), int(request.args.get('page_size', 20))


# ==================== 仪表盘 ====================

@taishan_admin_bp.route('/api/admin/taishan/dashboard', methods=['GET'])
@require_admin
def dashboard(admin):
    svc = TaishanService()
    return jsonify(svc.get_dashboard_stats(request.args.get('ec_id'), request.args.get('project_id')))


# ==================== 食堂管理 ====================

@taishan_admin_bp.route('/api/admin/taishan/cafeteria/categories', methods=['GET'])
@require_admin
def list_cafeteria_categories(admin):
    svc = TaishanService()
    return jsonify(svc.list_cafeteria_categories(request.args.get('ec_id')))


@taishan_admin_bp.route('/api/admin/taishan/cafeteria/categories', methods=['POST'])
@require_admin
def create_cafeteria_category(admin):
    data = request.get_json() or {}
    from business_common.repositories.cafeteria_repository import CafeteriaCategoryRepository
    import uuid
    data['fid'] = str(uuid.uuid4())
    repo = CafeteriaCategoryRepository()
    cid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': cid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/cafeteria/categories/<int:cat_id>', methods=['PUT'])
@require_admin
def update_cafeteria_category(admin, cat_id):
    data = request.get_json() or {}
    from business_common.repositories.cafeteria_repository import CafeteriaCategoryRepository
    repo = CafeteriaCategoryRepository()
    repo.update(cat_id, data)
    return jsonify({'success': True, 'msg': '更新成功'})


@taishan_admin_bp.route('/api/admin/taishan/cafeteria/dishes', methods=['GET'])
@require_admin
def list_cafeteria_dishes(admin):
    svc = TaishanService()
    return jsonify(svc.list_cafeteria_dishes(request.args.get('category_id'), request.args.get('ec_id')))


@taishan_admin_bp.route('/api/admin/taishan/cafeteria/dishes', methods=['POST'])
@require_admin
def create_cafeteria_dish(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.cafeteria_repository import CafeteriaDishRepository
    repo = CafeteriaDishRepository()
    did = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': did}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/cafeteria/dishes/<int:dish_id>', methods=['PUT'])
@require_admin
def update_cafeteria_dish(admin, dish_id):
    data = request.get_json() or {}
    from business_common.repositories.cafeteria_repository import CafeteriaDishRepository
    repo = CafeteriaDishRepository()
    repo.update(dish_id, data)
    return jsonify({'success': True, 'msg': '更新成功'})


@taishan_admin_bp.route('/api/admin/taishan/cafeteria/dishes/<int:dish_id>', methods=['DELETE'])
@require_admin
def delete_cafeteria_dish(admin, dish_id):
    from business_common.repositories.cafeteria_repository import CafeteriaDishRepository
    repo = CafeteriaDishRepository()
    repo.soft_delete(dish_id)
    return jsonify({'success': True, 'msg': '已删除'})


@taishan_admin_bp.route('/api/admin/taishan/cafeteria/orders', methods=['GET'])
@require_admin
def list_cafeteria_orders(admin):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_orders('cafeteria', page, size, request.args.get('status')))


@taishan_admin_bp.route('/api/admin/taishan/cafeteria/orders/<int:order_id>/status', methods=['POST'])
@require_admin
def update_cafeteria_order(admin, order_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_cafeteria_order_status(order_id, data.get('status')))


# ==================== 包间管理 ====================

@taishan_admin_bp.route('/api/admin/taishan/banquet/rooms', methods=['GET'])
@require_admin
def list_banquet_rooms(admin):
    svc = TaishanService()
    return jsonify(svc.list_banquet_rooms(request.args.get('ec_id')))


@taishan_admin_bp.route('/api/admin/taishan/banquet/rooms', methods=['POST'])
@require_admin
def create_banquet_room(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.banquet_repository import BanquetRoomRepository
    repo = BanquetRoomRepository()
    rid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': rid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/banquet/rooms/<int:room_id>', methods=['PUT'])
@require_admin
def update_banquet_room(admin, room_id):
    data = request.get_json() or {}
    from business_common.repositories.banquet_repository import BanquetRoomRepository
    repo = BanquetRoomRepository()
    repo.update(room_id, data)
    return jsonify({'success': True, 'msg': '更新成功'})


@taishan_admin_bp.route('/api/admin/taishan/banquet/bookings', methods=['GET'])
@require_admin
def list_banquet_bookings(admin):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_bookings('banquet', page, size, request.args.get('status')))


@taishan_admin_bp.route('/api/admin/taishan/banquet/bookings/<int:booking_id>/status', methods=['POST'])
@require_admin
def update_banquet_booking(admin, booking_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_banquet_booking_status(booking_id, data.get('status'), data.get('remark')))


# ==================== 饮品管理 ====================

@taishan_admin_bp.route('/api/admin/taishan/drink/categories', methods=['GET'])
@require_admin
def list_drink_categories(admin):
    svc = TaishanService()
    return jsonify(svc.list_drink_categories())


@taishan_admin_bp.route('/api/admin/taishan/drink/categories', methods=['POST'])
@require_admin
def create_drink_category(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.drink_repository import DrinkCategoryRepository
    repo = DrinkCategoryRepository()
    cid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': cid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/drink/items', methods=['GET'])
@require_admin
def list_drink_items(admin):
    svc = TaishanService()
    return jsonify(svc.list_drink_items(request.args.get('category_id')))


@taishan_admin_bp.route('/api/admin/taishan/drink/items', methods=['POST'])
@require_admin
def create_drink_item(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.drink_repository import DrinkItemRepository
    repo = DrinkItemRepository()
    iid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': iid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/drink/items/<int:item_id>', methods=['PUT'])
@require_admin
def update_drink_item(admin, item_id):
    data = request.get_json() or {}
    from business_common.repositories.drink_repository import DrinkItemRepository
    repo = DrinkItemRepository()
    repo.update(item_id, data)
    return jsonify({'success': True, 'msg': '更新成功'})


@taishan_admin_bp.route('/api/admin/taishan/drink/orders', methods=['GET'])
@require_admin
def list_drink_orders(admin):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_orders('drink', page, size, request.args.get('status')))


@taishan_admin_bp.route('/api/admin/taishan/drink/orders/<int:order_id>/status', methods=['POST'])
@require_admin
def update_drink_order(admin, order_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_drink_order_status(order_id, data.get('status')))


# ==================== 场馆管理 ====================

@taishan_admin_bp.route('/api/admin/taishan/sports/venues', methods=['GET'])
@require_admin
def list_sports_venues(admin):
    svc = TaishanService()
    return jsonify(svc.list_sports_venues(request.args.get('type'), request.args.get('ec_id')))


@taishan_admin_bp.route('/api/admin/taishan/sports/venues', methods=['POST'])
@require_admin
def create_sports_venue(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.sports_repository import SportsVenueRepository
    repo = SportsVenueRepository()
    vid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': vid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/sports/venues/<int:venue_id>', methods=['PUT'])
@require_admin
def update_sports_venue(admin, venue_id):
    data = request.get_json() or {}
    from business_common.repositories.sports_repository import SportsVenueRepository
    repo = SportsVenueRepository()
    repo.update(venue_id, data)
    return jsonify({'success': True, 'msg': '更新成功'})


@taishan_admin_bp.route('/api/admin/taishan/sports/bookings', methods=['GET'])
@require_admin
def list_sports_bookings(admin):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_bookings('sports', page, size, request.args.get('status')))


@taishan_admin_bp.route('/api/admin/taishan/sports/bookings/<int:booking_id>/status', methods=['POST'])
@require_admin
def update_sports_booking(admin, booking_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_sports_booking_status(booking_id, data.get('status')))


# ==================== 洗车管理 ====================

@taishan_admin_bp.route('/api/admin/taishan/carwash/services', methods=['GET'])
@require_admin
def list_carwash_services(admin):
    svc = TaishanService()
    return jsonify(svc.list_carwash_services())


@taishan_admin_bp.route('/api/admin/taishan/carwash/services', methods=['POST'])
@require_admin
def create_carwash_service(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.carwash_laundry_repository import CarwashServiceRepository
    repo = CarwashServiceRepository()
    sid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': sid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/carwash/stations', methods=['GET'])
@require_admin
def list_carwash_stations(admin):
    svc = TaishanService()
    return jsonify(svc.list_carwash_stations())


@taishan_admin_bp.route('/api/admin/taishan/carwash/stations', methods=['POST'])
@require_admin
def create_carwash_station(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.carwash_laundry_repository import CarwashStationRepository
    repo = CarwashStationRepository()
    sid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': sid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/carwash/orders', methods=['GET'])
@require_admin
def list_carwash_orders(admin):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_orders('carwash', page, size, request.args.get('status')))


@taishan_admin_bp.route('/api/admin/taishan/carwash/orders/<int:order_id>/status', methods=['POST'])
@require_admin
def update_carwash_order(admin, order_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_carwash_order_status(order_id, data.get('status')))


# ==================== 洗衣管理 ====================

@taishan_admin_bp.route('/api/admin/taishan/laundry/services', methods=['GET'])
@require_admin
def list_laundry_services(admin):
    svc = TaishanService()
    return jsonify(svc.list_laundry_services())


@taishan_admin_bp.route('/api/admin/taishan/laundry/services', methods=['POST'])
@require_admin
def create_laundry_service(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.carwash_laundry_repository import LaundryServiceRepository
    repo = LaundryServiceRepository()
    sid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': sid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/laundry/prices', methods=['GET'])
@require_admin
def list_laundry_prices(admin):
    svc = TaishanService()
    return jsonify(svc.list_laundry_prices(request.args.get('service_id')))


@taishan_admin_bp.route('/api/admin/taishan/laundry/prices', methods=['POST'])
@require_admin
def create_laundry_price(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.carwash_laundry_repository import LaundryPriceRepository
    repo = LaundryPriceRepository()
    pid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': pid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/laundry/orders', methods=['GET'])
@require_admin
def list_laundry_orders(admin):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_orders('laundry', page, size, request.args.get('status')))


@taishan_admin_bp.route('/api/admin/taishan/laundry/orders/<int:order_id>/status', methods=['POST'])
@require_admin
def update_laundry_order(admin, order_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_laundry_order_status(order_id, data.get('status')))


# ==================== 会员管理 ====================

@taishan_admin_bp.route('/api/admin/taishan/members', methods=['GET'])
@require_admin
def list_members(admin):
    page, size = _page_args()
    from business_common.repositories.member_repository_v2 import MemberRepository as MemberRepoV2
    repo = MemberRepoV2()
    return jsonify({'success': True, 'data': repo.find_page(page, size, {'deleted': 0})})


@taishan_admin_bp.route('/api/admin/taishan/members/<int:member_id>/grant-points', methods=['POST'])
@require_admin
def admin_grant_points(admin, member_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.grant_points(data.get('user_id'), int(data.get('points', 0)),
                                     source='manual', description=data.get('description')))


# ==================== 优惠券管理 ====================

@taishan_admin_bp.route('/api/admin/taishan/coupons/templates', methods=['GET'])
@require_admin
def list_coupon_templates(admin):
    svc = TaishanService()
    return jsonify(svc.list_coupon_templates(request.args.get('ec_id')))


@taishan_admin_bp.route('/api/admin/taishan/coupons/templates', methods=['POST'])
@require_admin
def create_coupon_template(admin):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.create_coupon_template(data))


@taishan_admin_bp.route('/api/admin/taishan/coupons/issue', methods=['POST'])
@require_admin
def issue_coupon(admin):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.issue_coupon(data.get('template_id'), data.get('user_id'),
                                     data.get('ec_id'), data.get('project_id')))


# ==================== 社区管理 ====================

@taishan_admin_bp.route('/api/admin/taishan/community/categories', methods=['GET'])
@require_admin
def list_community_categories(admin):
    svc = TaishanService()
    return jsonify(svc.list_community_categories())


@taishan_admin_bp.route('/api/admin/taishan/community/categories', methods=['POST'])
@require_admin
def create_community_category(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.community_repository import CommunityCategoryRepository
    repo = CommunityCategoryRepository()
    cid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': cid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/community/services', methods=['GET'])
@require_admin
def list_community_services(admin):
    svc = TaishanService()
    return jsonify(svc.list_community_services(request.args.get('category_id')))


@taishan_admin_bp.route('/api/admin/taishan/community/services', methods=['POST'])
@require_admin
def create_community_service(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.community_repository import CommunityServiceRepository
    repo = CommunityServiceRepository()
    sid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': sid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/community/activities', methods=['GET'])
@require_admin
def list_community_activities(admin):
    svc = TaishanService()
    return jsonify(svc.list_community_activities(request.args.get('ec_id'), request.args.get('project_id')))


@taishan_admin_bp.route('/api/admin/taishan/community/activities', methods=['POST'])
@require_admin
def create_community_activity(admin):
    data = request.get_json() or {}
    import uuid
    data['fid'] = str(uuid.uuid4())
    from business_common.repositories.community_repository import CommunityActivityRepository
    repo = CommunityActivityRepository()
    aid = repo.insert(data)
    return jsonify({'success': True, 'data': {'id': aid}, 'msg': '创建成功'})


@taishan_admin_bp.route('/api/admin/taishan/community/activities/<int:activity_id>', methods=['PUT'])
@require_admin
def update_community_activity(admin, activity_id):
    data = request.get_json() or {}
    from business_common.repositories.community_repository import CommunityActivityRepository
    repo = CommunityActivityRepository()
    repo.update(activity_id, data)
    return jsonify({'success': True, 'msg': '更新成功'})


@taishan_admin_bp.route('/api/admin/taishan/community/posts', methods=['GET'])
@require_admin
def list_community_posts(admin):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_community_posts(request.args.get('type', 'idle'), page, size))


@taishan_admin_bp.route('/api/admin/taishan/community/posts/<int:post_id>/status', methods=['POST'])
@require_admin
def update_post_status(admin, post_id):
    data = request.get_json() or {}
    from business_common.repositories.community_repository import CommunityPostRepository
    repo = CommunityPostRepository()
    repo.update(post_id, {'status': data.get('status', 1)})
    return jsonify({'success': True, 'msg': '更新成功'})


# ==================== 消费总账 ====================

@taishan_admin_bp.route('/api/admin/taishan/ledger', methods=['GET'])
@require_admin
def admin_ledger(admin):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_consumption_ledger(request.args.get('user_id'), request.args.get('module'), page, size))


@taishan_admin_bp.route('/api/admin/taishan/ledger/summary', methods=['GET'])
@require_admin
def admin_ledger_summary(admin):
    svc = TaishanService()
    return jsonify(svc.get_consumption_summary(request.args.get('user_id')))
