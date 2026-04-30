#!/usr/bin/env python3
"""
社区商业 - 管理端 Web 服务（MVC 架构）
端口: 22313
路由层仅处理 HTTP 请求/响应，业务逻辑委托给 AdminService
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import config, auth, error_handler
from business_common.services import AdminService

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

error_handler.register_error_handlers(app)


# ============ 管理员认证 ============

def get_current_admin():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_staff(token, isdev) if token else None


def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_admin()
        if not user:
            return jsonify({'success': False, 'msg': '请使用管理员账号登录'})
        return f(user, *args, **kwargs)
    return decorated


# ============ 申请单管理 ============

@app.route('/api/admin/applications', methods=['GET'])
@require_admin
def list_applications(user):
    """申请单列表"""
    svc = AdminService()
    return jsonify(svc.list_applications(
        status=request.args.get('status'),
        app_type=request.args.get('app_type'),
        keyword=request.args.get('keyword', ''),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/admin/applications/<int:app_id>', methods=['GET'])
@require_admin
def get_application(user, app_id):
    """申请单详情"""
    svc = AdminService()
    return jsonify(svc.get_application(app_id))


@app.route('/api/admin/applications/<int:app_id>', methods=['PUT'])
@require_admin
def update_application(user, app_id):
    """修改申请单"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.update_application(app_id, data))


@app.route('/api/admin/applications/<int:app_id>', methods=['DELETE'])
@require_admin
def delete_application(user, app_id):
    """删除申请单"""
    svc = AdminService()
    return jsonify(svc.delete_application(app_id))


# ============ 订单管理 ============

@app.route('/api/admin/orders', methods=['GET'])
@require_admin
def list_orders(user):
    """订单列表"""
    svc = AdminService()
    return jsonify(svc.list_orders(
        status=request.args.get('status'),
        keyword=request.args.get('keyword', ''),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/admin/orders/<int:order_id>', methods=['GET'])
@require_admin
def get_order(user, order_id):
    """订单详情"""
    svc = AdminService()
    return jsonify(svc.get_order(order_id))


@app.route('/api/admin/orders/<int:order_id>', methods=['PUT'])
@require_admin
def update_order(user, order_id):
    """修改订单"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.update_order(order_id, data))


@app.route('/api/admin/orders/<int:order_id>', methods=['DELETE'])
@require_admin
def delete_order(user, order_id):
    """删除订单"""
    svc = AdminService()
    return jsonify(svc.delete_order(order_id))


# ============ 门店管理 ============

@app.route('/api/admin/shops', methods=['GET'])
@require_admin
def list_shops(user):
    """门店列表"""
    svc = AdminService()
    return jsonify(svc.list_shops())


@app.route('/api/admin/shops/<int:shop_id>', methods=['GET'])
@require_admin
def get_shop(user, shop_id):
    """门店详情"""
    svc = AdminService()
    return jsonify(svc.get_shop(shop_id))


@app.route('/api/admin/shops', methods=['POST'])
@require_admin
def create_shop(user):
    """创建门店"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.create_shop(data))


@app.route('/api/admin/shops/<int:shop_id>', methods=['PUT'])
@require_admin
def update_shop(user, shop_id):
    """修改门店"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.update_shop(shop_id, data))


@app.route('/api/admin/shops/<int:shop_id>', methods=['DELETE'])
@require_admin
def delete_shop(user, shop_id):
    """删除门店"""
    svc = AdminService()
    return jsonify(svc.delete_shop(shop_id))


# ============ 统计数据 ============

@app.route('/api/admin/statistics', methods=['GET'])
@require_admin
def get_statistics(user):
    """综合统计"""
    svc = AdminService()
    return jsonify(svc.get_statistics())


# ============ 用户管理 ============

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def list_users(user):
    """用户列表"""
    svc = AdminService()
    return jsonify(svc.list_members(
        keyword=request.args.get('keyword', ''),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


# ============ 健康检查 ============

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'module': 'admin-web', 'status': 'ok'})


# ============ 静态文件 ============

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


# ============ 泰山城投模块 ============
from taishan_routes import taishan_admin_bp
app.register_blueprint(taishan_admin_bp)

# ============ 启动 ============

if __name__ == '__main__':
    print("管理端 Web 服务启动在端口 " + str(config.PORTS['admin']))
    app.run(host='0.0.0.0', port=config.PORTS['admin'], debug=False)
