#!/usr/bin/env python3
"""
社区商业 - 用户端 H5 服务
端口: 22311
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import sys, os, time, json, logging
import urllib.request
import urllib.parse

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import config, db, auth, utils, error_handler, rate_limiter, notification, payment_service, push_service, user_settings_service
from business_common.cache_service import cache_get, cache_set, cache_delete
from business_common.order_service import OrderService
from business_common.logistics_service import logistics
from business_common.search_service import search
from business_common.cart_recommendation_service import cart_recommendation
from business_common.user_behavior_service import user_behavior_service as user_behavior
from business_common.product_spec_service import spec_service
from business_common.product_qa_service import product_qa
from business_common.points_mall import PointsMallService
from business_common.fid_utils import generate_fid, generate_business_fid  # V47.0: FID生成工具

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

ORDER_EXPIRE_MINUTES = OrderService.ORDER_EXPIRE_MINUTES

# 注册全局错误处理器
error_handler.register_error_handlers(app)

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

def invalidate_user_cache(user_id):
    """清理用户侧统计缓存"""
    try:
    cache_delete(f'user_stats_{user_id}')
    cache_delete(f'user_profile_{user_id}')
def bump_product_counter(product_id, field, delta=1):
    """更新商品行为计数，支持浏览量/收藏量"""
    if not product_id or field not in ('view_count', 'favorite_count'):
    return
    try:
    db.execute(
    f"UPDATE business_products SET {field}=GREATEST(COALESCE({field}, 0) + %s, 0), updated_at=NOW() WHERE id=%s AND deleted=0",
    [int(delta), product_id]
    )
# ============ 统计 ============

@app.route('/api/user/stats', methods=['GET'])
@require_login
def get_user_stats(user):
    """P13优化：合并N+1查询为少量聚合查询"""
    uid = user['user_id']
    
    # 尝试从缓存获取（缓存60秒）
    cache_key = f'user_stats_{uid}'
    cached = cache_get(cache_key)
    if cached:
    return jsonify({'success': True, 'data': cached})
    
    # P13优化：使用 UNION 将多个 COUNT 查询合并为单次 DB 调用
    # 注意：MySQL 不允许在 UNION 中直接用条件聚合，我们改用单次多表查询
    
    # 方案1：单次查询获取所有统计（推荐）
    stats = db.get_one("""
    SELECT 
    (SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='pending') AS pending,
    (SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='processing') AS processing,
    (SELECT COUNT(*) FROM business_applications WHERE user_id=%s AND deleted=0 AND status='completed') AS completed,
    (SELECT COUNT(*) FROM business_orders WHERE user_id=%s AND deleted=0) AS orders,
    (SELECT COUNT(*) FROM business_venue_bookings WHERE user_id=%s AND deleted=0) AS bookings,
    (SELECT COUNT(*) FROM business_notifications WHERE user_id=%s AND is_read=0) AS unread_notifications,
    (SELECT COUNT(*) FROM business_user_coupons uc 
    WHERE uc.user_id=%s AND uc.status='unused' 
    AND (SELECT valid_until FROM business_coupons c WHERE c.id=uc.coupon_id) >= CURDATE()) AS unused_coupons
    """, [uid, uid, uid, uid, uid, uid, uid])
    
    data = {
    'user_name': user.get('user_name', ''),
    'pending': stats.get('pending', 0) if stats else 0, 
    'processing': stats.get('processing', 0) if stats else 0,
    'completed': stats.get('completed', 0) if stats else 0, 
    'orders': stats.get('orders', 0) if stats else 0, 
    'bookings': stats.get('bookings', 0) if stats else 0,
    'unread_notifications': stats.get('unread_notifications', 0) if stats else 0,
    'unused_coupons': stats.get('unused_coupons', 0) if stats else 0
    }
    
    # 缓存60秒
    cache_set(cache_key, data, 60)
    
    return jsonify({'success': True, 'data': data})

# ============ 申请单 ============

@app.route('/api/user/applications', methods=['GET'])
@require_login
def get_user_applications(user):
    """获取用户申请列表"""
    from business_common.application_service import ApplicationService
    type_code = request.args.get('type_code')
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    result = ApplicationService.get_user_applications(
        user_id=user['user_id'], type_code=type_code, status=status,
        page=page, page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/applications', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=20, window_seconds=60)  # 限流：每分钟最多20次申请
def create_application(user):
    data    = request.get_json() or {}
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
    app_fid = generate_business_fid('app')  # V47.0: 生成FID主键
    db.execute(
    "INSERT INTO business_applications (fid,app_no,app_type,title,content,user_id,user_name,user_phone,ec_id,project_id,status,images,priority) "
    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s)",
    [app_fid, app_no, app_type, title, content, user['user_id'], user['user_name'],
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
    """取消申请"""
    from business_common.application_service import ApplicationService
    result = ApplicationService.cancel_application(
        app_id=int(app_id), user_id=user['user_id']
    )
    return jsonify(result)

@app.route('/api/cart', methods=['GET'])
@require_login
def get_cart(user):
    """V32.0: 获取购物车详情"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    cart_data = cart_service.get_cart(user['user_id'], ec_id, project_id)
    return jsonify({'success': True, 'data': cart_data})

@app.route('/api/cart/add', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=30, window_seconds=60)
def add_to_cart(user):
    """V32.0: 添加商品到购物车"""
    data = request.get_json() or {}
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    sku_id = data.get('sku_id')
    session_id = data.get('session_id')  # 游客会话ID

    if not product_id:
    return jsonify({'success': False, 'msg': '请选择商品'})

    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    result = cart_service.add_to_cart(
    user_id=user['user_id'],
    product_id=product_id,
    quantity=quantity,
    sku_id=sku_id,
    ec_id=ec_id,
    project_id=project_id
    )

    # V32.0: 游客购物车合并
    if session_id and result.get('success'):
    cart_service.merge_cart(user['user_id'], session_id, ec_id, project_id)

    return jsonify(result)

@app.route('/api/cart/update', methods=['POST'])
@require_login
def update_cart_item(user):
    """V32.0: 更新购物车商品数量"""
    data = request.get_json() or {}
    cart_id = data.get('cart_id')
    quantity = int(data.get('quantity', 1))

    if not cart_id:
    return jsonify({'success': False, 'msg': '缺少购物车项ID'})

    result = cart_service.update_quantity(user['user_id'], cart_id, quantity)
    return jsonify(result)

@app.route('/api/cart/remove', methods=['POST'])
@require_login
def remove_from_cart(user):
    """V32.0: 从购物车移除商品"""
    data = request.get_json() or {}
    cart_id = data.get('cart_id')

    if not cart_id:
    return jsonify({'success': False, 'msg': '缺少购物车项ID'})

    result = cart_service.remove_from_cart(user['user_id'], cart_id)
    return jsonify(result)

@app.route('/api/cart/clear', methods=['POST'])
@require_login
def clear_cart(user):
    """V32.0: 清空购物车"""
    result = cart_service.clear_cart(user['user_id'])
    return jsonify(result)

@app.route('/api/cart/select', methods=['POST'])
@require_login
def select_cart_items(user):
    """V32.0: 选择/取消选择购物车商品"""
    data = request.get_json() or {}
    cart_ids = data.get('cart_ids', [])
    selected = data.get('selected', True)

    if not isinstance(cart_ids, list):
    cart_ids = [cart_ids]

    result = cart_service.select_items(user['user_id'], cart_ids, selected)
    return jsonify(result)

@app.route('/api/cart/quick-buy', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def quick_buy(user):
    """V32.0: 立即购买（跳过购物车）"""
    data = request.get_json() or {}
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    sku_id = data.get('sku_id')
    address_id = data.get('address_id')

    if not product_id:
    return jsonify({'success': False, 'msg': '请选择商品'})

    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    result = cart_service.create_quick_order(
    user_id=user['user_id'],
    product_id=product_id,
    quantity=quantity,
    sku_id=sku_id,
    ec_id=ec_id,
    project_id=project_id,
    address_id=address_id
    )

    return jsonify(result)

@app.route('/api/cart/merge', methods=['POST'])
@require_login
def merge_cart(user):
    """V32.0: 合并游客购物车到用户购物车"""
    data = request.get_json() or {}
    session_id = data.get('session_id')

    if not session_id:
    return jsonify({'success': True, 'msg': '无需合并', 'merged_count': 0})

    result = cart_service.merge_cart(
    user_id=user['user_id'],
    session_id=session_id,
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )

    return jsonify(result)

# ============ V41.0: 路由别名兼容层 ============
# 修复前后端路由不匹配问题，前端使用 /api/user/* 后端使用 /api/*
# 为保证向后兼容，添加别名路由

@app.route('/api/user/products', methods=['GET'])
def get_products_user_alias():
    """V41.0: 商品列表 - /api/user/products 别名 (兼容前端)"""
    return get_products()

@app.route('/api/user/cart', methods=['GET'])
@require_login
def get_cart_user_alias(user):
    """V41.0: 获取购物车 - /api/user/cart 别名 (兼容前端)"""
    return get_cart(user)

@app.route('/api/user/cart/add', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=30, window_seconds=60)
def add_to_cart_user_alias(user):
    """V41.0: 添加到购物车 - /api/user/cart/add 别名 (兼容前端)"""
    return add_to_cart(user)

@app.route('/api/user/cart/update', methods=['POST'])
@require_login
def update_cart_user_alias(user):
    """V41.0: 更新购物车 - /api/user/cart/update 别名 (兼容前端)"""
    return update_cart_item(user)

@app.route('/api/user/cart/select-all', methods=['POST'])
@require_login
def select_all_cart_alias(user):
    """V41.0: 全选购物车商品"""
    data = request.get_json() or {}
    selected = data.get('selected', True)
    
    # 获取所有未删除的购物车商品
    cart_items = db.get_all(
    "SELECT id FROM business_cart WHERE user_id=%s AND deleted=0",
    [user['user_id']]
    ) or []
    
    cart_ids = [item['id'] for item in cart_items]
    if cart_ids:
    result = cart_service.select_items(user['user_id'], cart_ids, bool(selected))
    else:
    result = {'success': True, 'msg': '购物车为空'}
    return jsonify(result)

@app.route('/api/user/cart/<int:cart_id>', methods=['PUT'])
@require_login
def update_cart_item_alias(user, cart_id):
    """V41.0: 更新购物车商品 - 支持 /api/user/cart/{id} 路径"""
    data = request.get_json() or {}
    quantity = int(data.get('quantity', 1))
    selected = data.get('selected')
    
    if quantity:
    result = cart_service.update_quantity(user['user_id'], cart_id, quantity)
    elif selected is not None:
    result = cart_service.select_items(user['user_id'], [cart_id], bool(selected))
    else:
    return jsonify({'success': False, 'msg': '缺少更新参数'})
    return jsonify(result)

@app.route('/api/user/cart/<int:cart_id>', methods=['DELETE'])
@require_login
def remove_from_cart_alias(user, cart_id):
    """V41.0: 删除购物车商品 - 支持 /api/user/cart/{id} DELETE 路径"""
    result = cart_service.remove_from_cart(user['user_id'], cart_id)
    return jsonify(result)

@app.route('/api/user/cart/recommendations', methods=['GET'])
@require_login
def get_cart_recommendations(user):
    """V41.0: 获取购物车智能推荐"""
    ec_id = user.get('ec_id', 1)
    project_id = user.get('project_id', 1)
    
    # 获取购物车商品ID用于排除
    cart_items = db.get_all(
    "SELECT product_id FROM business_cart WHERE user_id=%s AND deleted=0",
    [user['user_id']]
    ) or []
    exclude_ids = [item['product_id'] for item in cart_items if item.get('product_id')]
    
    # 获取4种类型的推荐
    cart_recommend = cart_recommendation.get_recommendations(
    user['user_id'], ec_id, project_id, 'cart', exclude_ids
    )
    viewed_recommend = cart_recommendation.get_recommendations(
    user['user_id'], ec_id, project_id, 'viewed', exclude_ids
    )
    purchased_recommend = cart_recommendation.get_recommendations(
    user['user_id'], ec_id, project_id, 'purchased', exclude_ids
    )
    similar_recommend = cart_recommendation.get_recommendations(
    user['user_id'], ec_id, project_id, 'similar', exclude_ids
    )
    
    # 合并去重
    seen = set(exclude_ids)
    merged = []
    for rec_list in [cart_recommend, viewed_recommend, purchased_recommend, similar_recommend]:
    for item in rec_list:
    if item['id'] not in seen and len(merged) < 12:
    seen.add(item['id'])
    merged.append(item)
    
    return jsonify({'success': True, 'data': merged or []})

@app.route('/api/user/behavior/track', methods=['POST'])
@require_login
def track_user_behavior(user):
    """记录用户行为"""
    data = request.get_json() or {}
    try:
        user_behavior.track(
            user_id=user['user_id'],
            action=data.get('action'),
            target_type=data.get('target_type'),
            target_id=data.get('target_id'),
            ec_id=user.get('ec_id'),
            project_id=user.get('project_id')
        )
    return jsonify({'success': True})

@app.route('/api/user/orders', methods=['GET'])
@require_login
def get_user_orders(user):
    """获取用户订单列表"""
    status = request.args.get('status')
    keyword = request.args.get('keyword', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 10)), 50)
    offset = (page - 1) * page_size
    
    conditions = ["user_id=%s", "deleted=0"]
    params = [user['user_id']]
    if status: conditions.append("order_status=%s"); params.append(status)
    if keyword:
        conditions.append("(order_no LIKE %s OR shipping_address LIKE %s)")
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    
    where = " AND ".join(conditions)
    total = db.get_total(f"SELECT COUNT(*) FROM business_orders WHERE {where}", params)
    orders = db.get_all(
        f"SELECT id,order_no,order_type,total_amount,actual_amount,order_status,pay_status,"
        f"refund_status,created_at,shipping_address FROM business_orders WHERE {where} "
        f"ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {
        'items': orders, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/user/orders/<order_id>', methods=['GET'])
@require_login
def get_order_detail(user, order_id):
    """获取订单详情"""
    order = db.get_one(
        "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
        [order_id, user['user_id']]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    items = db.get_all(
        "SELECT * FROM business_order_items WHERE order_id=%s",
        [order_id]
    ) or []
    order['items'] = items
    return jsonify({'success': True, 'data': order})

@app.route('/api/user/orders/<order_id>/cancel', methods=['POST'])
@require_login
def cancel_order(user, order_id):
    """用户取消订单（仅pending状态可取消）"""
    order_service = OrderService()
    return jsonify(order_service.cancel_order(
    order_id=int(order_id),
    user_id=user['user_id'],
    reason='用户取消'
    ))

@app.route('/api/user/orders/<order_id>/refund', methods=['POST'])
@require_login
def apply_refund(user, order_id):
    """V19.0: 用户申请退款"""
    data = request.get_json() or {}
    reason = (data.get('reason') or '').strip()
    if not reason:
    return jsonify({'success': False, 'msg': '请填写退款原因'})
    
    order = db.get_one(
    "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
    [order_id, user['user_id']]
    )
    if not order:
    return jsonify({'success': False, 'msg': '订单不存在'})
    if order.get('pay_status') != 'paid':
    return jsonify({'success': False, 'msg': '订单未支付，无法申请退款'})
    if order.get('refund_status') in ('pending', 'processing'):
    return jsonify({'success': False, 'msg': '您已有退款申请在处理中'})
    
    try:
    db.execute(
    "UPDATE business_orders SET refund_status='pending', refund_reason=%s, refund_requested_at=NOW() WHERE id=%s",
    [reason, order_id]
    )
    
    return jsonify({'success': True, 'msg': '退款申请已提交'})
    except Exception as e:
    return jsonify({'success': False, 'msg': '申请失败'})

# ============ 订单增强 V32.0 ============

from business_common.order_enhance_service import order_enhance

@app.route('/api/user/orders/<order_id>/update', methods=['POST'])
@require_login
def update_order(user, order_id):
    """V32.0: 修改订单（收货信息）"""
    data = request.get_json() or {}
    result = order_enhance.update_order(
    order_id=order_id,
    user_id=user['user_id'],
    update_data=data,
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/user/orders/<order_id>/partial-refund', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=5, window_seconds=60)
def apply_partial_refund(user, order_id):
    """V32.0: 申请部分退款"""
    data = request.get_json() or {}
    refund_items = data.get('items', [])
    reason = data.get('reason', '')

    if not refund_items:
    return jsonify({'success': False, 'msg': '请选择要退款的商品'})

    result = order_enhance.partial_refund(
    order_id=order_id,
    user_id=user['user_id'],
    refund_items=refund_items,
    reason=reason,
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/user/orders/<order_id>/notes', methods=['GET'])
@require_login
def get_order_notes(user, order_id):
    """V32.0: 获取订单留言"""
    result = order_enhance.get_order_notes(
    order_id=order_id,
    user_id=user['user_id'],
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/user/orders/<order_id>/notes', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def add_order_note(user, order_id):
    """V32.0: 添加订单留言"""
    data = request.get_json() or {}
    content = data.get('content', '').strip()

    if not content:
    return jsonify({'success': False, 'msg': '留言内容不能为空'})

    result = order_enhance.add_order_note(
    order_id=order_id,
    user_id=user['user_id'],
    note_type='user_question',
    content=content,
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/user/orders/<order_id>/cancel-with-reason', methods=['POST'])
@require_login
def cancel_order_with_reason(user, order_id):
    """V32.0: 取消订单（带原因）"""
    data = request.get_json() or {}
    reason = data.get('reason', '').strip()

    if not reason:
    return jsonify({'success': False, 'msg': '请填写取消原因'})

    result = order_enhance.cancel_with_reason(
    order_id=order_id,
    user_id=user['user_id'],
    reason=reason,
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/user/orders/<order_id>/detail-enhanced', methods=['GET'])
@require_login
def get_order_detail_enhanced(user, order_id):
    """V32.0: 获取订单详情增强版（包含物流、留言等）"""
    order = order_enhance.get_order_detail_enhanced(
    order_id=order_id,
    user_id=user['user_id'],
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )

    if not order:
    return jsonify({'success': False, 'msg': '订单不存在'})

    return jsonify({'success': True, 'data': order})

# ============ 场馆预约 ============

@app.route('/api/user/bookings', methods=['GET'])
@require_login
def get_user_bookings(user):
    """获取用户预约列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total(
        "SELECT COUNT(*) FROM business_venue_bookings WHERE user_id=%s AND deleted=0",
        [user['user_id']]
    )
    bookings = db.get_all(
        "SELECT b.*,v.venue_name FROM business_venue_bookings b "
        "LEFT JOIN business_venues v ON b.venue_id=v.id "
        "WHERE b.user_id=%s AND b.deleted=0 ORDER BY b.created_at DESC LIMIT %s OFFSET %s",
        [user['user_id'], page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': bookings, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/user/venues', methods=['GET'])
@require_login
def get_venues(user):
    """获取场地列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_venues WHERE status='active' AND deleted=0")
    venues = db.get_all(
        "SELECT id,venue_name,venue_type,price,capacity,cover_image,address FROM business_venues "
        "WHERE status='active' AND deleted=0 ORDER BY sort_order ASC LIMIT %s OFFSET %s",
        [page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': venues, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/user/venues/<venue_id>', methods=['GET'])
@require_login
def get_venue_detail(user, venue_id):
    """获取场地详情"""
    venue = db.get_one(
        "SELECT * FROM business_venues WHERE id=%s AND status='active' AND deleted=0",
        [venue_id]
    )
    if not venue:
        return jsonify({'success': False, 'msg': '场地不存在'})
    time_slots = db.get_all(
        "SELECT * FROM business_venue_time_slots WHERE venue_id=%s AND status=1 ORDER BY start_time",
        [venue_id]
    ) or []
    venue['time_slots'] = time_slots
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
    return jsonify({'success': True, 'data': {'hours': hours}})

@app.route('/api/user/venues/<venue_id>/book', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)  # 限流：每分钟最多10次预约
def book_venue(user, venue_id):
    data    = request.get_json() or {}
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

# ============ 积分与会员信息 ============

@app.route('/api/user/member', methods=['GET'])
@require_login
def get_user_member(user):
    """获取会员信息"""
    member = db.get_one(
        "SELECT m.*, l.level_name, l.discount_rate, l.privileges "
        "FROM business_members m "
        "LEFT JOIN business_member_levels l ON m.member_level=l.level_code "
        "WHERE m.user_id=%s",
        [user['user_id']]
    )
    if not member:
        member = {'user_id': user['user_id'], 'points': 0, 'total_points': 0, 'balance': 0, 'member_level': 'L1'}
    return jsonify({'success': True, 'data': member})

@app.route('/api/user/points/logs', methods=['GET'])
@require_login
def get_user_points_logs(user):
    """获取积分记录"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_points_log WHERE user_id=%s", [user['user_id']])
    logs = db.get_all(
        "SELECT * FROM business_points_log WHERE user_id=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
        [user['user_id'], page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': logs, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/shops', methods=['GET'])
def get_shops():
    """获取门店列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_shops WHERE status='active' AND deleted=0")
    shops = db.get_all(
        "SELECT id,shop_name,address,phone,rating,cover_image FROM business_shops "
        "WHERE status='active' AND deleted=0 ORDER BY sort_order ASC LIMIT %s OFFSET %s",
        [page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': shops, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/shops/<shop_id>', methods=['GET'])
def get_shop_detail(shop_id):
    """获取门店详情"""
    shop = db.get_one(
        "SELECT * FROM business_shops WHERE id=%s AND status='active' AND deleted=0",
        [shop_id]
    )
    if not shop:
        return jsonify({'success': False, 'msg': '门店不存在'})
    return jsonify({'success': True, 'data': shop})

@app.route('/api/products', methods=['GET'])
def get_products():
    """获取商品列表，支持搜索、分类筛选、多维排序 (V12: 新增排序/分页/多租户)"""
    shop_id = request.args.get('shop_id')
    category = request.args.get('category')
    keyword = request.args.get('keyword', '').strip()
    # V12: 排序参数 price_asc/price_desc/sales/hot/new (默认综合排序)
    sort_by = request.args.get('sort_by', 'default')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 100)
    # 价格区间筛选
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    where = "p.status='active' AND p.deleted=0"
    params = []

    if shop_id:
    where += " AND p.shop_id=%s"; params.append(shop_id)
    if category:
    where += " AND p.category=%s"; params.append(category)
    if keyword:
    where += " AND (p.product_name LIKE %s OR p.description LIKE %s)"
    kw = '%' + keyword + '%'
    params.extend([kw, kw])
    if min_price:
    try:
    where += " AND p.price>=%s"; params.append(float(min_price))
    except (ValueError, TypeError):
    pass
    if max_price:
    try:
    where += " AND p.price<=%s"; params.append(float(max_price))
    except (ValueError, TypeError):
    pass

    # 多租户隔离
    user = get_current_user()
    if user:
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    if ec_id:
    where += " AND p.ec_id=%s"; params.append(ec_id)
    if project_id:
    where += " AND p.project_id=%s"; params.append(project_id)

    # 排序逻辑
    ORDER_MAP = {
    'price_asc':  'p.price ASC',
    'price_desc': 'p.price DESC',
    'sales':    'p.sales_count DESC',
    'hot':    'p.view_count DESC',
    'new':    'p.created_at DESC',
    'default':    'p.sort_order ASC, p.sales_count DESC',
    }
    order_clause = ORDER_MAP.get(sort_by, ORDER_MAP['default'])

    total = db.get_total(
    "SELECT COUNT(*) FROM business_products p WHERE " + where, params
    )
    offset = (page - 1) * page_size
    products = db.get_all(
    "SELECT p.id, p.shop_id, p.product_name, p.category, p.price, p.original_price, "
    "p.description, p.images, p.stock, p.sales_count, p.view_count, p.sort_order "
    "FROM business_products p WHERE " + where
    + f" ORDER BY {order_clause} LIMIT %s OFFSET %s",
    params + [page_size, offset]
    )

    return jsonify({'success': True, 'data': {
    'items': products or [],
    'total': total,
    'page': page,
    'page_size': page_size,
    'pages': (total + page_size - 1) // page_size if total else 0,
    'sort_by': sort_by,
    }})

# ============ 增强搜索 V22.0 ============

@app.route('/api/search/products', methods=['GET'])
def search_products():
    """
    增强商品搜索 V22.0
    支持: 全文索引、分词搜索、搜索历史、热门搜索
    """
    keyword = request.args.get('keyword', '').strip()
    category = request.args.get('category_id', type=int)
    sort = request.args.get('sort', 'sales')  # relevance/sales/price_asc/price_desc/new
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 100)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    # 获取用户信息
    user = get_current_user()
    user_id = user['user_id'] if user else None
    ec_id = user.get('ec_id') if user else None
    project_id = user.get('project_id') if user else None

    result = search.search_products(
    keyword=keyword,
    ec_id=ec_id,
    project_id=project_id,
    page=page,
    page_size=page_size,
    category_id=category,
    min_price=min_price,
    max_price=max_price,
    sort=sort,
    user_id=user_id
    )

    return jsonify(result)

@app.route('/api/search/history', methods=['GET'])
@require_login
def get_search_history(user):
    """获取用户搜索历史"""
    limit = min(max(1, int(request.args.get('limit', 10))), 50)
    history = search.get_user_search_history(user['user_id'], limit)
    return jsonify({'success': True, 'data': history})

@app.route('/api/search/history', methods=['DELETE'])
@require_login
def clear_search_history(user):
    """清除用户搜索历史"""
    success = search.clear_user_search_history(user['user_id'])
    return jsonify({'success': success, 'msg': '清除成功' if success else '清除失败'})

@app.route('/api/search/hot', methods=['GET'])
def get_hot_search():
    """获取热门搜索词"""
    user = get_current_user()
    ec_id = user.get('ec_id') if user else None
    project_id = user.get('project_id') if user else None
    limit = min(max(1, int(request.args.get('limit', 20))), 50)

    hot_words = search.get_hot_search_words(ec_id, project_id, limit)
    return jsonify({'success': True, 'data': hot_words})

@app.route('/api/search/suggestions', methods=['GET'])
def get_search_suggestions():
    """获取搜索建议 (自动补全)"""
    keyword = request.args.get('keyword', '').strip()
    if len(keyword) < 1:
    return jsonify({'success': True, 'data': []})

    suggestions = search._get_search_suggestions(keyword)
    return jsonify({'success': True, 'data': suggestions})

@app.route('/api/recommendations', methods=['GET'])
@require_login
def get_recommendations(user):
    """获取个性化推荐商品"""
    limit = min(max(1, int(request.args.get('limit', 10))), 50)
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    recommendations = search.get_recommended_products(
    user['user_id'], ec_id, project_id, limit
    )
    return jsonify({'success': True, 'data': recommendations})

@app.route('/api/products/<product_id>', methods=['GET'])
def get_product_detail(product_id):
    """获取商品详情，包含SKU规格，会员价"""
    from business_common.product_service import ProductService
    product_service = ProductService()
    
    user = get_current_user()
    user_id = user['user_id'] if user else None
    
    product = product_service.get_product_detail_for_user(product_id, user_id)
    
    if not product:
    return jsonify({'success': False, 'msg': '商品不存在或已下架'})
    
    return jsonify({'success': True, 'data': product})

# ============ 公告/通知系统 ============

@app.route('/api/notices', methods=['GET'])
def get_notices():
    """获取公告列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    try:
        total = db.get_total(
            "SELECT COUNT(*) FROM business_notices WHERE status='published' AND deleted=0 AND (end_date IS NULL OR end_date >= CURDATE())"
        )
        notices = db.get_all(
            "SELECT id,title,content,notice_type,importance,created_at FROM business_notices "
            "WHERE status='published' AND deleted=0 AND (end_date IS NULL OR end_date >= CURDATE()) "
            "ORDER BY importance DESC, created_at DESC LIMIT %s OFFSET %s",
            [page_size, offset]
        ) or []
        return jsonify({'success': True, 'data': {'items': notices, 'total': total, 'page': page, 'page_size': page_size}})
    except:
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': page, 'page_size': page_size}})

@app.route('/api/notices/<notice_id>', methods=['GET'])
def get_notice_detail(notice_id):
    """获取公告详情"""
    try:
        notice = db.get_one(
            "SELECT * FROM business_notices WHERE id=%s AND status='published' AND deleted=0",
            [notice_id]
        )
        if not notice:
            return jsonify({'success': False, 'msg': '公告不存在'})
        return jsonify({'success': True, 'data': notice})
    except:
        return jsonify({'success': False, 'msg': '公告不存在'})

@app.route('/api/user/bookings/<booking_id>/cancel', methods=['POST'])
@require_login
def cancel_booking(user, booking_id):
    """取消预约"""
    booking = db.get_one(
        "SELECT id,status FROM business_venue_bookings WHERE id=%s AND user_id=%s AND deleted=0",
        [booking_id, user['user_id']]
    )
    if not booking:
        return jsonify({'success': False, 'msg': '预约不存在'})
    if booking.get('status') not in ('pending', 'reserved'):
        return jsonify({'success': False, 'msg': '当前状态无法取消'})
    db.execute(
        "UPDATE business_venue_bookings SET status='cancelled', updated_at=NOW() WHERE id=%s",
        [booking_id]
    )
    return jsonify({'success': True, 'msg': '预约已取消'})

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
    if booking.get('status') not in ('pending', 'confirmed'):
    return jsonify({'success': False, 'msg': '该预约状态不可支付'})
    try:
    db.execute(
    "UPDATE business_venue_bookings SET pay_status='paid', status='confirmed', updated_at=NOW() WHERE id=%s",
    [booking_id]
    )
    # 积分奖励（支付成功送积分）
    try:
    reward = max(1, int(float(booking.get('total_price') or 0) / 10))  # 每10元1积分
    db.execute(
    "UPDATE business_members SET points=points+%s, total_points=total_points+%s WHERE user_id=%s",
    [reward, reward, user['user_id']]
    )
    db.execute(
    "INSERT INTO business_points_log (user_id, log_type, points, balance_after, description) "
    "SELECT %s, 'earn', %s, points, %s FROM business_members WHERE user_id=%s",
    [user['user_id'], reward, f'场地预约支付积分', user['user_id']]
    )
    except Exception as pe:
    logging.warning(f"支付积分奖励失败: {pe}")
    # 发送支付成功通知
    try:
    notification.send_notification(
    user['user_id'], '预约支付成功',
    f"您的场地预约已支付成功，核销码：{booking.get('verify_code','')}",
    notify_type='order', ref_id=str(booking_id), ref_type='booking'
    )
    return jsonify({'success': True, 'msg': '支付成功'})
    return jsonify({'success': False, 'msg': '支付失败，请重试'})

# ============ 评价功能 ============

@app.route('/api/user/reviews', methods=['GET'])
@require_login
def get_my_reviews(user):
    """获取我的评价列表"""
    from business_common.review_service import get_review_service
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    result = get_review_service().get_user_reviews(user['user_id'], page, page_size)
    return jsonify({'success': True, 'data': result})

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    """获取评价列表（公开接口，用于展示）"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 10)), 50)
    target_type = request.args.get('target_type')
    target_id = request.args.get('target_id')

    where = "deleted=0"
    params = []
    if target_type:
    where += " AND target_type=%s"; params.append(target_type)
    if target_id:
    where += " AND target_id=%s"; params.append(target_id)

    try:
    total = db.get_total("SELECT COUNT(*) FROM business_reviews WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
    """SELECT id, user_name, target_type, target_id, target_name, rating, content, images,
    is_anonymous, created_at
    FROM business_reviews WHERE """ + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
    params + [page_size, offset]
    )
    # P1增强：解析图片JSON
    for item in items or []:
    if item.get('images'):
    try:
    item['images_list'] = json.loads(item['images'])
    except:
    item['images_list'] = []
    else:
    item['images_list'] = []
    return jsonify({'success': True, 'data': {
    'items': items or [],
    'total': total,
    'page': page,
    'page_size': page_size,
    'pages': (total + page_size - 1) // page_size if total else 0
    }})
    return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}})

@app.route('/api/user/reviews', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=30, window_seconds=60)  # 限流：每分钟最多30次评价
def create_review(user):
    """提交评价"""
    data = request.get_json() or {}
    target_type = data.get('target_type')
    target_id = data.get('target_id')
    target_name = data.get('target_name', '')
    rating = int(data.get('rating', 0))
    content = data.get('content', '').strip()
    images = data.get('images', [])
    is_anonymous = int(data.get('is_anonymous', 0))

    # 参数校验
    if target_type not in ('venue', 'order', 'service', 'shop', 'product'):
    return jsonify({'success': False, 'msg': '评价对象类型无效'})
    if not target_id:
    return jsonify({'success': False, 'msg': '评价对象ID不能为空'})
    if rating < 1 or rating > 5:
    return jsonify({'success': False, 'msg': '评分必须在1-5之间'})
    if len(content) > 500:
    return jsonify({'success': False, 'msg': '评价内容不能超过500字'})

    # 检查是否已评价
    existing = db.get_one(
    "SELECT id FROM business_reviews WHERE user_id=%s AND target_type=%s AND target_id=%s AND deleted=0",
    [user['user_id'], target_type, str(target_id)]
    )
    if existing:
    return jsonify({'success': False, 'msg': '您已评价过此订单/场地，不能重复评价'})

    # V23.0: 内容安全审核（自动调用content_moderation模块）
    from business_common.content_moderation import ContentModeration
    mod_result = ContentModeration.moderate_text(content)
    moderation_status = 'approved'
    if mod_result['risk_level'] >= 3:  # 高风险直接拒绝
    return jsonify({'success': False, 'msg': '评价内容包含违规信息，请修改后重新提交'})
    elif mod_result['risk_level'] >= 2:  # 中风险标记为待人工审核
    moderation_status = 'pending_review'
    moderation_json = json.dumps(mod_result, ensure_ascii=False)

    user_name = '匿名用户' if is_anonymous else user.get('user_name', '')

    try:
    review_id = db.execute(
    """INSERT INTO business_reviews
    (user_id, user_name, target_type, target_id, target_name, rating, content, images, is_anonymous, ec_id, project_id, moderation_status, moderation_result)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
    [user['user_id'], user_name, target_type, target_id,
    target_name, rating, content, json.dumps(images), is_anonymous,
    user.get('ec_id'), user.get('project_id'), moderation_status, moderation_json]
    )
    
    reward_result = {'success': True, 'points': 0, 'growth': 0}
    growth_task_result = {'success': True, 'completed_tasks': []}
    
    try:
    from business_common.review_reward_service import review_reward_service
    reward_result = review_reward_service.grant_reward(
    user['user_id'],
    review_id,
    int(target_id) if target_type == 'order' else 0,
    rating,
    user.get('ec_id'),
    user.get('project_id')
    )
    except Exception as reward_error:
    logging.warning(f"评价奖励发放失败: {reward_error}")
    
    try:
    from business_common.growth_task_service import growth_task_service
    growth_task_result = growth_task_service.on_review(
    user['user_id'],
    user.get('ec_id'),
    user.get('project_id')
    ) or {'success': True, 'completed_tasks': []}
    except Exception as growth_error:
    logging.warning(f"评价成长任务更新失败: {growth_error}")
    
    # P0修复：提交评价后自动更新目标对象的评分缓存
    if target_type in ('venue', 'shop'):
    try:
    # 计算新的平均评分和评价数量
    stats = db.get_one("""
    SELECT ROUND(AVG(rating), 1) as avg_rating, COUNT(*) as review_count 
    FROM business_reviews 
    WHERE target_type=%s AND target_id=%s AND deleted=0
    """, [target_type, target_id])
    if stats:
    avg_rating = float(stats.get('avg_rating') or 0)
    review_count = int(stats.get('review_count') or 0)
    # 更新对应表的评分缓存字段
    if target_type == 'venue':
    db.execute(
    "UPDATE business_venues SET avg_rating=%s, review_count=%s WHERE id=%s",
    [avg_rating, review_count, target_id]
    )
    elif target_type == 'shop':
    db.execute(
    "UPDATE business_shops SET avg_rating=%s, review_count=%s WHERE id=%s",
    [avg_rating, review_count, target_id]
    )
    reward_parts = []
    if reward_result.get('points', 0) > 0:
    reward_parts.append(f"{reward_result['points']}积分")
    if reward_result.get('growth', 0) > 0:
    reward_parts.append(f"{reward_result['growth']}成长值")
    reward_msg = f"，获得{' + '.join(reward_parts)}" if reward_parts else ''
    completed_tasks = growth_task_result.get('completed_tasks') or []
    task_msg = f"，同步完成{len(completed_tasks)}项成长任务" if completed_tasks else ''
    
    return jsonify({
    'success': True,
    'msg': f'评价提交成功{reward_msg}{task_msg}',
    'data': {
    'review_id': review_id,
    'reward': reward_result,
    'growth_tasks': growth_task_result,
    'moderation_status': moderation_status
    }
    })
    return jsonify({'success': False, 'msg': '评价提交失败'})

@app.route('/api/user/reviews/<int:review_id>/append', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)  # 限流：每分钟最多10次追评
def append_review(user, review_id):
    """追加评价（追评）"""
    data = request.get_json() or {}
    append_content = data.get('append_content', '').strip()
    append_images = data.get('append_images', [])

    if not append_content and not append_images:
    return jsonify({'success': False, 'msg': '追评内容不能为空'})
    if len(append_content) > 300:
    return jsonify({'success': False, 'msg': '追评内容不能超过300字'})

    # 验证评价归属
    review = db.get_one(
    "SELECT id FROM business_reviews WHERE id=%s AND user_id=%s AND deleted=0",
    [review_id, user['user_id']]
    )
    if not review:
    return jsonify({'success': False, 'msg': '评价不存在或无权操作'})

    # 检查是否已追评
    existing = db.get_one(
    "SELECT id FROM business_reviews WHERE id=%s AND append_content IS NOT NULL AND append_content != ''",
    [review_id]
    )
    if existing:
    return jsonify({'success': False, 'msg': '您已追评过，不能重复追评'})

    # V23.0: 追评内容审核
    from business_common.content_moderation import ContentModeration
    mod_result = ContentModeration.moderate_text(append_content)
    if mod_result['risk_level'] >= 3:
    return jsonify({'success': False, 'msg': '追评内容包含违规信息，请修改后重新提交'})

    try:
    db.execute(
    """UPDATE business_reviews 
    SET append_content=%s, append_images=%s, append_created_at=NOW(),
    append_moderation_status=%s, append_moderation_result=%s
    WHERE id=%s""",
    [append_content, json.dumps(append_images), 
    'pending_review' if mod_result['risk_level'] >= 2 else 'approved',
    json.dumps(mod_result, ensure_ascii=False), review_id]
    )
    return jsonify({'success': True, 'msg': '追评成功'})
    return jsonify({'success': False, 'msg': '追评失败'})

@app.route('/api/reviews/stats', methods=['GET'])
def get_review_stats():
    """获取评价统计"""
    from business_common.review_service import get_review_service
    target_type = request.args.get('target_type', 'product')
    target_id = int(request.args.get('target_id', 0))
    stats = get_review_service().get_review_stats(target_type, target_id)
    return jsonify({'success': True, 'data': stats})

@app.route('/api/user/search/history', methods=['GET'])
@require_login
def get_user_search_history(user):
    """获取搜索历史"""
    from business_common.search_history_service import get_search_history_service
    return jsonify({'success': True, 'data': {'items': get_search_history_service().get_history(user['user_id'])}})

@app.route('/api/user/search/history', methods=['POST'])
@require_login
def add_search_history(user):
def add_search_history(user):
    """添加搜索历史"""
    from business_common.search_history_service import get_search_history_service
    data = request.get_json() or {}
    keyword = (data.get('keyword') or '').strip()
    if not keyword or len(keyword) < 2:
    return jsonify({'success': False, 'msg': '关键词太短'})
    svc = get_search_history_service()
    return jsonify(svc.add_history(user['user_id'], keyword, user.get('ec_id'), user.get('project_id')))

@app.route('/api/user/addresses/<int:addr_id>', methods=['DELETE'])
@require_login
def delete_address(user, addr_id):
    """删除收货地址"""
    from business_common.address_service import get_address_service
    addr_service = get_address_service()
    return jsonify(addr_service.delete_address(int(addr_id), user['user_id']))

@app.route('/api/user/addresses/<int:addr_id>/default', methods=['POST'])
@require_login
def set_default_address(user, addr_id):
    """设置默认收货地址"""
    from business_common.address_service import get_address_service
    addr_service = get_address_service()
    return jsonify(addr_service.set_default(int(addr_id), user['user_id']))

@app.route('/api/user/addresses/<int:addr_id>', methods=['DELETE'])
@require_login
def delete_address(user, addr_id):
    """删除收货地址"""
    uid = user['user_id']
    
    # 验证地址归属
    check = db.get_one(
    "SELECT id FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
    [addr_id, uid]
    )
    if not check:
    return jsonify({'success': False, 'msg': '地址不存在'})
    
    try:
    db.execute(
    "UPDATE business_user_addresses SET deleted=1, updated_at=NOW() WHERE id=%s AND user_id=%s",
    [addr_id, uid]
def confirm_order(user, order_id):
    """确认收货"""
    order = db.get_one(
        "SELECT id FROM business_orders WHERE id=%s AND user_id=%s AND order_status='shipped' AND deleted=0",
        [order_id, user['user_id']]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在或状态不允许确认'})
    db.execute(
        "UPDATE business_orders SET order_status='completed', completed_at=NOW(), updated_at=NOW() WHERE id=%s",
        [order_id]
    )
    return jsonify({'success': True, 'msg': '已确认收货'})

@app.route('/api/user/products/categories', methods=['GET'])
def get_product_categories():
    """获取商品分类"""
    categories = db.get_all(
        "SELECT id, name, parent_id, icon, sort_order FROM business_product_categories "
        "WHERE status=1 AND deleted=0 ORDER BY sort_order ASC, id ASC"
    ) or []
    return jsonify({'success': True, 'data': {'items': categories}})

@app.route('/api/user/checkin', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=1, window_seconds=10)
def daily_checkin(user):
    """V27.0: 每日签到，支持连续签到阶梯奖励配置"""
    uid = user['user_id']
    today = time.strftime('%Y-%m-%d')
    yesterday = time.strftime('%Y-%m-%d', time.localtime(time.time() - 86400))

    try:
    conn = db.get_db()
    cursor = conn.cursor()
    conn.begin()

    # V20.0: 使用FOR UPDATE行锁防止并发签到
    # 检查今天是否已签到（加锁）
    cursor.execute(
    "SELECT id FROM business_checkin_logs WHERE user_id=%s AND checkin_date=%s FOR UPDATE",
    [uid, today]
    )
    checkin = cursor.fetchone()
    if checkin:
    conn.rollback()
    return jsonify({'success': False, 'msg': '今天已经签到过了'})

    # 查询连续签到天数（加锁）
    cursor.execute(
    "SELECT id, continuous_days FROM business_checkin_logs WHERE user_id=%s AND checkin_date=%s FOR UPDATE",
    [uid, yesterday]
    )
    yesterday_checkin = cursor.fetchone()
    continuous = (yesterday_checkin[1] or 0) + 1 if yesterday_checkin else 1

    # V27.0: 从配置表获取奖励规则
    try:
    cursor.execute("""
    SELECT streak_days, base_points, bonus_points, bonus_type, bonus_threshold, description
    FROM business_checkin_rewards_config 
    WHERE status=1 AND streak_days <= %s 
    ORDER BY streak_days DESC LIMIT 1
    """, [continuous])
    reward_config = cursor.fetchone()
    except Exception as config_e:
    logging.warning(f"获取签到奖励配置失败，使用默认规则: {config_e}")
    reward_config = None
    
    if reward_config:
    base_points = reward_config[1] or 5
    bonus_points = reward_config[2] or 0
    reward_description = reward_config[5] or ''
    else:
    # 默认规则：连续签到奖励递增，最多7天循环
    base_points = min(continuous, 7)  # 1~7天分别奖励1~7积分
    bonus_points = 10 if continuous >= 7 else 0
    reward_description = f'连续签到{continuous}天奖励' if continuous >= 7 else ''
    
    total_reward = base_points + bonus_points

    # 锁定会员记录防止并发修改积分
    cursor.execute(
    "SELECT points FROM business_members WHERE user_id=%s FOR UPDATE",
    [uid]
    )

    # 写入签到记录
    cursor.execute(
    "INSERT INTO business_checkin_logs (user_id, checkin_date, continuous_days, reward_points) VALUES (%s,%s,%s,%s)",
    [uid, today, continuous, total_reward]
    )

    # 增加用户积分，同步更新连续签到天数
    cursor.execute(
    "UPDATE business_members SET points=points+%s, total_points=total_points+%s, checkin_streak=%s, last_checkin_date=%s WHERE user_id=%s",
    [total_reward, total_reward, continuous, today, uid]
    )

    # 写入积分日志
    bonus_desc = f' + {bonus_points}积分额外奖励' if bonus_points > 0 else ''
    cursor.execute(
    "INSERT INTO business_points_log (user_id, log_type, points, balance_after, description) "
    "SELECT %s, 'earn', %s, points, %s FROM business_members WHERE user_id=%s",
    [uid, total_reward, f'每日签到(连续{continuous}天): {base_points}积分{bonus_desc}', uid]
    )

    # V27.0: 检查并解锁成就
    check_and_unlock_achievement(cursor, conn, uid, 'checkin_days', continuous)

    conn.commit()

    # 清除缓存
    from business_common.cache_service import cache_delete
    cache_delete(f"user_stats_{uid}")
    cache_delete(f"user_profile_{uid}")

    # V27.0: 发送签到奖励通知
    try:
    notification.send_notification(
    user_id=uid,
    title='签到奖励到账',
    content=f"恭喜完成今日签到！获得 {total_reward} 积分，当前连续签到 {continuous} 天。",
    notify_type='checkin',
    ref_id=str(uid),
    ref_type='checkin'
    )
    except Exception as notif_e:
    logging.warning(f"发送签到通知失败: {notif_e}")

    return jsonify({'success': True, 'msg': '签到成功', 'data': {
    'continuous_days': continuous,
    'reward_points': total_reward,
    'base_points': base_points,
    'bonus_points': bonus_points,
    'description': reward_description
    }})
    except Exception as e:
    try:
    conn.rollback()
    logging.error(f"签到失败: {e}")
    return jsonify({'success': False, 'msg': '签到失败，请稍后重试'})
    finally:
    try:
    cursor.close()
    conn.close()

def check_and_unlock_achievement(cursor, conn, user_id, condition_type, condition_value):
    """V27.0: 检查并解锁成就"""
    try:
    # 查询符合条件的成就
    cursor.execute("""
    SELECT id, code, name, points_reward 
    FROM business_achievements 
    WHERE status=1 AND condition_type=%s AND condition_value <= %s
    """, [condition_type, condition_value])
    
    achievements = cursor.fetchall()
    for ach in achievements:
    ach_id, ach_code, ach_name, ach_points = ach
    
    # 检查是否已解锁
    cursor.execute(
    "SELECT id FROM business_user_achievements WHERE user_id=%s AND achievement_code=%s",
    [user_id, ach_code]
    )
    if cursor.fetchone():
    continue  # 已解锁，跳过
    
    # 解锁成就
    cursor.execute("""
    INSERT INTO business_user_achievements 
    (user_id, achievement_code, achievement_name, badge_icon, points_earned)
    VALUES (%s, %s, %s, %s, %s)
    """, [user_id, ach_code, ach_name, f'badge_{ach_code}', ach_points])
    
    # 发放积分奖励
    if ach_points > 0:
    cursor.execute(
    "UPDATE business_members SET points=points+%s, total_points=total_points+%s WHERE user_id=%s",
    [ach_points, ach_points, user_id]
    )
    cursor.execute(
    "INSERT INTO business_points_log (user_id, log_type, points, balance_after, description) "
    "SELECT %s, 'earn', %s, points, %s FROM business_members WHERE user_id=%s",
    [user_id, ach_points, f'成就解锁: {ach_name}', user_id]
    )
    
    logging.info(f"用户 {user_id} 解锁成就: {ach_name}")
@app.route('/api/user/checkin/status', methods=['GET'])
@require_login
def get_checkin_status(user):
    """获取签到状态"""
    from business_common.checkin_service import get_checkin_service
    checkin_service = get_checkin_service()
    result = checkin_service.get_checkin_status(
    user_id=user['user_id'],
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/checkin/rank', methods=['GET'])
@require_login
def get_checkin_rank(user):
    """获取签到排名"""
    from business_common.checkin_service import get_checkin_service
    import time
    today = time.strftime('%Y-%m-%d')
    rank = get_checkin_service().get_checkin_rank(user['user_id'], today)
    return jsonify({'success': True, 'data': {'rank': rank, 'date': today}})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# ============ V18.0 营销促销系统 ============

@app.route('/api/user/promotions', methods=['GET'])
@require_login
def get_active_promotions(user):
    """获取当前有效的营销活动列表"""
    from datetime import datetime
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    promo_type = request.args.get('type', '')  # seckill / full_reduce / discount / all

    where = "status='active' AND start_time <= NOW() AND end_time >= NOW()"
    params = []
    if ec_id:
    where += " AND (ec_id=%s OR ec_id IS NULL)"; params.append(ec_id)
    if project_id:
    where += " AND (project_id=%s OR project_id IS NULL)"; params.append(project_id)
    if promo_type and promo_type != 'all':
    where += " AND promo_type=%s"; params.append(promo_type)

    try:
    promotions = db.get_all(
    f"""SELECT id, promo_name, promo_type, description, banner_image,
    start_time, end_time, promo_type,
    min_amount, reduce_amount, discount_rate, seckill_price,
    total_stock, apply_type, apply_ids, per_limit
    FROM business_promotions WHERE {where}
    ORDER BY CASE promo_type WHEN 'seckill' THEN 1 WHEN 'full_reduce' THEN 2
    WHEN 'discount' THEN 3 ELSE 4 END, start_time DESC""",
    params
    )
    result = []
    for promo in (promotions or []):
    # 查询用户已使用次数
    used = db.get_total(
    "SELECT COALESCE(use_count,0) FROM business_promotion_users WHERE promotion_id=%s AND user_id=%s",
    [promo['id'], user['user_id']]
    ) or 0
    promo['user_used_count'] = used
    per_limit = promo.get('per_limit', 0)
    promo['can_use'] = (per_limit == 0 or used < per_limit)
    # 秒杀活动剩余库存
    if promo.get('promo_type') == 'seckill':
    stock = db.get_total(
    "SELECT total_stock FROM business_promotions WHERE id=%s",
    [promo['id']]
    )
    promo['remaining_stock'] = max(0, stock or 0)
    try:
    promo['apply_ids'] = json.loads(promo.get('apply_ids') or '[]')
    except Exception:
    promo['apply_ids'] = []
    result.append(promo)
    return jsonify({'success': True, 'data': result})
    return jsonify({'success': True, 'data': []})

@app.route('/api/user/promotions/<int:promo_id>', methods=['GET'])
@require_login
def get_promotion_detail(user, promo_id):
    """获取营销活动详情"""
    ec_id = user.get('ec_id')
    try:
    promo = db.get_one(
    """SELECT * FROM business_promotions WHERE id=%s AND status='active'
    AND start_time <= NOW() AND end_time >= NOW()""",
    [promo_id]
    )
    if not promo:
    return jsonify({'success': False, 'msg': '活动不存在或已结束'})
    # 用户参与状态
    used = db.get_one(
    "SELECT use_count FROM business_promotion_users WHERE promotion_id=%s AND user_id=%s",
    [promo_id, user['user_id']]
    )
    promo['user_used_count'] = (used or {}).get('use_count', 0)
    per_limit = promo.get('per_limit', 0)
    promo['can_use'] = (per_limit == 0 or promo['user_used_count'] < per_limit)
    try:
    promo['apply_ids'] = json.loads(promo.get('apply_ids') or '[]')
    except Exception:
    promo['apply_ids'] = []
    return jsonify({'success': True, 'data': promo})
    return jsonify({'success': False, 'msg': '查询失败'})

@app.route('/api/user/promotions/calc', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=30, window_seconds=60)
def calc_promotion_price(user):
    """V18.0：计算促销优惠价格（下单前预计算）"""
    data = request.get_json() or {}
    promo_id = data.get('promo_id')
    original_amount = float(data.get('amount', 0))

    if not promo_id or original_amount <= 0:
    return jsonify({'success': False, 'msg': '参数不完整'})

    try:
    from business_common.member_level import PromotionService
    promo = db.get_one(
    "SELECT * FROM business_promotions WHERE id=%s AND status='active' AND start_time<=NOW() AND end_time>=NOW()",
    [promo_id]
    )
    if not promo:
    return jsonify({'success': False, 'msg': '活动不存在或已结束'})

    # 检查用户限制
    used = db.get_total(
    "SELECT COALESCE(use_count,0) FROM business_promotion_users WHERE promotion_id=%s AND user_id=%s",
    [promo_id, user['user_id']]
    ) or 0
    per_limit = promo.get('per_limit', 0)
    if per_limit > 0 and used >= per_limit:
    return jsonify({'success': False, 'msg': f'您已达到本活动使用上限({per_limit}次)'})

    final_amount, saved = PromotionService.calculate_promo_discount(promo, original_amount)

    return jsonify({'success': True, 'data': {
    'promo_id': promo_id,
    'promo_name': promo.get('promo_name'),
    'promo_type': promo.get('promo_type'),
    'original_amount': original_amount,
    'final_amount': round(final_amount, 2),
    'saved_amount': round(saved, 2)
    }})
    return jsonify({'success': False, 'msg': '计算失败'})

# ============ 秒杀活动 V21.0新增 ============

@app.route('/api/seckill/activity', methods=['GET'])
@require_login
def get_seckill_activity(user):
    """获取当前秒杀活动"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
    from business_common.seckill_service import SeckillService
    activity = SeckillService.get_seckill_activity(
    promo_type='seckill',
    ec_id=ec_id,
    project_id=project_id
    )
    
    if not activity:
    return jsonify({'success': True, 'data': None, 'msg': '暂无秒杀活动'})
    
    # 查询秒杀商品信息
    apply_ids = json.loads(activity.get('apply_ids', '[]'))
    if apply_ids:
    product = db.get_one(
    "SELECT id, product_name, price, original_price, images, stock FROM business_products WHERE id=%s",
    [apply_ids[0]]
    )
    if product:
    activity['product'] = product
    # 设置原价（如果未设置）
    if not activity.get('original_price'):
    activity['original_price'] = product.get('price')
    
    # 查询已售数量和剩余库存
    sold = db.get_total(
    "SELECT COALESCE(SUM(quantity), 0) FROM business_seckill_orders WHERE activity_id=%s AND status != 'cancelled'",
    [activity['id']]
    ) or 0
    activity['sold_count'] = sold
    activity['remaining_stock'] = max(0, (activity.get('total_stock') or 0) - sold)
    
    # 用户已购数量
    my_bought = db.get_total(
    "SELECT COALESCE(SUM(quantity), 0) FROM business_seckill_orders WHERE activity_id=%s AND user_id=%s AND status != 'cancelled'",
    [activity['id'], user['user_id']]
    ) or 0
    activity['my_bought'] = my_bought
    per_limit = activity.get('per_limit', 1)
    activity['can_buy'] = per_limit == 0 or my_bought < per_limit
    activity['remaining_buy'] = max(0, per_limit - my_bought) if per_limit > 0 else 999
    
    return jsonify({'success': True, 'data': activity})
    return jsonify({'success': False, 'msg': '获取失败'})

@app.route('/api/seckill/orders', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=5, window_seconds=60)  # 秒杀限流：每分钟最多5次
def create_seckill_order(user):
    """创建秒杀订单"""
    data = request.get_json() or {}
    activity_id = data.get('activity_id')
    quantity = int(data.get('quantity', 1))
    address_id = data.get('address_id')
    
    if not activity_id:
    return jsonify({'success': False, 'msg': '请选择秒杀活动'})
    
    if quantity < 1 or quantity > 5:
    return jsonify({'success': False, 'msg': '购买数量需在1-5之间'})
    
    try:
    from business_common.seckill_service import SeckillService
    
    result = SeckillService.create_seckill_order(
    activity_id=activity_id,
    user_id=user['user_id'],
    user_name=user.get('user_name', ''),
    user_phone=user.get('phone', ''),
    quantity=quantity,
    address_id=address_id,
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )
    
    if result.get('success'):
    return jsonify({
    'success': True,
    'msg': '秒杀下单成功',
    'data': {
    'order_no': result.get('order_no'),
    'order_id': result.get('order_id'),
    'total_amount': result.get('total_amount'),
    'discount_amount': result.get('discount_amount')
    }
    })
    else:
    return jsonify({'success': False, 'msg': result.get('msg', '下单失败')})
    return jsonify({'success': False, 'msg': '秒杀下单失败，请稍后重试'})

@app.route('/api/seckill/orders', methods=['GET'])
@require_login
def get_seckill_orders(user):
    """获取用户的秒杀订单"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    try:
    from business_common.seckill_service import SeckillService
    result = SeckillService.get_user_seckill_orders(
    user_id=user['user_id'],
    page=page,
    page_size=page_size
    )
    return jsonify({'success': True, 'data': result})
    return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

# ============ 评价功能 V21.0增强 ============

@app.route('/api/user/reviews', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def create_review_user(user):
    """提交评价"""
    data = request.get_json() or {}
    target_type = data.get('target_type')  # order / shop / product / venue
    target_id = data.get('target_id')
    rating = int(data.get('rating', 5))
    content = (data.get('content') or '').strip()
    images_raw = data.get('images', [])
    
    if not target_type or not target_id:
    return jsonify({'success': False, 'msg': '参数不完整'})
    
    if rating < 1 or rating > 5:
    return jsonify({'success': False, 'msg': '评分需在1-5之间'})
    
    if len(content) > 500:
    return jsonify({'success': False, 'msg': '评价内容不能超过500字'})
    
    # 图片校验
    MAX_IMAGES = 5
    valid_images = []
    for img in (images_raw if isinstance(images_raw, list) else []):
    if isinstance(img, str) and (img.startswith('data:image/') or img.startswith('http')):
    valid_images.append(img)
    if len(valid_images) > MAX_IMAGES:
    return jsonify({'success': False, 'msg': f'最多上传{MAX_IMAGES}张图片'})
    
    try:
    # 检查是否已评价
    existing = db.get_one(
    "SELECT id FROM business_reviews WHERE user_id=%s AND target_type=%s AND target_id=%s AND deleted=0",
    [user['user_id'], target_type, str(target_id)]
    )
    if existing:
    return jsonify({'success': False, 'msg': '您已评价过该订单'})
    
    # 根据类型获取关联信息
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    if target_type == 'order':
    # 验证订单归属
    order = db.get_one(
    "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND order_status IN ('paid','completed')",
    [target_id, user['user_id']]
    )
    if not order:
    return jsonify({'success': False, 'msg': '订单不存在或状态不允许评价'})
    ec_id = order.get('ec_id')
    project_id = order.get('project_id')
    
    images_json = json.dumps(valid_images)
    
    db.execute("""
    INSERT INTO business_reviews
    (target_type, target_id, user_id, user_name, rating, content, images, ec_id, project_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, [target_type, str(target_id), user['user_id'], user.get('user_name', ''),
    rating, content, images_json, ec_id, project_id])
    
    # 更新关联统计
    _update_review_stats(target_type, target_id)
    
    # 发送通知给商家
    from business_common.notification import send_notification
    send_notification(
    user_id='staff',
    title='新评价提醒',
    content=f"用户 {user.get('user_name', '')} 提交了 {rating} 星评价",
    notify_type='review',
    ec_id=ec_id,
    project_id=project_id
    )
    
    return jsonify({'success': True, 'msg': '评价提交成功'})
    return jsonify({'success': False, 'msg': '评价提交失败'})

def _update_review_stats(target_type, target_id):
    """更新评价统计"""
    from business_common.review_service import get_review_service
    review_service = get_review_service()
    review_service.update_target_rating(target_type, target_id)

@app.route('/api/user/reviews', methods=['GET'])
@require_login
def get_my_reviews_user(user):
    """获取我的评价列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    offset = (page - 1) * page_size
    
    total = db.get_total(
    "SELECT COUNT(*) FROM business_reviews WHERE user_id=%s AND deleted=0",
    [user['user_id']]
    )
    
    reviews = db.get_all("""
    SELECT r.*, 
    CASE r.target_type
    WHEN 'order' THEN (SELECT order_no FROM business_orders WHERE id=r.target_id)
    WHEN 'shop' THEN (SELECT shop_name FROM business_shops WHERE id=r.target_id)
    WHEN 'product' THEN (SELECT product_name FROM business_products WHERE id=r.target_id)
    WHEN 'venue' THEN (SELECT venue_name FROM business_venues WHERE id=r.target_id)
    ELSE '未知'
    END as target_name
    FROM business_reviews r
    WHERE r.user_id=%s AND r.deleted=0
    ORDER BY r.created_at DESC
    LIMIT %s OFFSET %s
    """, [user['user_id'], page_size, offset])
    
    return jsonify({'success': True, 'data': {
    'items': reviews or [],
    'total': total,
    'page': page,
    'page_size': page_size
    }})

@app.route('/api/user/reviews/<int:review_id>', methods=['DELETE'])
@require_login
def delete_review(user, review_id):
    """删除评价"""
    affected = db.execute(
        "UPDATE business_reviews SET deleted=1, updated_at=NOW() WHERE id=%s AND user_id=%s",
        [review_id, user['user_id']]
    )
    return jsonify({'success': affected > 0, 'msg': '已删除' if affected > 0 else '评价不存在'})

@app.route('/api/user/member/benefits', methods=['GET'])
@require_login
def get_member_benefits(user):
    """获取会员权益"""
    member = db.get_one(
        "SELECT m.*,l.level_name,l.discount_rate,l.privileges "
        "FROM business_members m LEFT JOIN business_member_levels l ON m.member_level=l.level_code "
        "WHERE m.user_id=%s",
        [user['user_id']]
    )
    if not member:
        return jsonify({'success': False, 'msg': '未找到会员信息'})
    return jsonify({'success': True, 'data': member})

@app.route('/api/user/orders/<int:order_id>/logistics', methods=['GET'])
@require_login
def get_order_logistics(user, order_id):
    """获取订单物流"""
    order = db.get_one(
        "SELECT tracking_no,logistics_company FROM business_orders WHERE id=%s AND user_id=%s",
        [order_id, user['user_id']]
    )
    if not order or not order.get('tracking_no'):
        return jsonify({'success': False, 'msg': '暂无物流信息'})
    return jsonify({'success': True, 'data': order})

@app.route('/api/user/logistics/companies', methods=['GET'])
def get_logistics_companies():
    """获取支持的物流公司列表"""
    return jsonify({
    'success': True,
    'data': logistics.get_logistics_companies()
    })

@app.route('/api/user/logistics/query', methods=['GET'])
def query_logistics_by_no():
    """根据快递单号查询物流 (用于扫码查件)"""
    tracking_no = request.args.get('tracking_no', '').strip()
    company_code = request.args.get('company_code', '').strip()

    if not tracking_no:
    return jsonify({'success': False, 'msg': '请输入快递单号'})

    result = logistics.query_logistics(tracking_no, company_code)
    return jsonify(result)

# ============ V42.0 商品多规格属性 ============

@app.route('/api/user/products/<int:product_id>/specs', methods=['GET'])
def get_product_specs(product_id):
    """V42.0: 获取商品规格组及SKU矩阵"""
    groups = spec_service.get_spec_groups(product_id)
    matrix = spec_service.generate_sku_matrix(product_id)
    price_range = spec_service.get_sku_price_range(product_id)
    return jsonify({
    'success': True,
    'data': {
    'groups': groups,
    'matrix': matrix,
    'price_range': price_range
    }
    })

@app.route('/api/user/products/<int:product_id>/specs', methods=['POST'])
@require_login
def create_product_spec(user, product_id):
    """V42.0: 添加商品规格组（管理员/商家）"""
    data = request.get_json() or {}
    spec_name = data.get('spec_name', '').strip()
    values = data.get('values', [])

    if not spec_name:
    return jsonify({'success': False, 'msg': '规格名称不能为空'})

    result = spec_service.add_spec_group(product_id, spec_name, values)
    return jsonify(result)

@app.route('/api/user/products/<int:product_id>/sku/create', methods=['POST'])
@require_login
def create_sku(user, product_id):
    """V42.0: 创建或更新SKU"""
    data = request.get_json() or {}
    specs = data.get('specs', {})
    price = float(data.get('price', 0))
    stock = int(data.get('stock', 0))
    sku_code = data.get('sku_code')

    result = spec_service.create_or_update_sku(product_id, specs, price, stock, sku_code)
    return jsonify(result)

@app.route('/api/user/skus/<int:sku_id>', methods=['PUT'])
@require_login
def update_sku(user, sku_id):
    """V42.0: 更新SKU价格/库存"""
    data = request.get_json() or {}
    price = data.get('price')
    stock = data.get('stock')

    result = spec_service.update_sku_price_and_stock(sku_id, price, stock)
    return jsonify(result)

# ============ V42.0 商品问答系统 ============

@app.route('/api/user/products/<int:product_id>/qa', methods=['GET'])
def get_product_qa(product_id):
    """V42.0: 获取商品问答列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)

    result = product_qa.get_product_qa_list(product_id, page, page_size)
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/products/<int:product_id>/qa/stats', methods=['GET'])
def get_product_qa_stats(product_id):
    """V42.0: 获取商品问答统计"""
    stats = product_qa.get_product_qa_stats(product_id)
    return jsonify({'success': True, 'data': stats})

@app.route('/api/user/qa/<int:qa_id>', methods=['GET'])
@require_login
def get_qa_detail(user, qa_id):
    """V42.0: 获取问答详情"""
    detail = product_qa.get_qa_detail(qa_id, user['user_id'])
    if not detail:
    return jsonify({'success': False, 'msg': '问答不存在'})
    return jsonify({'success': True, 'data': detail})

@app.route('/api/user/qa', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=20, window_seconds=60)
def create_question(user):
    """V42.0: 提交商品提问"""
    data = request.get_json() or {}
    product_id = data.get('product_id')
    question = data.get('question', '').strip()

    if not product_id:
    return jsonify({'success': False, 'msg': '请指定商品'})
    if not question:
    return jsonify({'success': False, 'msg': '请填写问题内容'})

    result = product_qa.create_question(
    user_id=user['user_id'],
    user_name=user.get('user_name', '匿名用户'),
    product_id=product_id,
    question=question,
    ec_id=user.get('ec_id', 1),
    project_id=user.get('project_id', 1)
    )
    return jsonify(result)

@app.route('/api/user/qa/<int:qa_id>/answer', methods=['POST'])
@require_login
def answer_question(user, qa_id):
    """V42.0: 回复问答（商家回复或追问追问回复）"""
    data = request.get_json() or {}
    answer = data.get('answer', '').strip()

    if not answer:
    return jsonify({'success': False, 'msg': '请填写回复内容'})

    result = product_qa.answer_question(
    question_id=qa_id,
    answer=answer,
    replier_id=user.get('user_id'),
    replier_name=user.get('user_name', '商家'),
    is_staff=(user.get('staff_id') is not None)
    )
    return jsonify(result)

@app.route('/api/user/qa/<int:qa_id>/followup', methods=['POST'])
@require_login
def add_followup(user, qa_id):
    """V42.0: 追加追问"""
    data = request.get_json() or {}
    content = data.get('content', '').strip()

    if not content:
    return jsonify({'success': False, 'msg': '请填写追问内容'})

    result = product_qa.add_followup(
    question_id=qa_id,
    user_id=user['user_id'],
    user_name=user.get('user_name', '匿名用户'),
    content=content
    )
    return jsonify(result)

@app.route('/api/user/qa/<int:qa_id>/close', methods=['POST'])
@require_login
def close_qa(user, qa_id):
    """V42.0: 关闭问答"""
    result = product_qa.close_question(qa_id, user['user_id'])
    return jsonify(result)

@app.route('/api/user/qa/my', methods=['GET'])
@require_login
def get_my_questions(user):
    """V42.0: 获取我的提问列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    result = product_qa.get_user_questions(user['user_id'], page, page_size)
    return jsonify({'success': True, 'data': result})

# ============ V42.0 积分商城 ============

@app.route('/api/user/points-mall', methods=['GET'])
@require_login
def get_points_mall(user):
    """V42.0: 获取积分商品列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    category = request.args.get('category')
    status = request.args.get('status', 'active')

    result = PointsMallService.get_products(
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id'),
    page=page,
    page_size=page_size,
    category=category,
    status=status
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/points-mall/<int:goods_id>', methods=['GET'])
@require_login
def get_points_goods(user, goods_id):
    """V42.0: 获取积分商品详情"""
    goods = PointsMallService.get_product_detail(goods_id)
    if not goods:
    return jsonify({'success': False, 'msg': '商品不存在'})
    return jsonify({'success': True, 'data': goods})

@app.route('/api/user/points-mall/exchange', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def exchange_points_goods(user):
    """V42.0: 积分兑换商品"""
    data = request.get_json() or {}
    goods_id = data.get('goods_id')
    quantity = int(data.get('quantity', 1))
    address_snapshot = data.get('address_snapshot', '')
    phone = data.get('phone', '')

    if not goods_id:
    return jsonify({'success': False, 'msg': '请选择要兑换的商品'})

    result = PointsMallService.exchange_goods(
    user_id=user['user_id'],
    user_name=user.get('user_name', ''),
    goods_id=goods_id,
    quantity=quantity,
    address_snapshot=address_snapshot,
    phone=phone,
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/user/points-mall/exchanges', methods=['GET'])
@require_login
def get_points_exchanges(user):
    """获取积分兑换记录"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_points_exchanges WHERE user_id=%s", [user['user_id']])
    items = db.get_all(
        "SELECT * FROM business_points_exchanges WHERE user_id=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
        [user['user_id'], page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/user/seckill/countdown', methods=['GET'])
def get_seckill_countdown(user=None):
    """V42.0: 获取秒杀倒计时信息（供前端展示）"""
    try:
    from datetime import datetime
    from business_common.seckill_service import SeckillService

    activities = db.get_all("""
    SELECT id, promo_name, promo_type, description,
    start_time, end_time, total_stock,
    (SELECT COALESCE(SUM(quantity), 0) FROM business_seckill_orders
    WHERE activity_id=business_promotions.id AND status != 'cancelled') as sold_count,
    status
    FROM business_promotions
    WHERE promo_type='seckill' AND status='active'
    AND end_time >= NOW()
    ORDER BY start_time ASC
    LIMIT 5
    """) or []

    now = datetime.now()
    result = []
    for act in activities:
    start = act.get('start_time', now)
    end = act.get('end_time', now)

    if now < start:
    phase = 'waiting'  # 即将开始
    remaining = int((start - now).total_seconds())
    elif now > end:
    phase = 'ended'   # 已结束
    remaining = 0
    else:
    phase = 'ongoing'  # 进行中
    remaining = int((end - now).total_seconds())

    result.append({
    'id': act['id'],
    'name': act['promo_name'],
    'description': act.get('description', ''),
    'start_time': str(start),
    'end_time': str(end),
    'total_stock': act.get('total_stock', 0),
    'sold_count': act.get('sold_count', 0),
    'remaining_stock': max(0, (act.get('total_stock') or 0) - (act.get('sold_count') or 0)),
    'phase': phase,
    'remaining_seconds': remaining
    })

    return jsonify({'success': True, 'data': result})
    return jsonify({'success': True, 'data': []})

@app.route('/api/user/products/<int:product_id>/reviews', methods=['GET'])
def get_product_reviews(product_id):
    """获取商品评价列表"""
    from business_common.review_service import get_review_service
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 10)), 50)
    result = get_review_service().get_product_reviews(int(product_id), page, page_size)
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/member/card', methods=['GET'])
@require_login
def get_member_card(user):
    """获取会员卡信息"""
    member = db.get_one(
        "SELECT m.*,l.level_name,l.discount_rate,l.icon "
        "FROM business_members m LEFT JOIN business_member_levels l ON m.member_level=l.level_code "
        "WHERE m.user_id=%s",
        [user['user_id']]
    )
    return jsonify({'success': True, 'data': member or {}})

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

# ============ V23.0 积分商城 ============

@app.route('/api/points-mall/products', methods=['GET'])
def get_points_mall_products():
    """获取积分商品列表（公开接口）"""
    from business_common.points_mall import PointsMallService
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 50)
    category = request.args.get('category')

    user = get_current_user()
    ec_id = user.get('ec_id') if user else None
    project_id = user.get('project_id') if user else None

    result = PointsMallService.get_products(
    ec_id=ec_id, project_id=project_id,
    page=page, page_size=page_size, category=category
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/points-mall/products/<goods_id>', methods=['GET'])
def get_points_mall_product_detail(goods_id):
    """获取积分商品详情"""
    from business_common.points_mall import PointsMallService
    goods = PointsMallService.get_product_detail(goods_id)
    if not goods:
    return jsonify({'success': False, 'msg': '商品不存在'})
    return jsonify({'success': True, 'data': goods})

@app.route('/api/user/points-mall/exchange', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=5, window_seconds=60)
def exchange_points_goods_user(user):
    """积分兑换商品"""
    from business_common.points_mall import PointsMallService
    data = request.get_json() or {}
    goods_id = data.get('goods_id')
    quantity = max(1, int(data.get('quantity', 1)))
    address_id = data.get('address_id')

    if not goods_id:
    return jsonify({'success': False, 'msg': '请选择商品'})

    # 获取收货地址快照
    address_snapshot = ''
    phone = user.get('phone', '')
    if address_id:
    addr = db.get_one(
    "SELECT * FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
    [address_id, user['user_id']]
    )
    if addr:
    address_snapshot = f"{addr.get('contact_name','')} {addr.get('contact_phone','')} " \
    f"{addr.get('province','')}{addr.get('city','')}{addr.get('district','')}{addr.get('address','')}"
    phone = addr.get('contact_phone', phone)

    result = PointsMallService.exchange_goods(
    user_id=user['user_id'],
    user_name=user.get('user_name', ''),
    goods_id=goods_id,
    quantity=quantity,
    address_snapshot=address_snapshot,
    phone=phone,
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/user/points-mall/exchanges', methods=['GET'])
@require_login
def get_user_exchanges(user):
    """获取我的兑换记录"""
    from business_common.points_mall import PointsMallService
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20)), 50))
    status = request.args.get('status')

    result = PointsMallService.get_user_exchanges(
    user_id=user['user_id'], page=page, page_size=page_size, status=status
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/points-mall/exchanges/<exchange_id>/confirm', methods=['POST'])
@require_login
def confirm_exchange(user, exchange_id):
    """确认兑换收货"""
    from business_common.points_mall import PointsMallService
    result = PointsMallService.confirm_exchange(user['user_id'], exchange_id)
    return jsonify(result)

# ============ V28.0 成长值体系 ============

@app.route('/api/user/growth/info', methods=['GET'])
@require_login
def get_growth_info(user):
    """V28.0: 获取用户成长值详情"""
    from business_common.growth_service import GrowthService
    info = GrowthService.get_member_growth_info(user.get('user_id'))
    if not info:
    return jsonify({'success': False, 'msg': '用户信息不存在'})
    return jsonify({'success': True, 'data': info})

@app.route('/api/user/growth/logs', methods=['GET'])
@require_login
def get_growth_logs(user):
    """V28.0: 获取成长值记录"""
    from business_common.growth_service import GrowthService
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 50)
    
    result = GrowthService.get_growth_logs(
    user_id=user.get('user_id'),
    page=page,
    page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/growth/rules', methods=['GET'])
def get_growth_rules():
    """V28.0: 获取成长值规则（公开接口）"""
    from business_common.growth_service import GrowthService
    rules = GrowthService.get_growth_rules()
    return jsonify({'success': True, 'data': {'items': rules}})

@app.route('/api/user/achievements', methods=['GET'])
@require_login
def get_user_achievements(user):
    """获取用户成就"""
    achievements = db.get_all(
        "SELECT ua.*,a.achievement_name,a.icon,a.points as reward_points,a.description "
        "FROM business_user_achievements ua "
        "LEFT JOIN business_achievements a ON ua.achievement_id=a.id "
        "WHERE ua.user_id=%s ORDER BY ua.unlocked_at DESC",
        [user['user_id']]
    ) or []
    return jsonify({'success': True, 'data': {'items': achievements}})

@app.route('/api/user/points/exchanges', methods=['GET'])
@require_login
def get_points_exchanges_user(user):
    """V28.0: 获取用户积分兑换记录"""
    uid = user.get('user_id')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 50)
    
    total = db.get_total(
    "SELECT COUNT(*) FROM business_points_exchanges WHERE user_id=%s AND deleted=0",
    [uid]
    )
    offset = (page - 1) * page_size
    
    items = db.get_all(
    """SELECT id, exchange_no, goods_name, goods_image, points_price, quantity,
    total_points, status, tracking_no, logistics_company, created_at, shipped_at
    FROM business_points_exchanges
    WHERE user_id=%s AND deleted=0
    ORDER BY created_at DESC
    LIMIT %s OFFSET %s""",
    [uid, page_size, offset]
    ) or []
    
    return jsonify({'success': True, 'data': {
    'items': items,
    'total': total,
    'page': page,
    'page_size': page_size,
    'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/user/points/exchanges/<int:exchange_id>', methods=['GET'])
@require_login
def get_points_exchange_detail(user, exchange_id):
    """V28.0: 获取积分兑换详情"""
    uid = user.get('user_id')
    
    exchange = db.get_one(
    """SELECT e.*, d.logistics_company, d.tracking_no, d.delivery_status, d.ship_time
    FROM business_points_exchanges e
    LEFT JOIN business_points_delivery d ON d.exchange_id = e.id
    WHERE e.id=%s AND e.user_id=%s AND e.deleted=0""",
    [exchange_id, uid]
    )
    
    if not exchange:
    return jsonify({'success': False, 'msg': '兑换记录不存在'})
    
    return jsonify({'success': True, 'data': exchange})

@app.route('/api/user/points/exchanges/<int:exchange_id>/confirm', methods=['POST'])
@require_login
def confirm_points_exchange_received(user, exchange_id):
    """V28.0: 确认收货"""
    uid = user.get('user_id')
    
    exchange = db.get_one(
    "SELECT * FROM business_points_exchanges WHERE id=%s AND user_id=%s AND status='shipped'",
    [exchange_id, uid]
    )
    
    if not exchange:
    return jsonify({'success': False, 'msg': '兑换记录不存在或状态不允许'})
    
    try:
    db.execute(
    "UPDATE business_points_exchanges SET status='completed', completed_at=NOW() WHERE id=%s",
    [exchange_id]
    )
    # 更新物流状态
    db.execute(
    "UPDATE business_points_delivery SET delivery_status='delivered', signed_time=NOW() WHERE exchange_id=%s",
    [exchange_id]
    )
    return jsonify({'success': True, 'msg': '确认收货成功'})
    return jsonify({'success': False, 'msg': '操作失败'})

# ============ V33.0 发票管理 ============

@app.route('/api/user/invoice/titles', methods=['GET'])
@require_login
def get_invoice_titles(user):
    """获取发票抬头列表"""
    from business_common.invoice_service_v2 import get_invoice_service
    return jsonify({'success': True, 'data': {'items': get_invoice_service().get_invoice_titles(user['user_id'])}})

@app.route('/api/user/invoice/titles', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=20, window_seconds=60)
def create_invoice_title(user):
    """创建发票抬头"""
    from business_common.invoice_service_v2 import get_invoice_service
    data = request.get_json() or {}
    return jsonify(get_invoice_service().create_invoice_title(
        user_id=user['user_id'],
        title_type=data.get('title_type', 'personal'),
        title_name=data.get('title_name', '').strip(),
        tax_no=data.get('tax_no', ''),
        bank_name=data.get('bank_name', ''),
        bank_account=data.get('bank_account', ''),
        address=data.get('address', ''),
        phone=data.get('phone', ''),
        is_default=bool(data.get('is_default', False)),
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    ))

@app.route('/api/user/invoice/titles/<int:title_id>', methods=['PUT'])
@require_login
def update_invoice_title(user, title_id):
    """更新发票抬头"""
    from business_common.invoice_service_v2 import get_invoice_service
    data = request.get_json() or {}
    return jsonify(get_invoice_service().update_invoice_title(
        title_id=int(title_id),
        user_id=user['user_id'],
        title_name=data.get('title_name'),
        tax_no=data.get('tax_no'),
        bank_name=data.get('bank_name'),
        bank_account=data.get('bank_account'),
        address=data.get('address'),
        phone=data.get('phone'),
        is_default=data.get('is_default')
    ))

@app.route('/api/user/invoice/titles/<int:title_id>', methods=['DELETE'])
@require_login
def delete_invoice_title(user, title_id):
    """删除发票抬头"""
    from business_common.invoice_service_v2 import get_invoice_service
    return jsonify(get_invoice_service().delete_invoice_title(int(title_id), user['user_id']))

@app.route('/api/user/invoices', methods=['GET'])
@require_login
def get_user_invoices(user):
    """获取发票列表"""
    from business_common.invoice_service_v2 import get_invoice_service
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    result = get_invoice_service().get_invoices(user['user_id'], page, page_size)
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/invoices/<int:invoice_id>', methods=['GET'])
@require_login
def get_user_invoice_detail(user, invoice_id):
    """获取发票详情"""
    invoice = db.get_one(
        "SELECT i.*,o.order_no FROM business_invoices i "
        "LEFT JOIN business_orders o ON i.order_id=o.id "
        "WHERE i.id=%s AND i.user_id=%s AND i.deleted=0",
        [invoice_id, user['user_id']]
    )
    if not invoice:
        return jsonify({'success': False, 'msg': '发票不存在'})
    return jsonify({'success': True, 'data': invoice})

@app.route('/api/user/orders/<int:order_id>/invoice/apply', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def apply_invoice_from_order(user, order_id):
    """申请发票"""
    from business_common.invoice_service_v2 import get_invoice_service
    data = request.get_json() or {}
    return jsonify(get_invoice_service().apply_invoice_from_order(
        user_id=user['user_id'],
        order_id=int(order_id),
        title_id=data.get('title_id'),
        title_type=data.get('title_type'),
        title_name=data.get('title_name'),
        tax_no=data.get('tax_no')
    ))

@app.route('/api/user/invoices/<int:invoice_id>/cancel', methods=['POST'])
@require_login
def cancel_invoice(user, invoice_id):
    """取消发票申请"""
    from business_common.invoice_service_v2 import get_invoice_service
    return jsonify(get_invoice_service().cancel_invoice(int(invoice_id), user['user_id']))

@app.route('/api/user/growth/tasks', methods=['GET'])
@require_login
def get_growth_tasks(user):
    """V38.0: 获取用户成长任务列表"""
    uid = user.get('user_id')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
    from business_common.growth_task_service import growth_task_service
    result = growth_task_service.get_user_task_summary(uid, ec_id, project_id)
    return jsonify({'success': True, 'data': result})
    return jsonify({'success': True, 'data': {
    'total_tasks': 0, 'completed_tasks': 0, 'remaining_tasks': 0,
    'completion_rate': 0, 'tasks': []
    }})

@app.route('/api/user/growth/tasks/claim/<int:task_id>', methods=['POST'])
@require_login
def claim_growth_task_reward(user, task_id):
    """V38.0: 领取成长任务奖励"""
    uid = user.get('user_id')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
    from business_common.growth_task_service import growth_task_service
    # 领取奖励时会触发成长值和积分发放
    result = growth_task_service.increment_task_progress(uid, 'order', ec_id, project_id, 0)
    return jsonify({'success': True, 'msg': '奖励已发放', 'data': result})
    return jsonify({'success': False, 'msg': '操作失败'})

# ============ V38.0 评价积分奖励 ============

@app.route('/api/user/review/reward/rules', methods=['GET'])
@require_login
def get_review_reward_rules(user):
    """V38.0: 获取评价积分奖励规则"""
    try:
    from business_common.review_reward_service import review_reward_service
    rules = review_reward_service.get_reward_rules_display()
    return jsonify({'success': True, 'data': rules})
    # 返回默认规则
    return jsonify({'success': True, 'data': [
    {'rating': 5, 'label': '5星好评', 'points': 20, 'growth': 10},
    {'rating': 4, 'label': '4星好评', 'points': 10, 'growth': 5},
    {'rating': 3, 'label': '3星中评', 'points': 5, 'growth': 2},
    {'rating': 2, 'label': '2星差评', 'points': 0, 'growth': 0},
    {'rating': 1, 'label': '1星差评', 'points': 0, 'growth': 0},
    ]})

@app.route('/api/user/review/reward/stats', methods=['GET'])
@require_login
def get_review_reward_stats(user):
    """V38.0: 获取用户评价奖励统计"""
    uid = user.get('user_id')
    
    try:
    from business_common.review_reward_service import review_reward_service
    stats = review_reward_service.get_user_reward_stats(uid)
    return jsonify({'success': True, 'data': stats})
    return jsonify({'success': True, 'data': {
    'total_reviews': 0, 'rewarded_reviews': 0,
    'total_points_earned': 0, 'total_growth_earned': 0, 'avg_rating': 0
    }})

# ============ V38.0 最优折扣计算 ============

@app.route('/api/user/discount/optimal', methods=['GET'])
@require_login
def get_optimal_discount(user):
    """获取最优折扣"""
    from business_common.discount_calculator_service import discount_calculator
    data = request.get_json() or {}
    result = discount_calculator.get_optimal_discount(
        user_id=user['user_id'],
        items=data.get('items', []),
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/discount/preview', methods=['POST'])
@require_login
def preview_discount(user):
    """V38.0: 预览折扣计算"""
    data = request.get_json() or {}
    
    order_amount = float(data.get('amount', 0))
    use_points = int(data.get('use_points', 0))
    coupon = data.get('coupon')
    
    if order_amount <= 0:
    return jsonify({'success': False, 'msg': '订单金额必须大于0'})
    
    try:
    from business_common.discount_calculator_service import discount_calculator
    result = discount_calculator.calculate_preview(order_amount, coupon, use_points)
    return jsonify({'success': True, 'data': result})
    return jsonify({'success': True, 'data': {
    'order_amount': order_amount,
    'use_points': use_points,
    'points_deduction': use_points / 100,
    'final_amount': order_amount,
    'total_discount': use_points / 100,
    }})

# ============ V38.0 分享追踪 ============

@app.route('/api/user/share/record', methods=['POST'])
@require_login
def record_share(user):
    """V38.0: 记录分享行为"""
    uid = user.get('user_id')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    data = request.get_json() or {}
    
    share_type = data.get('share_type', 'product')
    target_id = int(data.get('target_id', 0))
    target_title = data.get('title', '')
    channel = data.get('channel', 'link')
    
    if not target_id:
    return jsonify({'success': False, 'msg': '请提供分享目标'})
    
    try:
    from business_common.share_service import share_service
    result = share_service.record_share(
    uid, share_type, target_id, target_title, channel, ec_id, project_id
    )
    
    # 如果是分享商品，触发成长任务
    if share_type == 'product':
    try:
    from business_common.growth_task_service import growth_task_service
    growth_task_service.on_share(uid, ec_id, project_id)
    
    return jsonify({'success': True, 'data': result})
    return jsonify({'success': True, 'data': {
    'share_id': 0,
    'share_url': f'/product/{target_id}'
    }})

@app.route('/api/user/share/click', methods=['POST'])
def record_share_click():
    """V38.0: 记录分享链接点击（无需登录）"""
    data = request.get_json() or {}
    share_token = data.get('share_token', '')
    
    if not share_token:
    return jsonify({'success': False, 'msg': '缺少分享标识'})
    
    try:
    from business_common.share_service import share_service
    result = share_service.record_click(share_token)
    return jsonify({'success': True, 'data': result})
    return jsonify({'success': True, 'data': {'source_user_id': 0}})

@app.route('/api/user/share/stats', methods=['GET'])
@require_login
def get_share_stats(user):
    """V38.0: 获取用户分享统计"""
    uid = user.get('user_id')
    
    try:
    from business_common.share_service import share_service
    stats = share_service.get_user_share_stats(uid)
    return jsonify({'success': True, 'data': stats})
    return jsonify({'success': True, 'data': {
    'total_shares': 0, 'total_clicks': 0, 'total_converts': 0,
    'total_convert_amount': 0, 'click_rate': 0, 'convert_rate': 0
    }})

@app.route('/api/user/share/history', methods=['GET'])
@require_login
def get_share_history(user):
    """V38.0: 获取分享历史"""
    uid = user.get('user_id')
    limit = min(int(request.args.get('limit', 20)), 50)
    
    try:
    from business_common.share_service import share_service
    history = share_service.get_share_history(uid, limit)
    return jsonify({'success': True, 'data': history})
    return jsonify({'success': True, 'data': []})

@app.route('/api/user/share/poster/config', methods=['GET'])
@require_login
def get_share_poster_config(user):
    """V38.0: 获取分享海报配置"""
    uid = user.get('user_id')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    share_type = request.args.get('type', 'product')
    target_id = int(request.args.get('target_id', 0))
    share_url = (request.args.get('share_url') or '').strip()
    
    if not target_id:
    return jsonify({'success': False, 'msg': '请提供目标ID'})
    
    try:
    from business_common.share_service import share_service
    config = share_service.generate_poster_config(
    share_type, target_id, uid, ec_id, project_id, share_url=share_url or None
    )

    return jsonify({'success': True, 'data': config})
    return jsonify({'success': True, 'data': {
    'width': 750, 'height': 1000, 'elements': []
    }})

# ============ V29.0 申请审批系统 (用户端) ============

@app.route('/api/user/application/types', methods=['GET'])
@require_login
def get_application_types_list(user):
    """V29.0: 获取申请类型列表"""
    from business_common.application_service import ApplicationService
    category = request.args.get('category')
    types = ApplicationService.get_application_types(category=category)
    return jsonify({'success': True, 'data': {'items': types}})

@app.route('/api/user/application/types/<type_code>', methods=['GET'])
@require_login
def get_application_type_detail(user, type_code):
    """V29.0: 获取申请类型详情"""
    from business_common.application_service import ApplicationService
    app_type = ApplicationService.get_application_type(type_code)
    if not app_type:
    return jsonify({'success': False, 'msg': '申请类型不存在'})
    return jsonify({'success': True, 'data': app_type})

@app.route('/api/user/applications/v2', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def create_application_v2(user):
    """V29.0: 创建申请（支持8种业务类型）"""
    from business_common.application_service import ApplicationService
    
    data = request.get_json() or {}
    type_code = data.get('type_code')
    title = data.get('title', '').strip()
    form_data = data.get('form_data', {})
    remark = data.get('remark', '').strip()
    attachments = data.get('attachments', [])
    
    if not type_code:
    return jsonify({'success': False, 'msg': '请选择申请类型'})
    if not title:
    return jsonify({'success': False, 'msg': '请输入申请标题'})
    
    result = ApplicationService.create_application(
    user_id=user.get('user_id'),
    user_name=user.get('user_name', ''),
    user_phone=user.get('phone', ''),
    type_code=type_code,
    title=title,
    form_data=form_data,
    ec_id=user.get('ec_id'),
    project_id=user.get('project_id'),
    attachments=attachments,
    remark=remark
    )
    return jsonify(result)

@app.route('/api/user/applications/v2', methods=['GET'])
@require_login
def get_user_applications_v2(user):
    """V29.0: 获取用户申请列表（支持筛选和搜索）"""
    from business_common.application_service import ApplicationService
    
    type_code = request.args.get('type_code')
    status = request.args.get('status')
    keyword = request.args.get('keyword', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    result = ApplicationService.get_user_applications(
    user_id=user.get('user_id'),
    type_code=type_code,
    status=status,
    keyword=keyword if keyword else None,
    page=page,
    page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/applications/v2/<int:app_id>', methods=['GET'])
@require_login
def get_application_detail_v2(user, app_id):
    """V29.0: 获取申请详情"""
    from business_common.application_service import ApplicationService
    
    app = ApplicationService.get_application_detail(
    app_id=app_id,
    user_id=user.get('user_id'),
    is_staff=False
    )
    
    if not app:
    return jsonify({'success': False, 'msg': '申请不存在'})
    
    return jsonify({'success': True, 'data': app})

@app.route('/api/user/applications/v2/<int:app_id>/cancel', methods=['POST'])
@require_login
def cancel_application_v2(user, app_id):
    """V29.0: 取消申请"""
    from business_common.application_service import ApplicationService
    
    result = ApplicationService.cancel_application(
    app_id=app_id,
    user_id=user.get('user_id')
    )
    return jsonify(result)

@app.route('/api/user/applications/v2/<int:app_id>/favorite', methods=['POST'])
@require_login
def set_application_favorite(user, app_id):
    """V29.0: 设置/取消常用申请"""
    from business_common.application_service import ApplicationService
    
    data = request.get_json() or {}
    is_favorite = 1 if data.get('is_favorite') else 0
    
    result = ApplicationService.set_favorite(
    app_id=app_id,
    user_id=user.get('user_id'),
    is_favorite=is_favorite
    )
    return jsonify(result)

@app.route('/api/user/applications/v2/<int:app_id>/copy', methods=['POST'])
@require_login
def copy_application_v2(user, app_id):
    """V29.0: 复制申请（一键复用）"""
    from business_common.application_service import ApplicationService
    
    result = ApplicationService.copy_application(
    app_id=app_id,
    user_id=user.get('user_id')
    )
    return jsonify(result)

@app.route('/api/user/applications/v2/favorites', methods=['GET'])
@require_login
def get_favorite_applications(user):
    """获取收藏的申请"""
    from business_common.application_service import ApplicationService
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    result = ApplicationService.get_favorite_applications(
        user_id=user['user_id'], page=page, page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/user/applications/v2/check-lift', methods=['POST'])
@require_login
def check_lift_availability(user):
    """V29.0: 检查货梯可用性"""
    data = request.get_json() or {}
    lift_no = data.get('lift_no')
    use_date = data.get('use_date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([lift_no, use_date, start_time, end_time]):
    return jsonify({'success': False, 'msg': '缺少必要参数'})
    
    # 查询同一货梯同一时间段的已批准申请
    existing = db.get_all(
    """SELECT id, start_time, end_time FROM (
    SELECT id,
    JSON_UNQUOTE(JSON_EXTRACT(form_data, '$.start_time')) as start_time,
    JSON_UNQUOTE(JSON_EXTRACT(form_data, '$.end_time')) as end_time
    FROM business_applications
    WHERE app_type='cargo_lift' 
    AND status IN ('pending', 'approved', 'processing')
    AND JSON_UNQUOTE(JSON_EXTRACT(form_data, '$.lift_no')) = %s
    AND JSON_UNQUOTE(JSON_EXTRACT(form_data, '$.use_date')) = %s
    AND ec_id=%s AND project_id=%s
    ) t WHERE (start_time <= %s AND end_time > %s) OR (start_time < %s AND end_time >= %s)""",
    [lift_no, use_date, user.get('ec_id'), user.get('project_id'), 
    end_time, start_time, end_time, start_time]
    )
    
    if existing:
    return jsonify({
    'success': True,
    'data': {
    'available': False,
    'msg': '该时间段货梯已被预约',
    'conflicts': existing
    }
    })
    
    return jsonify({
    'success': True,
    'data': {
    'available': True,
    'msg': '该时间段可用'
    }
    })

# ============ V2 访客邀约转发接口 ============

GUEST_SERVICE_URL = 'https://wj.wojiacloud.com/api/guest'

@app.route('/api/v2/guest/invitations', methods=['GET'])
@require_login
def get_guest_invitations_v2(user):
    """
    V2版访客邀约列表 - 转发到访客服务
    转发接口: https://wj.wojiacloud.com/api/guest/getGuestList
    """
    try:
    # 获取参数
    current = request.args.get('current', '1')
    row_count = request.args.get('row_count', '10')
    
    # 从用户信息中获取token
    token = request.args.get('access_token') or request.headers.get('Token', '')
    
    # 构建目标URL
    timestamp = str(int(time.time() * 1000))
    target_url = f"{GUEST_SERVICE_URL}/getGuestList?time={timestamp}&current={current}&rowCount={row_count}&access_token={urllib.parse.quote(token)}"
    
    logging.info(f"[GuestV2] 转发请求: {target_url.replace(token, '***')}")
    
    # 创建请求
    req = urllib.request.Request(
    target_url,
    headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
    }
    )
    
    # 发送请求
    with urllib.request.urlopen(req, timeout=30) as response:
    response_data = response.read().decode('utf-8')
    
    # 解析响应
    result = json.loads(response_data)
    
    # 统一返回格式
    if result.get('result') == 'success' or result.get('success'):
    return jsonify({
    'success': True,
    'data': result.get('data', []),
    'total': len(result.get('data', [])),
    'page': int(current),
    'page_size': int(row_count),
    'msg': result.get('msg', '获取成功')
    })
    else:
    return jsonify({
    'success': False,
    'msg': result.get('msg', '获取访客列表失败'),
    'data': []
    })
    
    except urllib.error.HTTPError as e:
    logging.error(f"[GuestV2] HTTP错误: {e.code} - {e.reason}")
    return jsonify({'success': False, 'msg': f'访客服务异常: {e.reason}', 'data': []})
    except urllib.error.URLError as e:
    logging.error(f"[GuestV2] 网络错误: {e.reason}")
    return jsonify({'success': False, 'msg': '访客服务连接失败', 'data': []})
    return jsonify({'success': False, 'msg': f'获取访客列表失败: {str(e)}', 'data': []})

@app.route('/api/v2/guest/detail', methods=['GET'])
@require_login
def get_guest_detail_v2(user):
    """
    V2版访客详情 - 转发到访客服务
    转发接口: https://wj.wojiacloud.com/api/guest/getGuestDetail
    """
    try:
    guest_id = request.args.get('guest_id')
    if not guest_id:
    return jsonify({'success': False, 'msg': '缺少访客ID'})
    
    # 从用户信息中获取token
    token = request.args.get('access_token') or request.headers.get('Token', '')
    
    # 构建目标URL
    timestamp = str(int(time.time() * 1000))
    target_url = f"{GUEST_SERVICE_URL}/getGuestDetail?time={timestamp}&guestId={urllib.parse.quote(guest_id)}&access_token={urllib.parse.quote(token)}"
    
    logging.info(f"[GuestV2] 转发详情请求: guest_id={guest_id}")
    
    # 创建请求
    req = urllib.request.Request(
    target_url,
    headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
    }
    )
    
    # 发送请求
    with urllib.request.urlopen(req, timeout=30) as response:
    response_data = response.read().decode('utf-8')
    
    # 解析响应
    result = json.loads(response_data)
    
    if result.get('result') == 'success' or result.get('success'):
    return jsonify({
    'success': True,
    'data': result.get('data', {}),
    'msg': result.get('msg', '获取成功')
    })
    else:
    return jsonify({
    'success': False,
    'msg': result.get('msg', '获取访客详情失败')
    })
    return jsonify({'success': False, 'msg': f'获取访客详情失败: {str(e)}'})

# ============ V2版房间管理接口 ============

@app.route('/api/v2/rooms', methods=['GET'])
@require_login
def get_rooms_v2(user):
    """
    V2版获取房间列表 - 转发到访客服务
    转发接口: https://wj.wojiacloud.com/api/guest/getRoomList
    """
    try:
    # 获取参数
    current = request.args.get('current', '1')
    row_count = request.args.get('row_count', '10')
    keyword = request.args.get('keyword', '')
    
    # 从用户信息中获取token
    token = request.args.get('access_token') or request.headers.get('Token', '')
    
    # 构建目标URL
    timestamp = str(int(time.time() * 1000))
    target_url = f"{GUEST_SERVICE_URL}/getRoomList?time={timestamp}&current={current}&rowCount={row_count}"
    
    # 如果有搜索关键词，添加参数
    if keyword:
    target_url += f"&keyword={urllib.parse.quote(keyword)}"
    
    target_url += f"&access_token={urllib.parse.quote(token)}"
    
    logging.info(f"[RoomV2] 转发请求: {target_url.replace(token, '***')}")
    
    # 创建请求
    req = urllib.request.Request(
    target_url,
    headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Origin': 'https://wj.wojiacloud.com',
    'Referer': 'https://wj.wojiacloud.com/'
    }
    )
    
    # 发送请求
    with urllib.request.urlopen(req, timeout=30) as response:
    response_data = response.read().decode('utf-8')
    
    # 解析响应
    result = json.loads(response_data)
    
    # 统一返回格式
    if result.get('result') == 'success' or result.get('success'):
    return jsonify({
    'success': True,
    'data': result.get('data', []),
    'total': result.get('total', len(result.get('data', []))),
    'page': int(current),
    'page_size': int(row_count),
    'msg': result.get('msg', '获取成功')
    })
    else:
    return jsonify({
    'success': False,
    'msg': result.get('msg', '获取房间列表失败'),
    'data': []
    })
    
    except urllib.error.HTTPError as e:
    logging.error(f"[RoomV2] HTTP错误: {e.code} - {e.reason}")
    return jsonify({'success': False, 'msg': f'访客服务异常: {e.reason}', 'data': []})
    except urllib.error.URLError as e:
    logging.error(f"[RoomV2] 网络错误: {e.reason}")
    return jsonify({'success': False, 'msg': '访客服务连接失败', 'data': []})
    return jsonify({'success': False, 'msg': f'获取房间列表失败: {str(e)}', 'data': []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22311, debug=False)

