#!/usr/bin/env python3
"""
社区商业管理系统 - 后端API
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# 数据库配置
DB_CONFIG = {
    'host': '47.98.238.209',
    'port': 3306,
    'user': 'root',
    'password': 'Wojiacloud$2023',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def success(data=None, msg='success'):
    return jsonify({'success': True, 'msg': msg, 'data': data})

def error(msg='error', code=400):
    return jsonify({'success': False, 'msg': msg}), code

# ============ 通用功能 ============

def get_current_user():
    """获取当前用户信息"""
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev', '0')
    if not token:
        return None
    # 验证 token 获取用户信息
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM sys_user WHERE token=%s", (token,))
        user = cursor.fetchone()
        db.close()
        return user
    except:
        return None

# ============ 门店管理 API ============

@app.route('/api/business/shops', methods=['GET'])
def get_shops():
    """获取门店列表"""
    shop_type = request.args.get('type')
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    if shop_type:
        cursor.execute("SELECT * FROM business_shops WHERE shop_type=%s AND status='open' AND deleted=0", (shop_type,))
    else:
        cursor.execute("SELECT * FROM business_shops WHERE status='open' AND deleted=0")
    
    shops = cursor.fetchall()
    db.close()
    return success(shops)

@app.route('/api/business/shops/<int:shop_id>', methods=['GET'])
def get_shop_detail(shop_id):
    """获取门店详情"""
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM business_shops WHERE id=%s AND deleted=0", (shop_id,))
    shop = cursor.fetchone()
    db.close()
    
    if not shop:
        return error('门店不存在')
    return success(shop)

# ============ 商品管理 API ============

@app.route('/api/business/products', methods=['GET'])
def get_products():
    """获取商品列表"""
    shop_id = request.args.get('shop_id', type=int)
    category = request.args.get('category')
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    sql = "SELECT * FROM business_products WHERE status='available' AND deleted=0"
    params = []
    
    if shop_id:
        sql += " AND shop_id=%s"
        params.append(shop_id)
    if category:
        sql += " AND category=%s"
        params.append(category)
    
    sql += " ORDER BY sort_order ASC, created_at DESC"
    
    cursor.execute(sql, params)
    products = cursor.fetchall()
    db.close()
    return success(products)

@app.route('/api/business/products/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    """获取商品详情"""
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM business_products WHERE id=%s AND deleted=0", (product_id,))
    product = cursor.fetchone()
    db.close()
    
    if not product:
        return error('商品不存在')
    return success(product)

# ============ 订单管理 API ============

def generate_order_no():
    """生成订单编号"""
    return 'BC' + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(datetime.datetime.now().microsecond)[:3]

@app.route('/api/business/orders', methods=['POST'])
def create_order():
    """创建订单"""
    user = get_current_user()
    if not user:
        return error('请先登录', 401)
    
    data = request.get_json()
    order_type = data.get('order_type')  # dine_in/takeout/delivery/pickup
    shop_id = data.get('shop_id')
    items = data.get('items', [])
    
    if not items:
        return error('请选择商品')
    
    # 计算订单金额
    total_amount = sum(item['price'] * item['quantity'] for item in items)
    
    db = get_db()
    cursor = db.cursor()
    
    # 创建订单
    order_no = generate_order_no()
    sql = """INSERT INTO business_orders 
             (order_no, order_type, shop_id, user_id, user_name, user_phone, 
              delivery_address, appointment_time, person_count, total_amount, actual_amount, order_status)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    
    cursor.execute(sql, (
        order_no, order_type, shop_id, 
        user.get('id'), user.get('user_name'), user.get('phone'),
        data.get('delivery_address'), data.get('appointment_time'),
        data.get('person_count', 1), total_amount, total_amount, 'pending'
    ))
    
    order_id = cursor.lastrowid
    
    # 添加订单明细
    item_sql = """INSERT INTO business_order_items 
                  (order_id, product_id, product_name, product_image, price, quantity, subtotal)
                  VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    
    for item in items:
        cursor.execute(item_sql, (
            order_id, item['product_id'], item['product_name'],
            item.get('product_image'), item['price'], item['quantity'],
            item['price'] * item['quantity']
        ))
    
    db.commit()
    db.close()
    
    return success({'order_id': order_id, 'order_no': order_no}, '订单创建成功')

@app.route('/api/business/orders', methods=['GET'])
def get_orders():
    """获取订单列表"""
    user = get_current_user()
    if not user:
        return error('请先登录', 401)
    
    status = request.args.get('status')
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    sql = "SELECT * FROM business_orders WHERE user_id=%s AND deleted=0"
    params = [user.get('id')]
    
    if status:
        sql += " AND order_status=%s"
        params.append(status)
    
    sql += " ORDER BY created_at DESC LIMIT 50"
    
    cursor.execute(sql, params)
    orders = cursor.fetchall()
    
    # 获取订单明细
    for order in orders:
        cursor.execute("SELECT * FROM business_order_items WHERE order_id=%s", (order['id'],))
        order['items'] = cursor.fetchall()
    
    db.close()
    return success(orders)

@app.route('/api/business/orders/<int:order_id>', methods=['GET'])
def get_order_detail(order_id):
    """获取订单详情"""
    user = get_current_user()
    if not user:
        return error('请先登录', 401)
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("SELECT * FROM business_orders WHERE id=%s AND user_id=%s", 
                   (order_id, user.get('id')))
    order = cursor.fetchone()
    
    if order:
        cursor.execute("SELECT * FROM business_order_items WHERE order_id=%s", (order_id,))
        order['items'] = cursor.fetchall()
    
    db.close()
    
    if not order:
        return error('订单不存在')
    return success(order)

# ============ 场地预定 API ============

@app.route('/api/business/venues', methods=['GET'])
def get_venues():
    """获取场地列表"""
    venue_type = request.args.get('type')
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    if venue_type:
        cursor.execute("SELECT * FROM business_venues WHERE venue_type=%s AND status='open' AND deleted=0", (venue_type,))
    else:
        cursor.execute("SELECT * FROM business_venues WHERE status='open' AND deleted=0")
    
    venues = cursor.fetchall()
    db.close()
    return success(venues)

@app.route('/api/business/venues/<int:venue_id>/bookings', methods=['GET'])
def get_venue_bookings(venue_id):
    """获取场地预定情况"""
    book_date = request.args.get('date', datetime.date.today().isoformat())
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""SELECT * FROM business_venue_bookings 
                     WHERE venue_id=%s AND book_date=%s AND status IN ('pending', 'confirmed')
                     AND deleted=0""", 
                  (venue_id, book_date))
    
    bookings = cursor.fetchall()
    db.close()
    return success(bookings)

@app.route('/api/business/venues/book', methods=['POST'])
def create_venue_booking():
    """预定场地"""
    user = get_current_user()
    if not user:
        return error('请先登录', 401)
    
    data = request.get_json()
    venue_id = data.get('venue_id')
    book_date = data.get('book_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    db = get_db()
    cursor = db.cursor()
    
    # 检查时间是否已被预定
    cursor.execute("""SELECT COUNT(*) FROM business_venue_bookings 
                     WHERE venue_id=%s AND book_date=%s AND status IN ('pending', 'confirmed')
                     AND ((start_time<%s AND end_time>%s) OR (start_time<%s AND end_time>%s) 
                     OR (start_time>=%s AND end_time<=%s))""",
                  (venue_id, book_date, start_time, start_time, end_time, end_time, start_time, end_time))
    
    if cursor.fetchone()[0] > 0:
        db.close()
        return error('该时间段已被预定')
    
    # 计算价格
    cursor.execute("SELECT price FROM business_venues WHERE id=%s", (venue_id,))
    venue = cursor.fetchone()
    if not venue:
        db.close()
        return error('场地不存在')
    
    # 计算小时数
    start = datetime.datetime.strptime(start_time, '%H:%M')
    end = datetime.datetime.strptime(end_time, '%H:%M')
    hours = (end - start).seconds / 3600
    total_price = float(venue[0]) * hours
    
    # 生成核销码
    verify_code = datetime.datetime.now().strftime('%Y%m%d%H%M%S')[-6:]
    
    sql = """INSERT INTO business_venue_bookings 
             (venue_id, user_id, user_name, user_phone, book_date, start_time, end_time, total_hours, total_price, verify_code, status)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    
    cursor.execute(sql, (
        venue_id, user.get('id'), user.get('user_name'), user.get('phone'),
        book_date, start_time, end_time, hours, total_price, verify_code, 'pending'
    ))
    
    db.commit()
    booking_id = cursor.lastrowid
    db.close()
    
    return success({'booking_id': booking_id, 'verify_code': verify_code}, '预定成功')

# ============ 会员管理 API ============

@app.route('/api/business/member', methods=['GET'])
def get_member_info():
    """获取会员信息"""
    user = get_current_user()
    if not user:
        return error('请先登录', 401)
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("SELECT * FROM business_members WHERE user_id=%s", (user.get('id'),))
    member = cursor.fetchone()
    
    if not member:
        # 创建会员
        cursor.execute("""INSERT INTO business_members (user_id, user_name, phone, member_level, points, balance)
                         VALUES (%s, %s, %s, 'bronze', 0, 0)""",
                      (user.get('id'), user.get('user_name'), user.get('phone')))
        db.commit()
        cursor.execute("SELECT * FROM business_members WHERE user_id=%s", (user.get('id'),))
        member = cursor.fetchone()
    
    db.close()
    return success(member)

@app.route('/api/business/points/log', methods=['GET'])
def get_points_log():
    """获取积分记录"""
    user = get_current_user()
    if not user:
        return error('请先登录', 401)
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""SELECT * FROM business_points_log 
                     WHERE user_id=%s ORDER BY created_at DESC LIMIT 50""",
                  (user.get('id'),))
    logs = cursor.fetchall()
    db.close()
    return success(logs)

# ============ 优惠券 API ============

@app.route('/api/business/coupons', methods=['GET'])
def get_coupons():
    """获取优惠券列表"""
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""SELECT * FROM business_coupons 
                     WHERE status='active' AND valid_to>=CURDATE()
                     AND total_count > received_count
                     ORDER BY created_at DESC""")
    coupons = cursor.fetchall()
    db.close()
    return success(coupons)

@app.route('/api/business/coupons/<int:coupon_id>/receive', methods=['POST'])
def receive_coupon(coupon_id):
    """领取优惠券"""
    user = get_current_user()
    if not user:
        return error('请先登录', 401)
    
    db = get_db()
    cursor = db.cursor()
    
    # 检查优惠券是否存在
    cursor.execute("SELECT * FROM business_coupons WHERE id=%s AND status='active'", (coupon_id,))
    coupon = cursor.fetchone()
    
    if not coupon:
        db.close()
        return error('优惠券不存在')
    
    # 检查是否已领取
    cursor.execute("SELECT COUNT(*) FROM business_user_coupons WHERE user_id=%s AND coupon_id=%s",
                  (user.get('id'), coupon_id))
    if cursor.fetchone()[0] > 0:
        db.close()
        return error('您已领取过该优惠券')
    
    # 领取优惠券
    cursor.execute("INSERT INTO business_user_coupons (user_id, coupon_id) VALUES (%s, %s)",
                  (user.get('id'), coupon_id))
    
    # 更新已领取数量
    cursor.execute("UPDATE business_coupons SET received_count=received_count+1 WHERE id=%s", (coupon_id,))
    
    db.commit()
    db.close()
    
    return success(None, '优惠券领取成功')

@app.route('/api/business/my/coupons', methods=['GET'])
def get_my_coupons():
    """获取我的优惠券"""
    user = get_current_user()
    if not user:
        return error('请先登录', 401)
    
    status = request.args.get('status', 'unused')
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""SELECT uc.*, c.coupon_name, c.coupon_type, c.discount_amount, c.min_amount, c.valid_to
                     FROM business_user_coupons uc
                     JOIN business_coupons c ON uc.coupon_id=c.id
                     WHERE uc.user_id=%s AND uc.status=%s
                     ORDER BY uc.received_at DESC""",
                  (user.get('id'), status))
    
    coupons = cursor.fetchall()
    db.close()
    return success(coupons)

# ============ 公告 API ============

@app.route('/api/business/notices', methods=['GET'])
def get_notices():
    """获取公告列表"""
    notice_type = request.args.get('type')
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    sql = "SELECT * FROM business_notices WHERE publish_status='published'"
    params = []
    
    if notice_type:
        sql += " AND notice_type=%s"
        params.append(notice_type)
    
    sql += " ORDER BY publish_time DESC LIMIT 20"
    
    cursor.execute(sql, params)
    notices = cursor.fetchall()
    db.close()
    return success(notices)

# ============ 评价 API ============

@app.route('/api/business/reviews', methods=['GET'])
def get_reviews():
    """获取评价列表"""
    shop_id = request.args.get('shop_id', type=int)
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    sql = "SELECT * FROM business_reviews WHERE 1=1"
    params = []
    
    if shop_id:
        sql += " AND shop_id=%s"
        params.append(shop_id)
    
    sql += " ORDER BY created_at DESC LIMIT 20"
    
    cursor.execute(sql, params)
    reviews = cursor.fetchall()
    db.close()
    return success(reviews)

@app.route('/api/business/reviews', methods=['POST'])
def create_review():
    """提交评价"""
    user = get_current_user()
    if not user:
        return error('请先登录', 401)
    
    data = request.get_json()
    order_id = data.get('order_id')
    shop_id = data.get('shop_id')
    rating = data.get('rating')
    content = data.get('content')
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""INSERT INTO business_reviews 
                     (order_id, shop_id, user_id, user_name, rating, content)
                     VALUES (%s, %s, %s, %s, %s, %s)""",
                  (order_id, shop_id, user.get('id'), user.get('user_name'), rating, content))
    
    db.commit()
    db.close()
    
    return success(None, '评价提交成功')

# ============ 健康检查 ============

@app.route('/health', methods=['GET'])
def health():
    return success({'status': 'ok', 'module': 'business'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22311, debug=True)
