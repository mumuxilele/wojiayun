#!/usr/bin/env python3
"""
社区商业 - 用户端 H5 服务（MVC 架构）
端口: 22311
路由层仅处理 HTTP 请求/响应，业务逻辑委托给 Service 层
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import config, auth, error_handler
from business_common.services import ApplicationService, OrderService, ProductService
from business_common.services import UserService as _unused
from business_common.models import Application
from business_common.repositories.booking_repository import BookingRepository
from business_common.repositories.shop_repository import ShopRepository
from business_common.repositories.product_repository import ProductRepository

# 泰山城投模块
from taishan_routes import taishan_user_bp

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

error_handler.register_error_handlers(app)

# 注册泰山城投蓝图
app.register_blueprint(taishan_user_bp)


# ============ 用户认证 ============

def get_current_user():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_user(token, isdev) if token else None


def require_login(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'msg': '请先登录'})
        return f(user, *args, **kwargs)
    return decorated


# ============ 申请单 API ============

@app.route('/api/user/applications', methods=['GET'])
@require_login
def get_user_applications(user):
    """获取我的申请列表"""
    svc = ApplicationService()
    return jsonify(svc.get_user_applications(
        user_id=user['user_id'],
        status=request.args.get('status'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/user/applications', methods=['POST'])
@require_login
def create_application(user):
    """提交新申请"""
    data = request.get_json() or {}
    svc = ApplicationService()
    return jsonify(svc.create_application(
        user_id=user['user_id'],
        user_name=user['user_name'],
        type_code=data.get('app_type', ''),
        title=data.get('title', ''),
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id'),
        attachments=data.get('images', []) if isinstance(data.get('images'), list) else None,
        remark=data.get('content', '')
    ))


@app.route('/api/user/applications/<int:app_id>', methods=['GET'])
@require_login
def get_application_detail(user, app_id):
    """获取申请详情"""
    svc = ApplicationService()
    return jsonify(svc.get_application_detail(app_id))


@app.route('/api/user/applications/<int:app_id>', methods=['PUT'])
@require_login
def update_application(user, app_id):
    """修改申请（只能修改待处理的）"""
    data = request.get_json() or {}
    svc = ApplicationService()
    return jsonify(svc.update_application(
        app_id=app_id,
        user_id=user['user_id'],
        data=data,
        only_pending=True
    ))


# ============ 订单 API ============

@app.route('/api/user/orders', methods=['GET'])
@require_login
def get_user_orders(user):
    """获取我的订单"""
    svc = OrderService()
    return jsonify(svc.get_user_orders(
        user_id=user['user_id'],
        status=request.args.get('status'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/user/orders', methods=['POST'])
@require_login
def create_order(user):
    """创建订单"""
    data = request.get_json() or {}
    items = data.get('items', [])
    if not items:
        return jsonify({'success': False, 'msg': '订单商品不能为空'})
    svc = OrderService()
    return jsonify(svc.create_order(
        user_id=user['user_id'],
        user_name=user['user_name'],
        items=items,
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id'),
        receiver_name=data.get('receiver_name'),
        receiver_phone=data.get('receiver_phone'),
        receiver_address=data.get('receiver_address'),
        remark=data.get('remark')
    ))


@app.route('/api/user/orders/<int:order_id>/pay', methods=['POST'])
@require_login
def pay_order(user, order_id):
    """支付订单"""
    svc = OrderService()
    return jsonify(svc.pay_order(order_id, user_id=user['user_id']))


# ============ 预约 API ============

@app.route('/api/user/bookings', methods=['GET'])
@require_login
def get_user_bookings(user):
    """获取我的预约"""
    repo = BookingRepository()
    bookings = repo.find_by_user(user['user_id'])
    return jsonify({'success': True, 'data': bookings})


# ============ 门店/商品 API ============

@app.route('/api/shops', methods=['GET'])
def get_shops():
    """获取门店列表"""
    repo = ShopRepository()
    shop_type = request.args.get('type')
    shops = repo.find_open_shops(shop_type=shop_type)
    return jsonify({'success': True, 'data': shops})


@app.route('/api/products', methods=['GET'])
def get_products():
    """获取商品列表"""
    repo = ProductRepository()
    shop_id = request.args.get('shop_id')
    if shop_id:
        products = repo.find_by_field('shop_id', shop_id, limit=200)
    else:
        products = repo.find_by_field('status', 'available', limit=200)
    return jsonify({'success': True, 'data': products})


# ============ 健康检查 ============

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'module': 'user-h5', 'status': 'ok'})


# ============ 静态文件 ============

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


# ============ 启动 ============

if __name__ == '__main__':
    print("用户端 H5 服务启动在端口 " + str(config.PORTS['user']))
    app.run(host='0.0.0.0', port=config.PORTS['user'], debug=False)
