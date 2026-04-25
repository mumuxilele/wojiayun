#!/usr/bin/env python3
"""
社区商业 - 员工端 H5 服务（MVC 架构）
端口: 22312
路由层仅处理 HTTP 请求/响应，业务逻辑委托给 StaffService
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import config, auth, error_handler
from business_common.services import StaffService
from business_common.services import ApplicationService, OrderService
from business_common.models import Application

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

error_handler.register_error_handlers(app)


# ============ 员工认证 ============

def get_current_staff():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_staff(token, isdev) if token else None


def require_staff(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_staff()
        if not user:
            return jsonify({'success': False, 'msg': '请使用员工账号登录'})
        return f(user, *args, **kwargs)
    return decorated


# ============ 申请单 API ============

@app.route('/api/staff/applications', methods=['GET'])
@require_staff
def get_all_applications(user):
    """获取所有申请列表"""
    svc = StaffService()
    return jsonify(svc.list_applications(
        user=user,
        status=request.args.get('status'),
        keyword=request.args.get('keyword', ''),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/staff/applications/<int:app_id>', methods=['GET'])
@require_staff
def get_application_detail(user, app_id):
    """获取申请详情"""
    svc = StaffService()
    return jsonify(svc.get_application_detail(app_id))


@app.route('/api/staff/applications/<int:app_id>/process', methods=['POST'])
@require_staff
def process_application(user, app_id):
    """处理申请（审批）"""
    data = request.get_json() or {}
    action = data.get('action')  # process/reject/complete
    remark = data.get('remark', '') or data.get('result', '')

    status_map = {
        'process': Application.STATUS_PROCESSING,
        'reject': Application.STATUS_REJECTED,
        'complete': Application.STATUS_COMPLETED
    }
    new_status = status_map.get(action)
    if not new_status:
        return jsonify({'success': False, 'msg': '无效操作'})

    svc = ApplicationService()
    return jsonify(svc.update_status(
        app_id=app_id, status=new_status,
        approver_id=user.get('user_id'),
        approver_name=user.get('user_name'),
        remark=remark
    ))


# ============ 订单 API ============

@app.route('/api/staff/orders', methods=['GET'])
@require_staff
def get_all_orders(user):
    """获取所有订单"""
    svc = StaffService()
    return jsonify(svc.list_orders(
        user=user,
        status=request.args.get('status'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/staff/orders/<int:order_id>', methods=['GET'])
@require_staff
def get_order_detail(user, order_id):
    """获取订单详情"""
    svc = OrderService()
    return jsonify(svc.get_order_detail(order_id))


# ============ 统计 ============

@app.route('/api/staff/statistics', methods=['GET'])
@require_staff
def get_statistics(user):
    """获取统计数据"""
    svc = StaffService()
    return jsonify(svc.get_statistics(user))


# ============ 会员 ============

@app.route('/api/staff/members', methods=['GET'])
@require_staff
def get_members(user):
    """获取会员列表"""
    svc = StaffService()
    return jsonify(svc.list_members(
        keyword=request.args.get('keyword', ''),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


# ============ 健康检查 ============

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'module': 'staff-h5', 'status': 'ok'})


# ============ 静态文件 ============

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


# ============ 启动 ============

if __name__ == '__main__':
    print("员工端 H5 服务启动在端口 " + str(config.PORTS['staff']))
    app.run(host='0.0.0.0', port=config.PORTS['staff'], debug=False)
