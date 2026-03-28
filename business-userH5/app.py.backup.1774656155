#!/usr/bin/env python3
"""
社区商业 - 用户端 H5 服务
端口: 22311
优化版本 - 合并统计接口，提升性能
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import config, db, auth, utils

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

@app.after_request
def add_headers(response):
    response.headers['X-Response-Time'] = str(int(time.time() * 1000))
    return response

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

@app.route('/api/user/stats', methods=['GET'])
@require_login
def get_user_stats(user):
    uid = user['user_id']
    pending = db.get_total("SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='pending'", [uid])
    processing = db.get_total("SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='processing'", [uid])
    completed = db.get_total("SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='completed'", [uid])
    orders = db.get_total("SELECT COUNT(*) FROM business_orders WHERE user_id=%s AND deleted=0", [uid])
    return jsonify({'success': True, 'data': {'pending': pending, 'processing': processing, 'completed': completed, 'total_apps': pending+processing+completed, 'orders': orders}})

@app.route('/api/user/applications', methods=['GET'])
@require_login
def get_user_applications(user):
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    app_type = request.args.get('app_type')
    where = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    if status:
        where += " AND status=%s"
        params.append(status)
    if app_type:
        where += " AND app_type=%s"
        params.append(app_type)
    total = db.get_total("SELECT COUNT(*) FROM business_applications WHERE " + where, params)
    offset = (page - 1) * page_size
    sql = "SELECT id, app_no, app_type, title, status, created_at, updated_at FROM business_applications WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    items = db.get_all(sql, params)
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size, 'pages': (total + page_size - 1) // page_size}})

@app.route('/api/user/applications', methods=['POST'])
@require_login
def create_application(user):
    data = request.get_json() or {}
    app_type = data.get('app_type')
    title = data.get('title')
    content = data.get('content', '')
    images = data.get('images', '[]')
    priority = data.get('priority', 0)
    if not app_type or not title:
        return jsonify({'success': False, 'msg': '请填写必要信息'})
    app_no = utils.generate_no('APP')
    sql = "INSERT INTO business_applications (app_no, app_type, title, content, user_id, user_name, user_phone, ec_id, project_id, status, images, priority) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)"
    db.execute(sql, [app_no, app_type, title, content, user['user_id'], user['user_name'], user['phone'], user.get('ec_id'), user.get('project_id'), images, priority])
    return jsonify({'success': True, 'msg': '提交成功', 'data': {'app_no': app_no}})

@app.route('/api/user/applications/<app_id>', methods=['GET'])
@require_login
def get_application_detail(user, app_id):
    sql = "SELECT * FROM business_applications WHERE id=%s AND user_id=%s AND deleted=0"
    app = db.get_one(sql, [app_id, user['user_id']])
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    if app.get('images'):
        import json
        try:
            app['images_list'] = json.loads(app['images'])
        except:
            app['images_list'] = []
    return jsonify({'success': True, 'data': app})

@app.route('/api/user/orders', methods=['GET'])
@require_login
def get_user_orders(user):
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    where = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    if status:
        where += " AND status=%s"
        params.append(status)
    total = db.get_total("SELECT COUNT(*) FROM business_orders WHERE " + where, params)
    offset = (page - 1) * page_size
    sql = "SELECT id, order_no, title, amount, status, created_at FROM business_orders WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    items = db.get_all(sql, params)
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/user/orders/<order_id>', methods=['GET'])
@require_login
def get_order_detail(user, order_id):
    sql = "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0"
    order = db.get_one(sql, [order_id, user['user_id']])
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    return jsonify({'success': True, 'data': order})

@app.route('/api/user/bookings', methods=['GET'])
@require_login
def get_user_bookings(user):
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    total = db.get_total("SELECT COUNT(*) FROM business_bookings WHERE user_id=%s AND deleted=0", [user['user_id']])
    offset = (page - 1) * page_size
    sql = "SELECT * FROM business_bookings WHERE user_id=%s AND deleted=0 ORDER BY created_at DESC LIMIT %s OFFSET %s"
    items = db.get_all(sql, [user['user_id'], page_size, offset])
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'user-h5', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22311, debug=False)
