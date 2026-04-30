"""
泰山城投 - 用户端 H5 路由
覆盖: 食堂、包间、饮品、场馆、洗车、洗衣、会员、优惠券、社区服务
"""
from flask import Blueprint, request, jsonify
from functools import wraps
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import auth
from business_common.services.taishan_service import TaishanService

taishan_user_bp = Blueprint('taishan_user', __name__)


def get_current_user():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_user(token, isdev) if token else None


def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'msg': '请先登录'})
        return f(user, *args, **kwargs)
    return decorated


def _page_args():
    return int(request.args.get('page', 1)), int(request.args.get('page_size', 20))


# ==================== 食堂 ====================

@taishan_user_bp.route('/api/taishan/cafeteria/categories', methods=['GET'])
def cafeteria_categories():
    svc = TaishanService()
    return jsonify(svc.list_cafeteria_categories(request.args.get('ec_id')))


@taishan_user_bp.route('/api/taishan/cafeteria/dishes', methods=['GET'])
def cafeteria_dishes():
    svc = TaishanService()
    return jsonify(svc.list_cafeteria_dishes(
        request.args.get('category_id'), request.args.get('ec_id'), request.args.get('project_id')))


@taishan_user_bp.route('/api/taishan/cafeteria/dishes/<int:dish_id>', methods=['GET'])
def cafeteria_dish_detail(dish_id):
    svc = TaishanService()
    return jsonify(svc.get_cafeteria_dish(dish_id))


@taishan_user_bp.route('/api/taishan/cafeteria/orders', methods=['POST'])
@require_login
def create_cafeteria_order(user):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.create_cafeteria_order(user['user_id'], user.get('user_name'), user.get('user_phone'), data))


@taishan_user_bp.route('/api/taishan/cafeteria/orders', methods=['GET'])
@require_login
def list_cafeteria_orders(user):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_cafeteria_orders(user['user_id'], request.args.get('status'), page, size))


@taishan_user_bp.route('/api/taishan/cafeteria/orders/<int:order_id>', methods=['GET'])
@require_login
def cafeteria_order_detail(user, order_id):
    svc = TaishanService()
    return jsonify(svc.get_cafeteria_order(order_id))


# ==================== 包间 ====================

@taishan_user_bp.route('/api/taishan/banquet/rooms', methods=['GET'])
def banquet_rooms():
    svc = TaishanService()
    return jsonify(svc.list_banquet_rooms(request.args.get('ec_id')))


@taishan_user_bp.route('/api/taishan/banquet/rooms/<int:room_id>', methods=['GET'])
def banquet_room_detail(room_id):
    svc = TaishanService()
    return jsonify(svc.get_banquet_room(room_id))


@taishan_user_bp.route('/api/taishan/banquet/bookings', methods=['POST'])
@require_login
def create_banquet_booking(user):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.create_banquet_booking(user['user_id'], user.get('user_name'), user.get('user_phone'), data))


@taishan_user_bp.route('/api/taishan/banquet/bookings', methods=['GET'])
@require_login
def list_banquet_bookings(user):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_banquet_bookings(user['user_id'], request.args.get('status'), page, size))


# ==================== 饮品 ====================

@taishan_user_bp.route('/api/taishan/drink/categories', methods=['GET'])
def drink_categories():
    svc = TaishanService()
    return jsonify(svc.list_drink_categories())


@taishan_user_bp.route('/api/taishan/drink/items', methods=['GET'])
def drink_items():
    svc = TaishanService()
    return jsonify(svc.list_drink_items(request.args.get('category_id')))


@taishan_user_bp.route('/api/taishan/drink/orders', methods=['POST'])
@require_login
def create_drink_order(user):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.create_drink_order(user['user_id'], user.get('user_name'), user.get('user_phone'), data))


@taishan_user_bp.route('/api/taishan/drink/orders', methods=['GET'])
@require_login
def list_drink_orders(user):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_drink_orders(user['user_id'], request.args.get('status'), page, size))


# ==================== 运动场馆 ====================

@taishan_user_bp.route('/api/taishan/sports/venues', methods=['GET'])
def sports_venues():
    svc = TaishanService()
    return jsonify(svc.list_sports_venues(request.args.get('type'), request.args.get('ec_id')))


@taishan_user_bp.route('/api/taishan/sports/venues/<int:venue_id>', methods=['GET'])
def sports_venue_detail(venue_id):
    svc = TaishanService()
    return jsonify(svc.get_sports_venue(venue_id))


@taishan_user_bp.route('/api/taishan/sports/bookings', methods=['POST'])
@require_login
def create_sports_booking(user):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.create_sports_booking(user['user_id'], user.get('user_name'), user.get('user_phone'), data))


@taishan_user_bp.route('/api/taishan/sports/bookings', methods=['GET'])
@require_login
def list_sports_bookings(user):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_sports_bookings(user['user_id'], request.args.get('status'), page, size))


# ==================== 洗车 ====================

@taishan_user_bp.route('/api/taishan/carwash/services', methods=['GET'])
def carwash_services():
    svc = TaishanService()
    return jsonify(svc.list_carwash_services())


@taishan_user_bp.route('/api/taishan/carwash/stations', methods=['GET'])
def carwash_stations():
    svc = TaishanService()
    return jsonify(svc.list_carwash_stations())


@taishan_user_bp.route('/api/taishan/carwash/orders', methods=['POST'])
@require_login
def create_carwash_order(user):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.create_carwash_order(user['user_id'], user.get('user_name'), user.get('user_phone'), data))


@taishan_user_bp.route('/api/taishan/carwash/orders', methods=['GET'])
@require_login
def list_carwash_orders(user):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_carwash_orders(user['user_id'], request.args.get('status'), page, size))


# ==================== 洗衣 ====================

@taishan_user_bp.route('/api/taishan/laundry/services', methods=['GET'])
def laundry_services():
    svc = TaishanService()
    return jsonify(svc.list_laundry_services())


@taishan_user_bp.route('/api/taishan/laundry/prices', methods=['GET'])
def laundry_prices():
    svc = TaishanService()
    return jsonify(svc.list_laundry_prices(request.args.get('service_id')))


@taishan_user_bp.route('/api/taishan/laundry/orders', methods=['POST'])
@require_login
def create_laundry_order(user):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.create_laundry_order(user['user_id'], user.get('user_name'), user.get('user_phone'), data))


@taishan_user_bp.route('/api/taishan/laundry/orders', methods=['GET'])
@require_login
def list_laundry_orders(user):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_laundry_orders(user['user_id'], request.args.get('status'), page, size))


# ==================== 会员 ====================

@taishan_user_bp.route('/api/taishan/member/info', methods=['GET'])
@require_login
def member_info(user):
    svc = TaishanService()
    return jsonify(svc.get_member_info(user['user_id'], request.args.get('ec_id')))


@taishan_user_bp.route('/api/taishan/member/register', methods=['POST'])
@require_login
def register_member(user):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.get_or_create_member(
        user['user_id'], user.get('user_name'), user.get('user_phone'),
        data.get('ec_id'), data.get('project_id')))


@taishan_user_bp.route('/api/taishan/member/points', methods=['GET'])
@require_login
def member_points(user):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_points_logs(user['user_id'], request.args.get('type'), page, size))


# ==================== 优惠券 ====================

@taishan_user_bp.route('/api/taishan/coupons', methods=['GET'])
@require_login
def user_coupons(user):
    page, size = _page_args()
    status = request.args.get('status')
    svc = TaishanService()
    return jsonify(svc.list_user_coupons(user['user_id'], int(status) if status is not None else None, page, size))


@taishan_user_bp.route('/api/taishan/coupons/available', methods=['GET'])
@require_login
def available_coupons(user):
    svc = TaishanService()
    return jsonify(svc.get_available_coupons(user['user_id']))


# ==================== 消费总账 ====================

@taishan_user_bp.route('/api/taishan/ledger', methods=['GET'])
@require_login
def consumption_ledger(user):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_consumption_ledger(user['user_id'], request.args.get('module'), page, size))


@taishan_user_bp.route('/api/taishan/ledger/summary', methods=['GET'])
@require_login
def consumption_summary(user):
    svc = TaishanService()
    return jsonify(svc.get_consumption_summary(user['user_id']))


# ==================== 社区服务 ====================

@taishan_user_bp.route('/api/taishan/community/categories', methods=['GET'])
def community_categories():
    svc = TaishanService()
    return jsonify(svc.list_community_categories())


@taishan_user_bp.route('/api/taishan/community/services', methods=['GET'])
def community_services():
    svc = TaishanService()
    return jsonify(svc.list_community_services(request.args.get('category_id')))


@taishan_user_bp.route('/api/taishan/community/activities', methods=['GET'])
def community_activities():
    svc = TaishanService()
    return jsonify(svc.list_community_activities(request.args.get('ec_id'), request.args.get('project_id')))


@taishan_user_bp.route('/api/taishan/community/activities/<int:activity_id>', methods=['GET'])
def community_activity_detail(activity_id):
    svc = TaishanService()
    return jsonify(svc.get_community_activity(activity_id))


@taishan_user_bp.route('/api/taishan/community/activities/<int:activity_id>/signup', methods=['POST'])
@require_login
def sign_up_activity(user, activity_id):
    svc = TaishanService()
    return jsonify(svc.sign_up_activity(activity_id, user['user_id'], user.get('user_name'), user.get('user_phone')))


@taishan_user_bp.route('/api/taishan/community/posts', methods=['GET'])
def community_posts():
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.list_community_posts(request.args.get('type', 'idle'), page, size))


@taishan_user_bp.route('/api/taishan/community/posts', methods=['POST'])
@require_login
def create_community_post(user):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.create_community_post(user['user_id'], user.get('user_name'), data))
