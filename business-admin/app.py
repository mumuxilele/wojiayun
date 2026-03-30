#!/usr/bin/env python3
"""
社区商业 - 管理端 Web 服务
端口: 22313
功能: 场地管理(CRUD+图片+介绍+规则+收费)、预约时段管理、账单确认
数据隔离: 所有查询/保存都基于 ec_id 和 project_id
"""
from flask import Flask, g, request, jsonify, send_from_directory
from flask_cors import CORS
import sys, os, time, json, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import config, db, auth, utils

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ============ 管理员认证 ============

def get_current_admin():
    """获取当前管理员信息，包含 ec_id 和 project_id"""
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_user(token, isdev) if token else None

def get_data_scope():
    """获取当前用户的数据范围（ec_id, project_id）"""
    user = g.get('admin_user') or get_current_admin()
    if not user:
        return None, None
    return user.get('ec_id'), user.get('project_id')

def add_scope_filter(where, params, table_alias=''):
    """添加数据范围过滤条件"""
    ec_id, project_id = get_data_scope()
    prefix = table_alias + '.' if table_alias else ''
    if ec_id:
        where += f" AND {prefix}ec_id=%s"
        params.append(ec_id)
    if project_id:
        where += f" AND {prefix}project_id=%s"
        params.append(project_id)
    return where, params

def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_admin()
        if not user:
            return jsonify({'success': False, 'msg': '请先登录'})
        g.admin_user = user
        return f(user, *args, **kwargs)
    return decorated

# 认证钩子 - 在每个请求前检查登录状态
@app.before_request
def check_admin():
    # 排除不需要认证的路由
    exempt = ['/health', '/debugtest', '/api/admin/test', '/', '/index.html']
    if request.path in exempt or request.path.endswith('.html') or request.path.endswith('.css') or request.path.endswith('.js') or request.path == '/':
        return None
    # 验证 token
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    g.admin_user = user
    return None

@app.after_request
def add_headers(response):
    response.headers['X-Response-Time'] = str(int(time.time() * 1000))
    return response

# ============ 用户信息 API ============

@app.route('/api/admin/userinfo', methods=['GET'])
def get_admin_userinfo():
    """获取当前管理员信息"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    return jsonify({
        'success': True, 
        'data': {
            'user_id': user.get('user_id'),
            'user_name': user.get('user_name'),
            'phone': user.get('phone'),
            'ec_id': user.get('ec_id'),
            'project_id': user.get('project_id'),
            'is_staff': user.get('is_staff')
        }
    })

# ============ 统计概览 ============

@app.route('/api/admin/statistics', methods=['GET'])
def admin_statistics():
    """管理后台统计数据 - 按项目/企业过滤"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    # 构建过滤条件
    scope_filter = "deleted=0"
    params = []
    if ec_id:
        scope_filter += " AND ec_id=%s"
        params.append(ec_id)
    if project_id:
        scope_filter += " AND project_id=%s"
        params.append(project_id)
    
    today_orders = db.get_total(f"SELECT COUNT(*) FROM business_orders WHERE DATE(created_at)=CURDATE() AND {scope_filter}", params.copy())
    today_apps = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE DATE(created_at)=CURDATE() AND {scope_filter}", params.copy())
    total_orders = db.get_total(f"SELECT COUNT(*) FROM business_orders WHERE {scope_filter}", params.copy())
    total_apps = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {scope_filter}", params.copy())
    pending_apps = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE status='pending' AND {scope_filter}", params.copy())
    income = db.get_one(f"SELECT COALESCE(SUM(actual_amount),0) as total FROM business_orders WHERE {scope_filter} AND pay_status='paid'", params.copy())
    today_income = db.get_one(f"SELECT COALESCE(SUM(actual_amount),0) as total FROM business_orders WHERE DATE(created_at)=CURDATE() AND {scope_filter} AND pay_status='paid'", params.copy())
    
    return jsonify({'success': True, 'data': {
        'today_orders': today_orders, 
        'today_applications': today_apps,
        'total_orders': total_orders, 
        'total_applications': total_apps,
        'pending_applications': pending_apps,
        'total_income': float(income['total']) if income else 0,
        'today_income': float(today_income['total']) if today_income else 0,
    }})

# ============ 申请单管理 ============

@app.route('/api/admin/applications', methods=['GET'])
def admin_list_applications():
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    keyword = request.args.get('keyword', '')
    app_type = request.args.get('app_type', '')
    
    where = "deleted=0"
    params = []
    if status:
        where += " AND status=%s"
        params.append(status)
    if app_type:
        where += " AND app_type=%s"
        params.append(app_type)
    if keyword:
        where += " AND (title LIKE %s OR user_name LIKE %s OR app_no LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw, kw])
    where, params = add_scope_filter(where, params)
    
    total = db.get_total("SELECT COUNT(*) FROM business_applications WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id,app_no,app_type,title,content,user_name,user_phone,status,priority,created_at,updated_at "
        "FROM business_applications WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/admin/applications/<app_id>', methods=['GET'])
def admin_get_application(app_id):
    """获取申请单详情"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "id=%s AND deleted=0"
    params = [app_id]
    where, params = add_scope_filter(where, params)
    item = db.get_one("SELECT * FROM business_applications WHERE " + where, params)
    if not item:
        return jsonify({'success': False, 'msg': '申请单不存在'})
    return jsonify({'success': True, 'data': item})

@app.route('/api/admin/applications/<app_id>', methods=['PUT'])
def admin_update_application(app_id):
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}
    new_status = data.get('status')
    result = data.get('result', '')
    if new_status:
        db.execute("UPDATE business_applications SET status=%s, result=%s, updated_at=NOW() WHERE id=%s",
                   [new_status, result, app_id])
    return jsonify({'success': True, 'msg': '更新成功'})

@app.route('/api/admin/applications/<app_id>', methods=['DELETE'])
def admin_delete_application(app_id):
    """软删除申请单"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    db.execute("UPDATE business_applications SET deleted=1 WHERE id=%s", [app_id])
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 订单管理 ============

@app.route('/api/admin/orders', methods=['GET'])
def admin_list_orders():
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    pay_status = request.args.get('pay_status')
    keyword = request.args.get('keyword', '')
    
    where = "deleted=0"
    params = []
    if status:
        where += " AND order_status=%s"
        params.append(status)
    if pay_status:
        where += " AND pay_status=%s"
        params.append(pay_status)
    if keyword:
        where += " AND (order_no LIKE %s OR user_name LIKE %s OR user_phone LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw, kw])
    where, params = add_scope_filter(where, params)
    
    total = db.get_total("SELECT COUNT(*) FROM business_orders WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id,order_no,order_type,user_name,user_phone,total_amount,actual_amount,order_status,pay_status,created_at "
        "FROM business_orders WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/admin/orders/<order_id>', methods=['GET'])
def admin_get_order(order_id):
    """获取订单详情"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "id=%s AND deleted=0"
    params = [order_id]
    where, params = add_scope_filter(where, params)
    item = db.get_one("SELECT * FROM business_orders WHERE " + where, params)
    if not item:
        return jsonify({'success': False, 'msg': '订单不存在'})
    return jsonify({'success': True, 'data': item})

@app.route('/api/admin/orders/<order_id>', methods=['PUT'])
def admin_update_order(order_id):
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}
    status = data.get('order_status')
    if status:
        db.execute("UPDATE business_orders SET order_status=%s, updated_at=NOW() WHERE id=%s", [status, order_id])
    return jsonify({'success': True, 'msg': '更新成功'})

# ============ 门店管理 ============

@app.route('/api/admin/shops', methods=['GET'])
def admin_list_shops():
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 200)), 200)
    keyword = request.args.get('keyword', '')
    status = request.args.get('status', '')
    
    where = "deleted=0"
    params = []
    if keyword:
        where += " AND (shop_name LIKE %s OR address LIKE %s OR shop_code LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw, kw])
    if status:
        where += " AND status=%s"
        params.append(status)
    where, params = add_scope_filter(where, params)
    
    total = db.get_total("SELECT COUNT(*) FROM business_shops WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id,shop_name,shop_type,shop_code,address,phone,description,business_hours,status,created_at "
        "FROM business_shops WHERE " + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/admin/shops/<shop_id>', methods=['GET'])
def admin_get_shop(shop_id):
    """获取单个门店详情"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "id=%s AND deleted=0"
    params = [shop_id]
    where, params = add_scope_filter(where, params)
    shop = db.get_one("SELECT * FROM business_shops WHERE " + where, params)
    if not shop:
        return jsonify({'success': False, 'msg': '门店不存在'})
    return jsonify({'success': True, 'data': shop})

@app.route('/api/admin/shops', methods=['POST'])
@require_admin
def admin_create_shop(user):
    data = request.get_json() or {}
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    db.execute(
        "INSERT INTO business_shops (shop_name,shop_type,shop_code,address,phone,description,status,ec_id,project_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,'open',%s,%s)",
        [data.get('shop_name',''), data.get('shop_type',''), data.get('shop_code',''),
         data.get('address',''), data.get('phone',''), data.get('description',''), ec_id, project_id]
    )
    return jsonify({'success': True, 'msg': '创建成功'})

@app.route('/api/admin/shops/<shop_id>', methods=['PUT'])
def admin_update_shop(shop_id):
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}
    allowed_fields = ('shop_name', 'shop_type', 'shop_code', 'address', 'phone', 'description', 'status', 'business_hours')
    updates = []
    params = []
    for f in allowed_fields:
        if f in data:
            updates.append(f + "=%s")
            params.append(data[f])
    if not updates:
        return jsonify({'success': False, 'msg': '没有要更新的字段'})
    updates.append("updated_at=NOW()")
    params.append(shop_id)
    db.execute("UPDATE business_shops SET " + ", ".join(updates) + " WHERE id=%s", params)
    return jsonify({'success': True, 'msg': '更新成功'})

@app.route('/api/admin/shops/<shop_id>', methods=['DELETE'])
def admin_delete_shop(shop_id):
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    db.execute("UPDATE business_shops SET deleted=1 WHERE id=%s", [shop_id])
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 用户管理 ============

@app.route('/api/admin/users', methods=['GET'])
def admin_list_users():
    """用户/会员列表 - 从 business_members 表查询"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    keyword = request.args.get('keyword', '')
    level = request.args.get('level', '')
    
    where = "1=1"
    params = []
    if keyword:
        where += " AND (user_name LIKE %s OR phone LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw])
    if level:
        where += " AND member_level=%s"
        params.append(level)
    where, params = add_scope_filter(where, params)
    
    total = db.get_total("SELECT COUNT(*) FROM business_members WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id, user_id, user_name, phone, member_level, points, total_points, balance, created_at "
        "FROM business_members WHERE " + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

# ============ 场地管理 API ============

@app.route('/api/admin/venues', methods=['GET'])
def list_venues():
    """场地列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    keyword = request.args.get('keyword', '')
    status = request.args.get('status')
    
    where = "deleted=0"
    params = []
    if keyword:
        where += " AND (venue_name LIKE %s OR venue_code LIKE %s)"
        params.extend(['%' + keyword + '%', '%' + keyword + '%'])
    if status:
        where += " AND status=%s"
        params.append(status)
    where, params = add_scope_filter(where, params)
    
    total = db.get_total("SELECT COUNT(*) FROM business_venues WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id,venue_name,venue_code,venue_type,description,rules,capacity,price,images,facilities,open_hours,status,created_at "
        "FROM business_venues WHERE " + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/admin/venues', methods=['POST'])
@require_admin
def create_venue(user):
    """创建场地"""
    data = request.get_json() or {}
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    venue_name = data.get('venue_name', '').strip()
    venue_type = data.get('venue_type', 'other')
    venue_code = data.get('venue_code', '').strip()
    description = data.get('description', '')
    rules = data.get('rules', '')
    capacity = int(data.get('capacity', 0) or 0)
    price = float(data.get('price', 0) or 0)
    images = json.dumps(data.get('images', []))
    facilities = json.dumps(data.get('facilities', []))
    open_hours = json.dumps(data.get('open_hours', {}))
    status = data.get('status', 'open')
    
    if not venue_name:
        return jsonify({'success': False, 'msg': '场地名称不能为空'})
    
    db.execute(
        "INSERT INTO business_venues (venue_name,venue_code,venue_type,description,rules,capacity,price,images,facilities,open_hours,status,ec_id,project_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        [venue_name, venue_code, venue_type, description, rules, capacity, price, images, facilities, open_hours, status, ec_id, project_id]
    )
    return jsonify({'success': True, 'msg': '创建成功'})

@app.route('/api/admin/venues/<venue_id>', methods=['GET'])
def get_venue(venue_id):
    """获取场地详情"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    where = "id=%s AND deleted=0"
    params = [venue_id]
    where, params = add_scope_filter(where, params)
    
    venue = db.get_one("SELECT * FROM business_venues WHERE " + where, params)
    if not venue:
        return jsonify({'success': False, 'msg': '场地不存在'})
    return jsonify({'success': True, 'data': venue})

@app.route('/api/admin/venues/<venue_id>', methods=['PUT'])
def update_venue(venue_id):
    data = request.get_json() or {}
    updates = []
    fields = ['venue_name','venue_code','venue_type','description','rules','capacity','price','images','facilities','open_hours','status']
    params = []
    
    # 检查venue_code唯一性
    if 'venue_code' in data:
        venue_code = data['venue_code']
        existing = db.get_one("SELECT id FROM business_venues WHERE venue_code=%s AND id!=%s AND deleted=0", [venue_code, venue_id])
        if existing:
            return jsonify({'success': False, 'msg': '场馆编号已存在，请使用不同的编号'})
    
    for f in fields:
        if f in data:
            val = data[f]
            if f in ('images','facilities','open_hours') and isinstance(val, (list, dict)):
                val = json.dumps(val)
            updates.append(f + "=%s")
            params.append(val)
    
    if not updates:
        return jsonify({'success': False, 'msg': '没有更新字段'})
    
    params.append(venue_id)
    db.execute("UPDATE business_venues SET " + ",".join(updates) + " WHERE id=%s", params)
    return jsonify({'success': True, 'msg': '更新成功'})

@app.route('/api/admin/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    """删除场地"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    db.execute("UPDATE business_venues SET deleted=1 WHERE id=%s", [venue_id])
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 预约时段管理 API ============

@app.route('/api/admin/venue-bookings', methods=['GET'])
def list_venue_bookings():
    """所有场地预约列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    venue_id = request.args.get('venue_id')
    status = request.args.get('status')
    date = request.args.get('date')
    keyword = request.args.get('keyword', '')
    
    where = "vb.deleted=0"
    params = []
    if venue_id:
        where += " AND vb.venue_id=%s"
        params.append(venue_id)
    if status:
        where += " AND vb.status=%s"
        params.append(status)
    if date:
        where += " AND vb.book_date=%s"
        params.append(date)
    if keyword:
        where += " AND (vb.user_name LIKE %s OR vb.verify_code LIKE %s)"
        params.extend(['%' + keyword + '%', '%' + keyword + '%'])
    where, params = add_scope_filter(where, params, 'vb')
    
    total = db.get_total("SELECT COUNT(*) FROM business_venue_bookings vb WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT vb.id, vb.venue_id, vb.user_id, vb.user_name, vb.user_phone, "
        "CAST(vb.book_date AS CHAR) as book_date, "
        "CAST(vb.start_time AS CHAR) as start_time, CAST(vb.end_time AS CHAR) as end_time, "
        "CAST(vb.total_hours AS CHAR) as total_hours, vb.total_price, vb.status, vb.pay_status, vb.verify_code, vb.created_at, "
        "v.venue_name, v.venue_type "
        "FROM business_venue_bookings vb "
        "LEFT JOIN business_venues v ON vb.venue_id=v.id "
        "WHERE " + where + " ORDER BY vb.book_date DESC, vb.start_time ASC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/admin/venue-bookings/<booking_id>', methods=['PUT'])
def update_venue_booking(booking_id):
    """更新预约状态（确认/取消）"""
    data = request.get_json() or {}
    new_status = data.get('status')
    if new_status not in ('pending','confirmed','completed','cancelled'):
        return jsonify({'success': False, 'msg': '状态值无效'})
    db.execute("UPDATE business_venue_bookings SET status=%s WHERE id=%s", [new_status, booking_id])
    return jsonify({'success': True, 'msg': '状态更新成功'})

@app.route('/api/admin/venue-bookings/<booking_id>/pay', methods=['POST'])
def confirm_booking_pay(booking_id):
    """确认预约缴费"""
    data = request.get_json() or {}
    pay_status = data.get('pay_status', 'paid')
    db.execute(
        "UPDATE business_venue_bookings SET pay_status=%s, status='confirmed' WHERE id=%s",
        [pay_status, booking_id]
    )
    return jsonify({'success': True, 'msg': '缴费确认成功'})

@app.route('/api/admin/venue-bookings/<booking_id>/complete', methods=['POST'])
def complete_booking(booking_id):
    """完成预约（confirmed → completed）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    booking = db.get_one("SELECT id, status FROM business_venue_bookings WHERE id=%s AND deleted=0", [booking_id])
    if not booking:
        return jsonify({'success': False, 'msg': '预约不存在'})
    if booking.get('status') != 'confirmed':
        return jsonify({'success': False, 'msg': '只有已确认的预约才能标记完成'})
    db.execute("UPDATE business_venue_bookings SET status='completed', updated_at=NOW() WHERE id=%s", [booking_id])
    return jsonify({'success': True, 'msg': '预约已完成'})

@app.route('/api/admin/venue-bookings/verify', methods=['POST'])
def verify_booking_code():
    """核销码验证 - 根据核销码查找预约并完成核销"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}
    verify_code = (data.get('verify_code') or '').strip().upper()
    if not verify_code:
        return jsonify({'success': False, 'msg': '请输入核销码'})
    where = "verify_code=%s AND deleted=0"
    params = [verify_code]
    where, params = add_scope_filter(where, params, '')
    booking = db.get_one(
        "SELECT vb.*, v.venue_name FROM business_venue_bookings vb "
        "LEFT JOIN business_venues v ON vb.venue_id=v.id "
        "WHERE vb." + where,
        params
    )
    if not booking:
        return jsonify({'success': False, 'msg': '核销码无效或不属于本项目'})
    if booking.get('status') == 'completed':
        return jsonify({'success': False, 'msg': '该预约已核销', 'data': booking})
    if booking.get('status') == 'cancelled':
        return jsonify({'success': False, 'msg': '该预约已取消', 'data': booking})
    if booking.get('status') == 'pending':
        return jsonify({'success': False, 'msg': '该预约尚未确认，无法核销', 'data': booking})
    # confirmed 状态可以核销
    db.execute(
        "UPDATE business_venue_bookings SET status='completed', updated_at=NOW() WHERE id=%s",
        [booking['id']]
    )
    booking['status'] = 'completed'
    return jsonify({'success': True, 'msg': '核销成功', 'data': booking})

# ============ 场地统计 ============

@app.route('/api/admin/venue-statistics', methods=['GET'])
def venue_statistics():
    """场地统计数据"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    venue_id = request.args.get('venue_id')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    where = "vb.deleted=0"
    params = []
    if venue_id:
        where += " AND vb.venue_id=%s"
        params.append(venue_id)
    if date_from:
        where += " AND vb.book_date>=%s"
        params.append(date_from)
    if date_to:
        where += " AND vb.book_date<=%s"
        params.append(date_to)
    where, params = add_scope_filter(where, params, 'vb')
    
    # 预约数
    total_bookings = db.get_total("SELECT COUNT(*) FROM business_venue_bookings vb WHERE " + where, params)
    # 收入
    income = db.get_one(
        "SELECT COALESCE(SUM(total_price),0) as total FROM business_venue_bookings vb WHERE " + where + " AND vb.pay_status='paid'",
        params
    )
    # 待确认
    pending = db.get_total("SELECT COUNT(*) FROM business_venue_bookings vb WHERE " + where + " AND vb.status='pending'", params)
    # 已完成
    completed = db.get_total("SELECT COUNT(*) FROM business_venue_bookings vb WHERE " + where + " AND vb.status='completed'", params)
    
    return jsonify({'success': True, 'data': {
        'total_bookings': total_bookings,
        'total_income': float(income['total']) if income else 0,
        'pending_bookings': pending,
        'completed_bookings': completed
    }})

# ============ 积分管理 API ============

@app.route('/api/admin/points/members', methods=['GET'])
def admin_points_members():
    """会员积分列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    keyword = request.args.get('keyword', '')
    level = request.args.get('level')
    
    where = "1=1"
    params = []
    if keyword:
        where += " AND user_name LIKE %s"
        params.append('%' + keyword + '%')
    if level:
        where += " AND member_level=%s"
        params.append(level)
    where, params = add_scope_filter(where, params)
    
    total = db.get_total("SELECT COUNT(*) FROM business_members WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id, user_id, user_name, phone, member_level, points, total_points "
        "FROM business_members WHERE " + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/admin/points/logs', methods=['GET'])
def admin_points_logs():
    """积分记录列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    user_id = request.args.get('user_id')
    log_type = request.args.get('type')
    keyword = request.args.get('keyword', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    where = "1=1"
    params = []
    if user_id:
        where += " AND user_id=%s"
        params.append(user_id)
    if log_type:
        where += " AND log_type=%s"
        params.append(log_type)
    if keyword:
        where += " AND (user_name LIKE %s OR phone LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw])
    if date_from:
        where += " AND DATE(created_at)>=%s"
        params.append(date_from)
    if date_to:
        where += " AND DATE(created_at)<=%s"
        params.append(date_to)
    where, params = add_scope_filter(where, params)
    
    total = db.get_total("SELECT COUNT(*) FROM business_points_log WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id, user_id, user_name, log_type as type, points, balance_after, description, created_at "
        "FROM business_points_log WHERE " + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/admin/points/adjust', methods=['POST'])
@require_admin
def admin_points_adjust(user):
    """管理员调整会员积分"""
    data = request.get_json() or {}
    target_user_id = data.get('user_id')
    points = int(data.get('points', 0))
    adjust_type = data.get('type', 'add')  # add / reduce
    description = data.get('description', '管理员调整')
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    if not target_user_id:
        return jsonify({'success': False, 'msg': '用户ID不能为空'})
    if points <= 0:
        return jsonify({'success': False, 'msg': '积分数量必须大于0'})
    
    # 获取会员信息（带数据范围过滤）
    where = "user_id=%s"
    params = [target_user_id]
    where, params = add_scope_filter(where, params)
    
    member = db.get_one("SELECT * FROM business_members WHERE " + where, params)
    if not member:
        return jsonify({'success': False, 'msg': '会员不存在或无权限'})
    
    # 计算积分变动（points 字段存当前余额）
    current = member.get('points', 0) or 0
    delta = points if adjust_type != 'reduce' else -points
    
    new_balance = current + delta
    if new_balance < 0:
        return jsonify({'success': False, 'msg': '积分余额不足，当前余额：' + str(current)})
    
    # 更新会员积分
    db.execute(
        "UPDATE business_members SET points=%s, total_points=total_points+%s WHERE user_id=%s",
        [new_balance, delta if delta > 0 else 0, target_user_id]
    )
    
    # 记录日志（带 ec_id 和 project_id）
    db.execute(
        "INSERT INTO business_points_log (user_id, user_name, log_type, points, balance_after, description, ec_id, project_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        [target_user_id, member['user_name'], 'admin', delta, new_balance, description, ec_id, project_id]
    )
    
    return jsonify({'success': True, 'msg': '积分调整成功', 'data': {'new_balance': new_balance}})

@app.route('/api/admin/points/stats', methods=['GET'])
def admin_points_stats():
    """积分统计概览"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    where = "1=1"
    params = []
    where, params = add_scope_filter(where, params)
    
    # 总会员数
    total_members = db.get_total("SELECT COUNT(*) FROM business_members WHERE " + where, params)
    # 总积分（字段名为 points，不是 current_points）
    total_points = db.get_one("SELECT COALESCE(SUM(points),0) as total FROM business_members WHERE " + where, params)
    # 今日积分变动
    today_where = where + " AND DATE(created_at)=CURDATE()"
    today_points = db.get_one(
        "SELECT COALESCE(SUM(ABS(points)),0) as total FROM business_points_log WHERE " + today_where, params
    )
    # 本月积分变动
    month_where = where + " AND YEAR(created_at)=YEAR(NOW()) AND MONTH(created_at)=MONTH(NOW())"
    month_points = db.get_one(
        "SELECT COALESCE(SUM(ABS(points)),0) as total FROM business_points_log WHERE " + month_where, params
    )
    
    return jsonify({'success': True, 'data': {
        'total_members': total_members,
        'total_points': int(total_points['total']) if total_points else 0,
        'today_points': int(today_points['total']) if today_points else 0,
        'month_points': int(month_points['total']) if month_points else 0
    }})

# ============ 申请单状态聚合统计 ============

@app.route('/api/admin/applications/stats/by-status', methods=['GET'])
def admin_applications_stats():
    """申请单各状态数量统计（一次性返回，避免前端4次请求）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "deleted=0"
    params = []
    where, params = add_scope_filter(where, params)
    rows = db.get_all(
        "SELECT status, COUNT(*) as cnt FROM business_applications WHERE " + where + " GROUP BY status",
        params
    )
    result = {r['status']: r['cnt'] for r in (rows or [])}
    return jsonify({'success': True, 'data': result})

@app.route('/api/admin/applications/stats/by-type', methods=['GET'])
def admin_applications_by_type():
    """申请单各类型数量统计"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "deleted=0"
    params = []
    where, params = add_scope_filter(where, params)
    rows = db.get_all(
        "SELECT app_type, COUNT(*) as cnt FROM business_applications WHERE " + where + " GROUP BY app_type",
        params
    )
    result = {r['app_type']: r['cnt'] for r in (rows or [])}
    return jsonify({'success': True, 'data': result})

# ============ 订单趋势接口（近N日） ============

@app.route('/api/admin/orders/trend', methods=['GET'])
def admin_orders_trend():
    """近N天订单趋势（订单数+收入）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    days = min(int(request.args.get('days', 7)), 30)
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    scope = "deleted=0"
    params = []
    if ec_id:
        scope += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        scope += " AND project_id=%s"; params.append(project_id)
    rows = db.get_all(
        f"SELECT DATE(created_at) as d, COUNT(*) as order_cnt, "
        f"COALESCE(SUM(CASE WHEN pay_status='paid' THEN actual_amount ELSE 0 END),0) as income "
        f"FROM business_orders WHERE {scope} AND created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY) "
        f"GROUP BY DATE(created_at) ORDER BY d ASC",
        params + [days]
    )
    # 填充缺失日期
    from datetime import date, timedelta
    date_map = {}
    for r in (rows or []):
        k = str(r['d']) if r.get('d') else ''
        if k:
            date_map[k] = {'order_cnt': r['order_cnt'], 'income': float(r['income'] or 0)}
    result = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).strftime('%Y-%m-%d')
        result.append({'date': d, 'order_cnt': date_map.get(d, {}).get('order_cnt', 0), 'income': date_map.get(d, {}).get('income', 0)})
    return jsonify({'success': True, 'data': result})

# ============ 申请单趋势接口（近N日） ============

@app.route('/api/admin/applications/trend', methods=['GET'])
def admin_applications_trend():
    """近N天申请单趋势"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    days = min(int(request.args.get('days', 7)), 30)
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    scope = "deleted=0"
    params = []
    if ec_id:
        scope += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        scope += " AND project_id=%s"; params.append(project_id)
    rows = db.get_all(
        f"SELECT DATE(created_at) as d, COUNT(*) as app_cnt "
        f"FROM business_applications WHERE {scope} AND created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY) "
        f"GROUP BY DATE(created_at) ORDER BY d ASC",
        params + [days]
    )
    from datetime import date, timedelta
    date_map = {str(r['d']): r['app_cnt'] for r in (rows or []) if r.get('d')}
    result = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).strftime('%Y-%m-%d')
        result.append({'date': d, 'app_cnt': date_map.get(d, 0)})
    return jsonify({'success': True, 'data': result})

# ============ 批量处理申请单 ============

@app.route('/api/admin/applications/batch', methods=['POST'])
def admin_batch_applications():
    """批量操作申请单（批量改状态/批量删除）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}
    action = data.get('action')  # 'delete' or 'status'
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'success': False, 'msg': '请选择要操作的申请单'})
    if len(ids) > 50:
        return jsonify({'success': False, 'msg': '单次批量操作不超过50条'})
    placeholders = ','.join(['%s'] * len(ids))
    if action == 'delete':
        db.execute(f"UPDATE business_applications SET deleted=1 WHERE id IN ({placeholders})", ids)
        return jsonify({'success': True, 'msg': f'已删除 {len(ids)} 条申请单'})
    elif action == 'status':
        new_status = data.get('status')
        if new_status not in ('processing', 'completed', 'rejected', 'pending'):
            return jsonify({'success': False, 'msg': '状态值无效'})
        db.execute(f"UPDATE business_applications SET status=%s, updated_at=NOW() WHERE id IN ({placeholders})", [new_status] + ids)
        return jsonify({'success': True, 'msg': f'已更新 {len(ids)} 条申请单状态'})
    return jsonify({'success': False, 'msg': '不支持的操作类型'})

# ============ 用户积分详情（管理端查询某用户） ============

@app.route('/api/admin/users/<user_id>/points', methods=['GET'])
def admin_user_points(user_id):
    """查询某用户积分详情"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    member = db.get_one("SELECT user_id, user_name, phone, points, total_points, balance, member_level FROM business_members WHERE user_id=%s", [user_id])
    if not member:
        return jsonify({'success': False, 'msg': '用户不存在'})
    logs = db.get_all(
        "SELECT log_type as type, points, balance_after, description, created_at "
        "FROM business_points_log WHERE user_id=%s ORDER BY id DESC LIMIT 20",
        [user_id]
    )
    return jsonify({'success': True, 'data': {'member': member, 'recent_logs': logs or []}})

# ============ CSV导出 ============

@app.route('/api/admin/export/applications', methods=['GET'])
def export_applications():
    """导出申请单CSV"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "deleted=0"
    params = []
    status = request.args.get('status')
    app_type = request.args.get('app_type')
    if status:
        where += " AND status=%s"; params.append(status)
    if app_type:
        where += " AND app_type=%s"; params.append(app_type)
    where, params = add_scope_filter(where, params)
    items = db.get_all(
        "SELECT app_no,app_type,title,user_name,user_phone,status,priority,created_at,updated_at "
        "FROM business_applications WHERE " + where + " ORDER BY created_at DESC LIMIT 1000",
        params
    )
    import io, csv
    from flask import Response
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['申请单号', '类型', '标题', '申请人', '联系电话', '状态', '优先级', '提交时间', '更新时间'])
    type_map = {'repair': '报修', 'booking': '预约', 'complaint': '投诉', 'consult': '咨询', 'other': '其他'}
    status_map = {'pending': '待处理', 'processing': '处理中', 'completed': '已完成', 'rejected': '已拒绝', 'cancelled': '已撤销'}
    for item in (items or []):
        writer.writerow([
            item.get('app_no', ''), type_map.get(item.get('app_type', ''), item.get('app_type', '')),
            item.get('title', ''), item.get('user_name', ''), item.get('user_phone', ''),
            status_map.get(item.get('status', ''), item.get('status', '')),
            item.get('priority', 0), item.get('created_at', ''), item.get('updated_at', '')
        ])
    output.seek(0)
    return Response(
        '\ufeff' + output.getvalue(),  # BOM for Excel
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=applications.csv'}
    )

@app.route('/api/admin/export/orders', methods=['GET'])
def export_orders():
    """导出订单CSV"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "deleted=0"
    params = []
    where, params = add_scope_filter(where, params)
    items = db.get_all(
        "SELECT order_no,order_type,user_name,user_phone,total_amount,actual_amount,order_status,pay_status,created_at "
        "FROM business_orders WHERE " + where + " ORDER BY created_at DESC LIMIT 1000",
        params
    )
    import io, csv
    from flask import Response
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['订单号', '类型', '用户', '电话', '总金额', '实付金额', '订单状态', '支付状态', '创建时间'])
    for item in (items or []):
        writer.writerow([
            item.get('order_no', ''), item.get('order_type', ''), item.get('user_name', ''),
            item.get('user_phone', ''), item.get('total_amount', 0), item.get('actual_amount', 0),
            item.get('order_status', ''), item.get('pay_status', ''), item.get('created_at', '')
        ])
    output.seek(0)
    return Response(
        '\ufeff' + output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=orders.csv'}
    )

# ============ 会员等级分布统计 ============

@app.route('/api/admin/members/stats/by-level', methods=['GET'])
def admin_members_by_level():
    """会员等级分布统计"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "1=1"
    params = []
    where, params = add_scope_filter(where, params)
    rows = db.get_all(
        "SELECT member_level, COUNT(*) as cnt FROM business_members WHERE " + where + " GROUP BY member_level",
        params
    )
    result = {r['member_level']: r['cnt'] for r in (rows or [])}
    return jsonify({'success': True, 'data': result})

# ============ 场地热度排行榜 ============

@app.route('/api/admin/venues/stats/hot', methods=['GET'])
def admin_venues_hot():
    """场地热度排行：按预约次数和收入排序"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    scope = "vb.deleted=0"
    params = []
    if ec_id:
        scope += " AND vb.ec_id=%s"
        params.append(ec_id)
    if project_id:
        scope += " AND vb.project_id=%s"
        params.append(project_id)
    rows = db.get_all(
        "SELECT v.id, v.venue_name, v.venue_type, "
        "COUNT(vb.id) as book_cnt, "
        "COALESCE(SUM(CASE WHEN vb.pay_status='paid' THEN vb.total_price ELSE 0 END), 0) as total_income, "
        "COUNT(CASE WHEN vb.status='completed' THEN 1 END) as completed_cnt "
        "FROM business_venues v "
        "LEFT JOIN business_venue_bookings vb ON v.id=vb.venue_id AND " + scope + " "
        "WHERE v.deleted=0 "
        "GROUP BY v.id, v.venue_name, v.venue_type "
        "ORDER BY book_cnt DESC LIMIT 10",
        params
    )
    return jsonify({'success': True, 'data': rows or []})

# ============ 健康检查 ============

@app.route('/health')
def health():
    return jsonify({'success': True, 'module': 'admin-web', 'status': 'ok', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})

@app.route('/debugtest')
def debugtest():
    return "DEBUG_TEST_OK"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22313, debug=False)
