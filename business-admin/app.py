#!/usr/bin/env python3
"""
社区商业 - 管理端 Web 服务
端口: 22313
功能: 场地管理(CRUD+图片+介绍+规则+收费)、预约时段管理、账单确认
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys, os, time, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import config, db, auth, utils

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

@app.after_request
def add_headers(response):
    response.headers['X-Response-Time'] = str(int(time.time() * 1000))
    return response

# ============ 管理员认证 ============

def get_current_admin():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_user(token, isdev) if token else None

def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_admin()
        if not user:
            return jsonify({'success': False, 'msg': '请先登录'})
        return f(user, *args, **kwargs)
    return decorated

# ============ 场地管理 API ============

@app.route('/api/admin/venues', methods=['GET'])
@require_admin
def list_venues(admin):
    """场地列表"""
    page      = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    keyword   = request.args.get('keyword', '')
    status    = request.args.get('status')
    
    where = "deleted=0"
    params = []
    if keyword:
        where += " AND (venue_name LIKE %s OR venue_code LIKE %s)"
        params.extend(['%' + keyword + '%', '%' + keyword + '%'])
    if status:
        where += " AND status=%s"
        params.append(status)
    
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
def create_venue(admin):
    """创建场地"""
    data = request.get_json() or {}
    venue_name    = data.get('venue_name', '').strip()
    venue_type    = data.get('venue_type', 'other')
    venue_code    = data.get('venue_code', '').strip()
    description   = data.get('description', '')
    rules         = data.get('rules', '')
    capacity      = int(data.get('capacity', 0) or 0)
    price         = float(data.get('price', 0) or 0)
    images        = json.dumps(data.get('images', []))
    facilities    = json.dumps(data.get('facilities', []))
    open_hours    = json.dumps(data.get('open_hours', {}))
    status        = data.get('status', 'open')
    
    if not venue_name:
        return jsonify({'success': False, 'msg': '场地名称不能为空'})
    
    db.execute(
        "INSERT INTO business_venues (venue_name,venue_code,venue_type,description,rules,capacity,price,images,facilities,open_hours,status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        [venue_name, venue_code, venue_type, description, rules, capacity, price, images, facilities, open_hours, status]
    )
    return jsonify({'success': True, 'msg': '创建成功'})

@app.route('/api/admin/venues/<venue_id>', methods=['GET'])
@require_admin
def get_venue(admin, venue_id):
    """获取场地详情"""
    venue = db.get_one("SELECT * FROM business_venues WHERE id=%s AND deleted=0", [venue_id])
    if not venue:
        return jsonify({'success': False, 'msg': '场地不存在'})
    return jsonify({'success': True, 'data': venue})

@app.route('/api/admin/venues/<venue_id>', methods=['PUT'])
@require_admin
def update_venue(admin, venue_id):
    """更新场地"""
    data = request.get_json() or {}
    updates = []
    fields = ['venue_name','venue_code','venue_type','description','rules','capacity','price','images','facilities','open_hours','status']
    params = []
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
@require_admin
def delete_venue(admin, venue_id):
    """删除场地"""
    db.execute("UPDATE business_venues SET deleted=1 WHERE id=%s", [venue_id])
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 预约时段管理 API ============

@app.route('/api/admin/venue-bookings', methods=['GET'])
@require_admin
def list_venue_bookings(admin):
    """所有场地预约列表"""
    page      = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    venue_id  = request.args.get('venue_id')
    status    = request.args.get('status')
    date      = request.args.get('date')
    keyword   = request.args.get('keyword', '')
    
    where = "vb.deleted=0"
    params = []
    if venue_id:
        where += " AND vb.venue_id=%s"; params.append(venue_id)
    if status:
        where += " AND vb.status=%s"; params.append(status)
    if date:
        where += " AND vb.book_date=%s"; params.append(date)
    if keyword:
        where += " AND (vb.user_name LIKE %s OR vb.verify_code LIKE %s)"
        params.extend(['%' + keyword + '%', '%' + keyword + '%'])
    
    total = db.get_total("SELECT COUNT(*) FROM business_venue_bookings vb WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT vb.*, v.venue_name, v.venue_type "
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
@require_admin
def update_venue_booking(admin, booking_id):
    """更新预约状态（确认/取消）"""
    data = request.get_json() or {}
    new_status = data.get('status')
    if new_status not in ('pending','confirmed','completed','cancelled'):
        return jsonify({'success': False, 'msg': '状态值无效'})
    db.execute("UPDATE business_venue_bookings SET status=%s WHERE id=%s", [new_status, booking_id])
    return jsonify({'success': True, 'msg': '状态更新成功'})

@app.route('/api/admin/venue-bookings/<booking_id>/pay', methods=['POST'])
@require_admin
def confirm_booking_pay(admin, booking_id):
    """确认预约缴费"""
    data = request.get_json() or {}
    pay_status = data.get('pay_status', 'paid')
    db.execute(
        "UPDATE business_venue_bookings SET pay_status=%s, status='confirmed' WHERE id=%s",
        [pay_status, booking_id]
    )
    return jsonify({'success': True, 'msg': '缴费确认成功'})

# ============ 场地统计 ============

@app.route('/api/admin/venue-statistics', methods=['GET'])
@require_admin
def venue_statistics(admin):
    """场地统计数据"""
    venue_id = request.args.get('venue_id')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    where = "vb.deleted=0"
    params = []
    if venue_id:
        where += " AND vb.venue_id=%s"; params.append(venue_id)
    if date_from:
        where += " AND vb.book_date>=%s"; params.append(date_from)
    if date_to:
        where += " AND vb.book_date<=%s"; params.append(date_to)
    
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

# ============ 健康检查 ============

@app.route('/health')
def health():
    return jsonify({'success': True, 'module': 'admin-web', 'status': 'ok', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22313, debug=False)
