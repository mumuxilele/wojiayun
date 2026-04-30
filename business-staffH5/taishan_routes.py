"""
泰山城投 - 员工端 H5 路由
覆盖: 订单处理、预约审核、核销、状态管理
"""
from flask import Blueprint, request, jsonify
from functools import wraps
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import auth
from business_common.services.taishan_service import TaishanService

taishan_staff_bp = Blueprint('taishan_staff', __name__)


def get_current_staff():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_staff(token, isdev) if token else None


def require_staff(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_staff()
        if not user:
            return jsonify({'success': False, 'msg': '请使用员工账号登录'})
        return f(user, *args, **kwargs)
    return decorated


def _page_args():
    return int(request.args.get('page', 1)), int(request.args.get('page_size', 20))


# ==================== 食堂订单管理 ====================

@taishan_staff_bp.route('/api/staff/taishan/cafeteria/orders', methods=['GET'])
@require_staff
def list_cafeteria_orders(staff):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_orders('cafeteria', page, size, request.args.get('status')))


@taishan_staff_bp.route('/api/staff/taishan/cafeteria/orders/<int:order_id>/status', methods=['POST'])
@require_staff
def update_cafeteria_order(staff, order_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_cafeteria_order_status(order_id, data.get('status')))


# ==================== 包间预约管理 ====================

@taishan_staff_bp.route('/api/staff/taishan/banquet/bookings', methods=['GET'])
@require_staff
def list_banquet_bookings(staff):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_bookings('banquet', page, size, request.args.get('status')))


@taishan_staff_bp.route('/api/staff/taishan/banquet/bookings/<int:booking_id>/status', methods=['POST'])
@require_staff
def update_banquet_booking(staff, booking_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_banquet_booking_status(booking_id, data.get('status'), data.get('remark')))


# ==================== 饮品订单管理 ====================

@taishan_staff_bp.route('/api/staff/taishan/drink/orders', methods=['GET'])
@require_staff
def list_drink_orders(staff):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_orders('drink', page, size, request.args.get('status')))


@taishan_staff_bp.route('/api/staff/taishan/drink/orders/<int:order_id>/status', methods=['POST'])
@require_staff
def update_drink_order(staff, order_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_drink_order_status(order_id, data.get('status')))


# ==================== 场馆预约管理 ====================

@taishan_staff_bp.route('/api/staff/taishan/sports/bookings', methods=['GET'])
@require_staff
def list_sports_bookings(staff):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_bookings('sports', page, size, request.args.get('status')))


@taishan_staff_bp.route('/api/staff/taishan/sports/bookings/<int:booking_id>/status', methods=['POST'])
@require_staff
def update_sports_booking(staff, booking_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_sports_booking_status(booking_id, data.get('status')))


# ==================== 洗车订单管理 ====================

@taishan_staff_bp.route('/api/staff/taishan/carwash/orders', methods=['GET'])
@require_staff
def list_carwash_orders(staff):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_orders('carwash', page, size, request.args.get('status')))


@taishan_staff_bp.route('/api/staff/taishan/carwash/orders/<int:order_id>/status', methods=['POST'])
@require_staff
def update_carwash_order(staff, order_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_carwash_order_status(order_id, data.get('status')))


# ==================== 洗衣订单管理 ====================

@taishan_staff_bp.route('/api/staff/taishan/laundry/orders', methods=['GET'])
@require_staff
def list_laundry_orders(staff):
    page, size = _page_args()
    svc = TaishanService()
    return jsonify(svc.admin_list_orders('laundry', page, size, request.args.get('status')))


@taishan_staff_bp.route('/api/staff/taishan/laundry/orders/<int:order_id>/status', methods=['POST'])
@require_staff
def update_laundry_order(staff, order_id):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.update_laundry_order_status(order_id, data.get('status')))


# ==================== 会员管理 ====================

@taishan_staff_bp.route('/api/staff/taishan/member/grant-points', methods=['POST'])
@require_staff
def grant_points(staff):
    data = request.get_json() or {}
    svc = TaishanService()
    return jsonify(svc.grant_points(
        data.get('user_id'), int(data.get('points', 0)),
        source='manual', description=data.get('description'),
        ec_id=data.get('ec_id'), project_id=data.get('project_id')))


# ==================== 活动报名管理 ====================

@taishan_staff_bp.route('/api/staff/taishan/community/activities/<int:activity_id>/signups', methods=['GET'])
@require_staff
def list_activity_signups(staff, activity_id):
    from business_common.repositories.community_repository import CommunityActivitySignupRepository
    repo = CommunityActivitySignupRepository()
    page, size = _page_args()
    return jsonify({'success': True, 'data': repo.find_by_activity(activity_id, page, size)})
