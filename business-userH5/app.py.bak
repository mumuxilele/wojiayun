#!/usr/bin/env python3
"""
社区商业 - 用户端 H5 服务
端口: 22311
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import config, db, auth, utils

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ============ 用户认证 ============

def get_current_user():
    """获取当前用户"""
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_user(token, isdev) if token else None

def require_login(f):
    """登录装饰器"""
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
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    status = request.args.get('status')
    
    where = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    
    if status:
        where += " AND status=%s"
        params.append(status)
    
    # 获取总数
    total = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {where}", params)
    
    # 获取列表
    offset = (page - 1) * page_size
    sql = f"SELECT * FROM business_applications WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.append(page_size)
    params.append(offset)
    items = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size
    }})

@app.route('/api/user/applications', methods=['POST'])
@require_login
def create_application(user):
    """提交新申请"""
    data = request.get_json() or {}
    
    app_type = data.get('app_type')
    title = data.get('title')
    content = data.get('content', '')
    images = data.get('images', '[]')
    
    if not app_type or not title:
        return jsonify({'success': False, 'msg': '请填写必要信息'})
    
    app_no = utils.generate_no('APP')
    
    sql = """INSERT INTO business_applications 
        (app_no, app_type, title, content, user_id, user_name, user_phone, ec_id, project_id, status, images)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)"""
    
    db.execute(sql, [
        app_no, app_type, title, content,
        user['user_id'], user['user_name'], user['phone'],
        user.get('ec_id'), user.get('project_id'),
        images
    ])
    
    return jsonify({'success': True, 'msg': '提交成功', 'data': {'app_no': app_no}})

@app.route('/api/user/applications/<app_id>', methods=['GET'])
@require_login
def get_application_detail(user, app_id):
    """获取申请详情"""
    sql = "SELECT * FROM business_applications WHERE id=%s AND user_id=%s AND deleted=0"
    app = db.get_one(sql, [app_id, user['user_id']])
    
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    
    return jsonify({'success': True, 'data': app})

@app.route('/api/user/applications/<app_id>', methods=['PUT'])
@require_login
def update_application(user, app_id):
    """修改申请(只能修改待处理的)"""
    data = request.get_json() or {}
    
    # 检查是否是自己的申请且状态为待处理
    sql = "SELECT * FROM business_applications WHERE id=%s AND user_id=%s AND status='pending' AND deleted=0"
    app = db.get_one(sql, [app_id, user['user_id']])
    
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在或无法修改'})
    
    # 更新
    updates = []
    params = []
    for field in ['title', 'content', 'images']:
        if field in data:
            updates.append(f"{field}=%s")
            params.append(data[field])
    
    if updates:
        params.append(app_id)
        db.execute(f"UPDATE business_applications SET {','.join(updates)} WHERE id=%s", params)
    
    return jsonify({'success': True, 'msg': '修改成功'})

# ============ 订单 API ============

@app.route('/api/user/orders', methods=['GET'])
@require_login
def get_user_orders(user):
    """获取我的订单"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    status = request.args.get('status')
    
    where = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    
    if status:
        where += " AND status=%s"
        params.append(status)
    
    total = db.get_total(f"SELECT COUNT(*) FROM business_orders WHERE {where}", params)
    
    offset = (page - 1) * page_size
    sql = f"SELECT * FROM business_orders WHERE {where} ORDER BY created_time DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    orders = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {
        'items': orders,
        'total': total,
        'page': page,
        'page_size': page_size
    }})

@app.route('/api/user/orders', methods=['POST'])
@require_login
def create_order(user):
    """创建订单"""
    data = request.get_json() or {}
    
    shop_id = data.get('shop_id')
    items = data.get('items', [])
    
    if not shop_id or not items:
        return jsonify({'success': False, 'msg': '参数不完整'})
    
    order_no = utils.generate_no('ORD')
    total_amount = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
    
    sql = """INSERT INTO business_orders 
        (order_no, user_id, user_name, shop_id, total_amount, status, pay_status)
        VALUES (%s, %s, %s, %s, %s, 'pending', 'unpaid')"""
    
    order_id = db.execute(sql, [order_no, user['user_id'], user['user_name'], shop_id, total_amount])
    
    # 插入订单项
    for item in items:
        item_sql = """INSERT INTO business_order_items 
            (order_id, product_id, product_name, price, quantity)
            VALUES (%s, %s, %s, %s, %s)"""
        db.execute(item_sql, [order_id, item.get('product_id'), item.get('product_name'), item.get('price'), item.get('quantity', 1)])
    
    return jsonify({'success': True, 'msg': '订单创建成功', 'data': {'order_no': order_no, 'order_id': order_id}})

@app.route('/api/user/orders/<order_id>/pay', methods=['POST'])
@require_login
def pay_order(user, order_id):
    """支付订单"""
    sql = "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND status='pending' AND deleted=0"
    order = db.get_one(sql, [order_id, user['user_id']])
    
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在或状态异常'})
    
    # 模拟支付
    db.execute("UPDATE business_orders SET status='paid', pay_status='paid', pay_time=NOW() WHERE id=%s", [order_id])
    
    return jsonify({'success': True, 'msg': '支付成功'})

# ============ 预约 API ============

@app.route('/api/user/bookings', methods=['GET'])
@require_login
def get_user_bookings(user):
    """获取我的预约"""
    sql = "SELECT * FROM business_venue_bookings WHERE user_id=%s AND deleted=0 ORDER BY booking_time DESC"
    bookings = db.get_all(sql, [user['user_id']])
    return jsonify({'success': True, 'data': bookings})

# ============ 门店/商品 API ============

@app.route('/api/shops', methods=['GET'])
def get_shops():
    """获取门店列表"""
    shop_type = request.args.get('type')
    if shop_type:
        shops = db.get_all("SELECT * FROM business_shops WHERE shop_type=%s AND status='open' AND deleted=0", [shop_type])
    else:
        shops = db.get_all("SELECT * FROM business_shops WHERE status='open' AND deleted=0")
    return jsonify({'success': True, 'data': shops})

@app.route('/api/products', methods=['GET'])
def get_products():
    """获取商品列表"""
    shop_id = request.args.get('shop_id')
    if shop_id:
        products = db.get_all("SELECT * FROM business_products WHERE shop_id=%s AND status='available' AND deleted=0", [shop_id])
    else:
        products = db.get_all("SELECT * FROM business_products WHERE status='available' AND deleted=0")
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
    print(f"用户端 H5 服务启动在端口 {config.PORTS['user']}")
    app.run(host='0.0.0.0', port=config.PORTS['user'], debug=False)
