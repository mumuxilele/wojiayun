#!/usr/bin/env python3
"""Staff H5 Service - Fixed Version"""
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

@app.route('/api/staff/stats', methods=['GET'])
@require_staff
def get_staff_stats(user):
    pending = db.get_total("SELECT COUNT(*) FROM business_applications WHERE deleted=0 AND status='pending'", [])
    processing = db.get_total("SELECT COUNT(*) FROM business_applications WHERE deleted=0 AND status='processing'", [])
    completed_today = db.get_total("SELECT COUNT(*) FROM business_applications WHERE deleted=0 AND status='completed' AND DATE(completed_at)=CURDATE()", [])
    total_orders = db.get_total("SELECT COUNT(*) FROM business_orders WHERE deleted=0", [])
    return jsonify({'success': True, 'data': {'pending': pending, 'processing': processing, 'completed_today': completed_today, 'total_orders': total_orders, 'total_apps': pending+processing}})

@app.route('/api/staff/statistics', methods=['GET'])
@require_staff
def get_staff_statistics(user):
    today_apps = db.get_total("SELECT COUNT(*) FROM business_applications WHERE deleted=0 AND DATE(created_at)=CURDATE()", [])
    pending_apps = db.get_total("SELECT COUNT(*) FROM business_applications WHERE deleted=0 AND status='pending'", [])
    
    app_stats = []
    try:
        app_stats = db.get_all("SELECT status, COUNT(*) as cnt FROM business_applications WHERE deleted=0 GROUP BY status", [])
    except Exception as e:
        print('Error getting app_stats:', e)
    
    order_stats = []
    try:
        total_orders = db.get_total("SELECT COUNT(*) FROM business_orders WHERE deleted=0", [])
        order_stats = [{'status': 'total', 'cnt': total_orders}]
    except Exception as e:
        print('Error getting order_stats:', e)
    
    return jsonify({
        'success': True, 
        'data': {
            'today': {'applications': today_apps, 'orders': 0, 'income': 0},
            'pending_applications': pending_apps,
            'application_stats': app_stats,
            'order_stats': order_stats
        }
    })

@app.route('/api/staff/applications', methods=['GET'])
@require_staff
def get_all_applications(user):
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    app_type = request.args.get('app_type')
    keyword = request.args.get('keyword', '')
    
    where = "deleted=0"
    params = []
    
    if status:
        where += " AND status=%s"
        params.append(status)
    if app_type:
        where += " AND app_type=%s"
        params.append(app_type)
    if keyword:
        where += " AND (title LIKE %s OR content LIKE %s OR user_name LIKE %s)"
        kw = "%" + keyword + "%"
        params.extend([kw, kw, kw])
    
    total = db.get_total("SELECT COUNT(*) FROM business_applications WHERE " + where, params)
    offset = (page - 1) * page_size
    sql = "SELECT id, app_no, app_type, title, status, user_name, user_phone, priority, created_at, assignee_name FROM business_applications WHERE " + where + " ORDER BY priority DESC, created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    items = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size, 'pages': (total + page_size - 1) // page_size}})

@app.route('/api/staff/applications/<app_id>', methods=['GET'])
@require_staff
def get_application_detail(user, app_id):
    sql = "SELECT * FROM business_applications WHERE id=%s AND deleted=0"
    app = db.get_one(sql, [app_id])
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    if app.get('images'):
        import json
        try:
            app['images_list'] = json.loads(app['images'])
        except:
            app['images_list'] = []
    return jsonify({'success': True, 'data': app})

@app.route('/api/staff/applications/<app_id>/process', methods=['POST'])
@require_staff
def process_application(user, app_id):
    data = request.get_json() or {}
    action = data.get('action')
    result = data.get('result', '')
    
    sql = "SELECT * FROM business_applications WHERE id=%s AND deleted=0"
    app = db.get_one(sql, [app_id])
    
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    
    if action == 'process':
        new_status = 'processing'
    elif action == 'reject':
        new_status = 'rejected'
    elif action == 'complete':
        new_status = 'completed'
    else:
        return jsonify({'success': False, 'msg': '无效操作'})
    
    sql = "UPDATE business_applications SET status=%s, result=%s, assignee_id=%s, assignee_name=%s, updated_at=NOW(), completed_at=NOW() WHERE id=%s"
    db.execute(sql, [new_status, result, user['user_id'], user['user_name'], app_id])
    
    return jsonify({'success': True, 'msg': '处理成功'})

@app.route('/api/staff/orders', methods=['GET'])
@require_staff
def get_all_orders(user):
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    
    where = "deleted=0"
    params = []
    
    if status:
        where += " AND status=%s"
        params.append(status)
    
    total = db.get_total("SELECT COUNT(*) FROM business_orders WHERE " + where, params)
    offset = (page - 1) * page_size
    sql = "SELECT id, order_no, status, user_name, user_phone, created_at FROM business_orders WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    orders = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {'items': orders, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/staff/orders/<order_id>', methods=['GET'])
@require_staff
def get_order_detail(user, order_id):
    sql = "SELECT * FROM business_orders WHERE id=%s AND deleted=0"
    order = db.get_one(sql, [order_id])
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    return jsonify({'success': True, 'data': order})

@app.route('/api/staff/orders/<order_id>/status', methods=['POST'])
@require_staff
def update_order_status(user, order_id):
    data = request.get_json() or {}
    status = data.get('status')
    
    if not status:
        return jsonify({'success': False, 'msg': '请提供状态'})
    
    sql = "UPDATE business_orders SET status=%s, updated_at=NOW() WHERE id=%s"
    db.execute(sql, [status, order_id])
    
    return jsonify({'success': True, 'msg': '更新成功'})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'staff-h5', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22312, debug=False)
