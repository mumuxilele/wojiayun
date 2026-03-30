#!/usr/bin/env python3
"""
社区商业 - 用户端 H5 服务
端口: 22311
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys, os, time, json, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

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
        'user_name': user.get('user_name', ''),
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
    images_raw = data.get('images', [])
    priority = int(data.get('priority', 0))

    if not app_type or not title:
        return jsonify({'success': False, 'msg': '请填写必要信息'})
    if len(title) > 100:
        return jsonify({'success': False, 'msg': '标题不能超过100个字符'})
    if len(content) > 2000:
        return jsonify({'success': False, 'msg': '内容不能超过2000个字符'})

    # XSS基础防护：转义HTML特殊字符
    import html as html_mod
    title = html_mod.escape(title)
    content = html_mod.escape(str(content))

    # 图片校验：限制数量和base64大小（防止超大请求）
    MAX_IMAGES = 5
    MAX_BASE64_SIZE = 1.5 * 1024 * 1024  # 约1.5MB per image (base64)
    if not isinstance(images_raw, list):
        images_raw = []
    if len(images_raw) > MAX_IMAGES:
        return jsonify({'success': False, 'msg': f'最多上传{MAX_IMAGES}张图片'})
    valid_images = []
    for img in images_raw:
        if isinstance(img, str):
            if img.startswith('data:image/') and len(img) > MAX_BASE64_SIZE:
                return jsonify({'success': False, 'msg': '单张图片不能超过1MB，请压缩后上传'})
            if img.startswith('data:image/') or img.startswith('http'):
                valid_images.append(img)
    images = json.dumps(valid_images)

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
    # 解析图片列表
    if app.get('images'):
        try:
            app['images_list'] = json.loads(app['images'])
        except:
            app['images_list'] = []
    return jsonify({'success': True, 'data': app})

@app.route('/api/user/applications/<app_id>/cancel', methods=['POST'])
@require_login
def cancel_application(user, app_id):
    """用户撤销申请（仅pending状态可撤销）"""
    app = db.get_one(
        "SELECT * FROM business_applications WHERE id=%s AND user_id=%s AND deleted=0",
        [app_id, user['user_id']]
    )
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    if app.get('status') != 'pending':
        return jsonify({'success': False, 'msg': '只有待处理的申请才可撤销'})
    db.execute(
        "UPDATE business_applications SET status='cancelled', updated_at=NOW() WHERE id=%s",
        [app_id]
    )
    return jsonify({'success': True, 'msg': '申请已撤销'})

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

@app.route('/api/user/orders/<order_id>/cancel', methods=['POST'])
@require_login
def cancel_order(user, order_id):
    """用户取消订单（仅pending状态可取消）"""
    order = db.get_one(
        "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
        [order_id, user['user_id']]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    status = order.get('order_status') or order.get('status', '')
    if status not in ('pending', ''):
        return jsonify({'success': False, 'msg': '只有待支付的订单才可取消'})
    db.execute(
        "UPDATE business_orders SET order_status='cancelled', updated_at=NOW() WHERE id=%s",
        [order_id]
    )
    return jsonify({'success': True, 'msg': '订单已取消'})

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
        "SELECT vb.id, vb.venue_id, vb.book_date, "
        "CAST(vb.start_time AS CHAR) as start_time, CAST(vb.end_time AS CHAR) as end_time, "
        "CAST(vb.total_hours AS CHAR) as total_hours, vb.total_price, vb.status, vb.verify_code, vb.created_at, "
        "v.venue_name, v.venue_type, v.images "
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
        if e <= s:
            return jsonify({'success': False, 'msg': '结束时间必须晚于开始时间'})
        hours = max((e - s).seconds / 3600, 0.5)
        total_price = float(venue.get('price') or 0) * hours
    except:
        hours = 1; total_price = float(venue.get('price') or 0)
    
    # 并发安全：使用数据库事务锁防止重复预约
    conn = db.get_db()
    try:
        cursor = conn.cursor()
        conn.begin()
        
        # FOR UPDATE 锁定相关行，防止并发重复预约
        cursor.execute(
            "SELECT id FROM business_venue_bookings "
            "WHERE venue_id=%s AND book_date=%s AND deleted=0 "
            "AND status IN ('pending','confirmed') "
            "AND NOT (end_time<=%s OR start_time>=%s) "
            "FOR UPDATE",
            [venue_id, book_date, start_time, end_time]
        )
        conflicts = cursor.fetchall()
        if conflicts:
            conn.rollback()
            return jsonify({'success': False, 'msg': '该时段已被预约，请选择其他时间'})
        
        verify_code = utils.generate_no('VBK')[-6:]
        cursor.execute(
            "INSERT INTO business_venue_bookings "
            "(venue_id,user_id,user_name,user_phone,book_date,start_time,end_time,total_hours,total_price,status,pay_status,verify_code,ec_id,project_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending','unpaid',%s,%s,%s)",
            [venue_id, user['user_id'], user['user_name'], user.get('phone'),
             book_date, start_time, end_time, hours, total_price, verify_code,
             user.get('ec_id'), user.get('project_id')]
        )
        conn.commit()
        return jsonify({'success': True, 'msg': '预约成功', 'data': {'verify_code': verify_code}})
    except Exception as e:
        conn.rollback()
        logging.error('book_venue error: %s', e)
        return jsonify({'success': False, 'msg': '预约失败，请稍后重试'})
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# ============ 积分与会员信息 ============

@app.route('/api/user/member', methods=['GET'])
@require_login
def get_user_member(user):
    """获取当前用户的会员积分信息"""
    uid = user['user_id']
    member = db.get_one(
        "SELECT user_id, user_name, phone, member_level, points, total_points, balance FROM business_members WHERE user_id=%s",
        [uid]
    )
    # 若会员不存在则自动初始化
    if not member:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        try:
            db.execute(
                "INSERT IGNORE INTO business_members (user_id, user_name, phone, points, total_points, balance, member_level, ec_id, project_id) "
                "VALUES (%s,%s,%s,0,0,0,'bronze',%s,%s)",
                [uid, user.get('user_name', ''), user.get('phone', ''), ec_id, project_id]
            )
            member = {'user_id': uid, 'user_name': user.get('user_name', ''), 'phone': user.get('phone', ''),
                      'member_level': 'bronze', 'points': 0, 'total_points': 0, 'balance': 0}
        except Exception as e:
            logging.warning('auto create member failed: %s', e)
            member = {'user_id': uid, 'points': 0, 'total_points': 0, 'balance': 0, 'member_level': 'bronze'}
    return jsonify({'success': True, 'data': member})

@app.route('/api/user/points/logs', methods=['GET'])
@require_login
def get_user_points_logs(user):
    """获取当前用户的积分记录"""
    uid = user['user_id']
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    log_type = request.args.get('type')
    where = "user_id=%s"
    params = [uid]
    if log_type:
        where += " AND log_type=%s"; params.append(log_type)
    total = db.get_total("SELECT COUNT(*) FROM business_points_log WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id, log_type as type, points, balance_after, description, created_at "
        "FROM business_points_log WHERE " + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

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
        "SELECT id,shop_id,product_name,category,price,description,images FROM business_products WHERE "
        + where + " ORDER BY id ASC",
        params
    )
    return jsonify({'success': True, 'data': products})

@app.route('/api/user/bookings/<booking_id>/cancel', methods=['POST'])
@require_login
def cancel_booking(user, booking_id):
    """用户取消预约（仅pending且未付款可取消）"""
    booking = db.get_one(
        "SELECT * FROM business_venue_bookings WHERE id=%s AND user_id=%s AND deleted=0",
        [booking_id, user['user_id']]
    )
    if not booking:
        return jsonify({'success': False, 'msg': '预约不存在'})
    if booking.get('status') not in ('pending',):
        return jsonify({'success': False, 'msg': '只有待确认的预约才可取消'})
    if booking.get('pay_status') == 'paid':
        return jsonify({'success': False, 'msg': '已付款的预约无法自行取消，请联系管理员'})
    db.execute(
        "UPDATE business_venue_bookings SET status='cancelled', updated_at=NOW() WHERE id=%s",
        [booking_id]
    )
    return jsonify({'success': True, 'msg': '预约已取消'})

# ============ 场馆预约支付 ============

@app.route('/api/user/bookings/<booking_id>/pay', methods=['POST'])
@require_login
def pay_booking(user, booking_id):
    """支付预约（模拟支付）"""
    booking = db.get_one(
        "SELECT * FROM business_venue_bookings WHERE id=%s AND user_id=%s AND deleted=0",
        [booking_id, user['user_id']]
    )
    if not booking:
        return jsonify({'success': False, 'msg': '预约不存在'})
    if booking.get('pay_status') == 'paid':
        return jsonify({'success': True, 'msg': '已支付'})
    db.execute(
        "UPDATE business_venue_bookings SET pay_status='paid', status='confirmed' WHERE id=%s",
        [booking_id]
    )
    return jsonify({'success': True, 'msg': '支付成功'})

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

