#!/usr/bin/env python3
"""
社区商业 - 用户端 H5 服务
端口: 22311
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

# ============ 统计 ============

@app.route('/api/user/stats', methods=['GET'])
@require_login
def get_user_stats(user):
    uid = user['user_id']
    pending    = db.get_total("SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='pending'", [uid])
    processing = db.get_total("SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='processing'", [uid])
    completed  = db.get_total("SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='completed'", [uid])
    orders     = db.get_total("SELECT COUNT(*) FROM business_orders WHERE user_id=%s AND deleted=0", [uid])
    bookings   = db.get_total("SELECT COUNT(*) FROM business_venue_bookings WHERE user_id=%s AND deleted=0", [uid])
    return jsonify({'success': True, 'data': {
        'pending': pending, 'processing': processing,
        'completed': completed, 'orders': orders, 'bookings': bookings
    }})

# ============ 申请单 ============

@app.route('/api/user/applications', methods=['GET'])
@require_login
def get_user_applications(user):
    page      = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status    = request.args.get('status')
    app_type  = request.args.get('app_type')
    where  = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    if status:
        where += " AND status=%s"; params.append(status)
    if app_type:
        where += " AND app_type=%s"; params.append(app_type)
    total  = db.get_total("SELECT COUNT(*) FROM business_applications WHERE " + where, params)
    offset = (page - 1) * page_size
    items  = db.get_all(
        "SELECT id,app_no,app_type,title,status,priority,created_at,updated_at FROM business_applications WHERE "
        + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/user/applications', methods=['POST'])
@require_login
def create_application(user):
    data     = request.get_json() or {}
    app_type = data.get('app_type')
    title    = data.get('title', '').strip()
    content  = data.get('content', '')
    images   = json.dumps(data.get('images', []))
    priority = int(data.get('priority', 0))
    if not app_type or not title:
        return jsonify({'success': False, 'msg': '请填写必要信息'})
    app_no = utils.generate_no('APP')
    db.execute(
        "INSERT INTO business_applications (app_no,app_type,title,content,user_id,user_name,user_phone,ec_id,project_id,status,images,priority) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s)",
        [app_no, app_type, title, content, user['user_id'], user['user_name'],
         user.get('phone'), user.get('ec_id'), user.get('project_id'), images, priority]
    )
    return jsonify({'success': True, 'msg': '提交成功', 'data': {'app_no': app_no}})

@app.route('/api/user/applications/<app_id>', methods=['GET'])
@require_login
def get_application_detail(user, app_id):
    app = db.get_one(
        "SELECT * FROM business_applications WHERE id=%s AND user_id=%s AND deleted=0",
        [app_id, user['user_id']]
    )
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    return jsonify({'success': True, 'data': app})

# ============ 订单 ============

@app.route('/api/user/orders', methods=['GET'])
@require_login
def get_user_orders(user):
    page      = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status    = request.args.get('status')
    where  = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    if status:
        where += " AND order_status=%s"; params.append(status)
    total  = db.get_total("SELECT COUNT(*) FROM business_orders WHERE " + where, params)
    offset = (page - 1) * page_size
    items  = db.get_all(
        "SELECT id,order_no,order_type,shop_id,total_amount,actual_amount,order_status,pay_status,created_at "
        "FROM business_orders WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/user/orders/<order_id>', methods=['GET'])
@require_login
def get_order_detail(user, order_id):
    order = db.get_one(
        "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
        [order_id, user['user_id']]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    return jsonify({'success': True, 'data': order})

# ============ 场馆预约 ============

@app.route('/api/user/bookings', methods=['GET'])
@require_login
def get_user_bookings(user):
    page      = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status    = request.args.get('status')
    where  = "vb.user_id=%s AND vb.deleted=0"
    params = [user['user_id']]
    if status:
        where += " AND vb.status=%s"; params.append(status)
    total  = db.get_total("SELECT COUNT(*) FROM business_venue_bookings vb WHERE " + where, params)
    offset = (page - 1) * page_size
    # business_venues 字段: venue_name, price (不是 name/price_per_hour)
    items  = db.get_all(
        "SELECT vb.id, vb.venue_id, vb.book_date, vb.start_time, vb.end_time, "
        "vb.total_hours, vb.total_price, vb.status, vb.verify_code, vb.created_at, "
        "v.venue_name, v.venue_type "
        "FROM business_venue_bookings vb "
        "LEFT JOIN business_venues v ON vb.venue_id=v.id "
        "WHERE " + where + " ORDER BY vb.book_date DESC, vb.created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/user/venues', methods=['GET'])
@require_login
def get_venues(user):
    page      = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    venue_type = request.args.get('type')
    # status 字段值是 'open' 不是 'active'
    where  = "deleted=0 AND status='open'"
    params = []
    if venue_type:
        where += " AND venue_type=%s"; params.append(venue_type)
    total  = db.get_total("SELECT COUNT(*) FROM business_venues WHERE " + where, params)
    offset = (page - 1) * page_size
    items  = db.get_all(
        "SELECT id,venue_name,venue_type,price,capacity,images,facilities,open_hours,status "
        "FROM business_venues WHERE " + where + " ORDER BY id ASC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size}})


@app.route('/api/user/venues/<venue_id>', methods=['GET'])
@require_login
def get_venue_detail(user, venue_id):
    """获取场地详情"""
    venue = db.get_one("SELECT * FROM business_venues WHERE id=%s AND deleted=0 AND status='open'", [venue_id])
    if not venue:
        return jsonify({'success': False, 'msg': '场地不存在'})
    return jsonify({'success': True, 'data': venue})


@app.route('/api/user/venues/<venue_id>/booked', methods=['GET'])
@require_login
def get_venue_booked_hours(user, venue_id):
    """获取某场地某日已预约的小时数列表（用于前端禁止重复预约）"""
    date = request.args.get('date')
    if not date:
        return jsonify({'success': True, 'data': {'hours': []}})
    # 查询该日期该场地的所有有效预约
    rows = db.get_all(
        "SELECT start_time, end_time FROM business_venue_bookings "
        "WHERE venue_id=%s AND book_date=%s AND status IN ('pending','confirmed') AND deleted=0",
        [venue_id, date]
    )
    hours = []
    for r in rows or []:
        try:
            st = r['start_time']
            et = r['end_time']
            sh = int(str(st).split(':')[0]) if st else 0
            eh = int(str(et).split(':')[0]) if et else 0
            for h in range(sh, eh):
                if h not in hours:
                    hours.append(h)
        except:
            pass
    return jsonify({'success': True, 'data': {'hours': hours}})

@app.route('/api/user/venues/<venue_id>/book', methods=['POST'])
@require_login
def book_venue(user, venue_id):
    data       = request.get_json() or {}
    book_date  = data.get('book_date')
    start_time = data.get('start_time')
    end_time   = data.get('end_time')
    if not all([book_date, start_time, end_time]):
        return jsonify({'success': False, 'msg': '请填写完整的预约信息'})
    venue = db.get_one("SELECT * FROM business_venues WHERE id=%s AND deleted=0 AND status='open'", [venue_id])
    if not venue:
        return jsonify({'success': False, 'msg': '场地不存在或已关闭'})
    try:
        from datetime import datetime
        s = datetime.strptime(start_time, '%H:%M')
        e = datetime.strptime(end_time, '%H:%M')
        hours = max((e - s).seconds / 3600, 0.5)
        total_price = float(venue.get('price') or 0) * hours
    except:
        hours = 1; total_price = float(venue.get('price') or 0)
    verify_code = utils.generate_no('VBK')[-6:]
    db.execute(
        "INSERT INTO business_venue_bookings "
        "(venue_id,user_id,user_name,user_phone,book_date,start_time,end_time,total_hours,total_price,status,verify_code) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s)",
        [venue_id, user['user_id'], user['user_name'], user.get('phone'),
         book_date, start_time, end_time, hours, total_price, verify_code]
    )
    return jsonify({'success': True, 'msg': '预约成功', 'data': {'verify_code': verify_code}})

# ============ 门店 ============

@app.route('/api/shops', methods=['GET'])
def get_shops():
    shop_type = request.args.get('type')
    where  = "status='open' AND deleted=0"
    params = []
    if shop_type:
        where += " AND shop_type=%s"; params.append(shop_type)
    shops = db.get_all(
        "SELECT id,shop_name,shop_type,address,phone,description,business_hours FROM business_shops WHERE "
        + where + " ORDER BY id ASC",
        params
    )
    return jsonify({'success': True, 'data': shops})

@app.route('/api/products', methods=['GET'])
def get_products():
    shop_id = request.args.get('shop_id')
    where  = "status='active' AND deleted=0"
    params = []
    if shop_id:
        where += " AND shop_id=%s"; params.append(shop_id)
    products = db.get_all(
        "SELECT id,shop_id,product_name,product_name,category,price,description,images FROM business_products WHERE "
        + where + " ORDER BY id ASC",
        params
    )
    return jsonify({'success': True, 'data': products})

# ============ 健康检查 ============

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'user-h5', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22311, debug=False)
