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
    except Exception as e:
        logging.warning(f"清理用户缓存失败: {e}")


def bump_product_counter(product_id, field, delta=1):
    """更新商品行为计数，支持浏览量/收藏量"""
    if not product_id or field not in ('view_count', 'favorite_count'):
        return
    try:
        db.execute(
            f"UPDATE business_products SET {field}=GREATEST(COALESCE({field}, 0) + %s, 0), updated_at=NOW() WHERE id=%s AND deleted=0",
            [int(delta), product_id]
        )
    except Exception as e:
        logging.warning(f"更新商品计数失败: field={field}, product_id={product_id}, error={e}")

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
@rate_limiter.rate_limit(limit=20, window_seconds=60)  # 限流：每分钟最多20次申请
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
    # 清除统计缓存，确保stats数据一致性
    from business_common.cache_service import cache_delete
    cache_delete(f"user_stats_{user['user_id']}")
    return jsonify({'success': True, 'msg': '申请已撤销'})

# ============ 购物车 V32.0 ============

from business_common.cart_service import cart


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
    """V41.0: 记录用户行为"""
    data = request.get_json() or {}
    behavior_type = data.get('behavior_type', 'browse_product')
    target_type = data.get('target_type', 'product')
    target_id = data.get('target_id')
    duration = data.get('duration', 0)
    
    if not target_id:
        return jsonify({'success': False, 'msg': '缺少目标ID'})
    
    try:
        # 获取目标名称
        target_name = ''
        if target_type == 'product':
            product = db.get_one("SELECT product_name FROM business_products WHERE id=%s", [target_id])
            target_name = product['product_name'] if product else ''
        elif target_type == 'shop':
            shop = db.get_one("SELECT shop_name FROM business_shops WHERE id=%s", [target_id])
            target_name = shop['shop_name'] if shop else ''
        
        user_behavior.track_behavior(
            user_id=user['user_id'],
            behavior_type=behavior_type,
            target_type=target_type,
            target_id=int(target_id),
            target_name=target_name,
            ec_id=user.get('ec_id', 1),
            project_id=user.get('project_id', 1),
            duration=duration,
            extra_data=data.get('extra_data')
        )
        return jsonify({'success': True, 'msg': '记录成功'})
    except Exception as e:
        logging.warning(f"记录行为失败: {e}")
        return jsonify({'success': False, 'msg': '记录失败'})


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
        f"SELECT id,order_no,order_type,shop_id,total_amount,actual_amount,order_status,pay_status,created_at, "
        f"COALESCE(expire_time, DATE_ADD(created_at, INTERVAL {ORDER_EXPIRE_MINUTES} MINUTE)) AS expire_time "
        "FROM business_orders WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )

    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/user/orders/<order_id>', methods=['GET'])
@require_login
def get_order_detail(user, order_id):
    order = db.get_one(
        f"SELECT *, COALESCE(expire_time, DATE_ADD(created_at, INTERVAL {ORDER_EXPIRE_MINUTES} MINUTE)) AS expire_time "
        "FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
        [order_id, user['user_id']]
    )

    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    # V15: 查询是否已评价
    try:
        review = db.get_one(
            "SELECT id FROM business_reviews WHERE user_id=%s AND target_type='order' AND target_id=%s AND deleted=0",
            [user['user_id'], str(order_id)]
        )
        order['has_review'] = 1 if review else 0
    except Exception:
        order['has_review'] = 0
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
    # V9.0修复：取消订单时回滚库存
    try:
        items = db.get_all(
            "SELECT product_id, quantity FROM business_order_items WHERE order_id=%s", [order_id]
        )
        if items:
            for item in items:
                db.execute(
                    "UPDATE business_products SET stock=stock+%s, sales_count=GREATEST(0, sales_count-%s) WHERE id=%s",
                    [item['quantity'], item['quantity'], item['product_id']]
                )
    except Exception as e:
        logging.warning(f"取消订单库存回滚失败: {e}")
    # 清除用户统计缓存
    from business_common.cache_service import cache_delete
    cache_delete(f"user_stats_{user['user_id']}")
    return jsonify({'success': True, 'msg': '订单已取消'})

@app.route('/api/user/orders/<order_id>/refund', methods=['POST'])
@require_login
def apply_refund(user, order_id):
    """V19.0: 用户申请退款（已支付/已发货订单）"""
    data = request.get_json() or {}
    reason = (data.get('reason') or '').strip()
    
    if not reason:
        return jsonify({'success': False, 'msg': '请填写退款原因'})
    
    # 查询订单
    order = db.get_one(
        "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
        [order_id, user['user_id']]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    
    status = order.get('order_status') or order.get('status', '')
    pay_status = order.get('pay_status', '')
    
    # 只有已支付或已发货的订单可申请退款
    if status not in ('paid', 'shipped'):
        return jsonify({'success': False, 'msg': '当前订单状态不支持退款申请'})
    
    if pay_status != 'paid':
        return jsonify({'success': False, 'msg': '订单未支付，无法申请退款'})
    
    # 检查是否已有退款申请
    if order.get('refund_status') in ('pending', 'processing'):
        return jsonify({'success': False, 'msg': '您已有退款申请在处理中'})
    
    if order.get('refund_status') == 'approved':
        return jsonify({'success': False, 'msg': '该订单已退款完成'})
    
    try:
        # 更新订单退款状态
        db.execute(
            """UPDATE business_orders 
               SET refund_status='pending', refund_reason=%s, refund_requested_at=NOW(), updated_at=NOW() 
               WHERE id=%s""",
            [reason, order_id]
        )
        
        # 发送通知给员工
        from business_common.notification import send_notification
        from business_common.websocket_service import push_notification
        
        send_notification(
            user_id='staff',
            title='新的退款申请',
            content=f"用户 {user.get('user_name', '')} 申请退款，订单号：{order.get('order_no', '')}，原因：{reason[:50]}",
            notify_type='refund',
            ec_id=order.get('ec_id'),
            project_id=order.get('project_id')
        )
        
        # WebSocket推送给员工端
        push_notification(
            channel='staff',
            data={
                'type': 'refund_request',
                'order_id': order_id,
                'order_no': order.get('order_no'),
                'user_name': user.get('user_name'),
                'amount': float(order.get('actual_amount', 0)),
                'reason': reason[:100]
            }
        )
        
        return jsonify({'success': True, 'msg': '退款申请已提交，请等待审核'})
    except Exception as e:
        logging.error(f"申请退款失败: {e}")
        return jsonify({'success': False, 'msg': '申请失败，请稍后重试'})

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
    """V27.0: 获取场地详情，浏览足迹自动记录"""
    venue = db.get_one("SELECT * FROM business_venues WHERE id=%s AND deleted=0 AND status='open'", [venue_id])
    if not venue:
        return jsonify({'success': False, 'msg': '场地不存在'})
    
    # V27.0: 自动记录浏览足迹
    try:
        images_list = []
        if venue.get('images'):
            try:
                images_list = json.loads(venue['images']) if isinstance(venue['images'], str) else venue.get('images', [])
            except:
                images_list = []
        
        db.execute("""
            INSERT INTO business_recently_viewed 
            (user_id, view_type, target_id, target_name, target_image, target_price, viewed_at)
            VALUES (%s, 'venue', %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
            target_name = VALUES(target_name),
            target_image = VALUES(target_image),
            target_price = VALUES(target_price),
            viewed_at = NOW()
        """, [
            user['user_id'], 
            venue_id,
            venue.get('venue_name', ''),
            images_list[0] if images_list else '',
            venue.get('price', 0)
        ])
    except Exception as e:
        logging.warning(f"记录场馆浏览足迹失败: {e}")
    
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
@rate_limiter.rate_limit(limit=10, window_seconds=60)  # 限流：每分钟最多10次预约
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
        """
        SELECT m.user_id, m.user_name, m.phone, m.member_level, m.points, m.total_points, m.balance,
               COALESCE(ml.level_name, m.member_level) AS display_level_name,
               COALESCE(ml.discount_rate, 1.00) AS discount_rate,
               COALESCE(ml.points_rate, 1.00) AS points_rate
        FROM business_members m
        LEFT JOIN business_member_levels ml ON m.member_level = ml.level_code
        WHERE m.user_id=%s
        LIMIT 1
        """,
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
            member = {
                'user_id': uid,
                'user_name': user.get('user_name', ''),
                'phone': user.get('phone', ''),
                'member_level': 'bronze',
                'display_level_name': '青铜会员',
                'discount_rate': 1.00,
                'points_rate': 1.00,
                'points': 0,
                'total_points': 0,
                'balance': 0
            }
        except Exception as e:
            logging.warning('auto create member failed: %s', e)
            member = {
                'user_id': uid,
                'user_name': user.get('user_name', ''),
                'phone': user.get('phone', ''),
                'points': 0,
                'total_points': 0,
                'balance': 0,
                'member_level': 'bronze',
                'display_level_name': '青铜会员',
                'discount_rate': 1.00,
                'points_rate': 1.00
            }
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
    # 兼容 type 和 shop_type 两种参数名
    shop_type = request.args.get('shop_type') or request.args.get('type')
    keyword = request.args.get('keyword', '').strip()
    show_all = request.args.get('show_all', '0')  # 是否显示已关闭门店
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)

    where = "deleted=0"
    if show_all != '1':
        where += " AND status='open'"
    params = []
    if shop_type:
        where += " AND shop_type=%s"; params.append(shop_type)
    if keyword:
        where += " AND (shop_name LIKE %s OR address LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw])
    try:
        total = db.get_total("SELECT COUNT(*) FROM business_shops WHERE " + where, params)
        offset = (page - 1) * page_size
        shops = db.get_all(
            "SELECT id,shop_name,shop_type,address,phone,description,business_hours,status,avg_rating FROM business_shops WHERE "
            + where + " ORDER BY status ASC, avg_rating DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        # 兼容旧版不含分页的调用（只传了简单参数）
        if page == 1 and page_size == 20 and not request.args.get('page'):
            return jsonify({'success': True, 'data': shops or []})
        return jsonify({'success': True, 'data': {'items': shops or [], 'total': total, 'page': page, 'page_size': page_size}})
    except Exception as e:
        logging.warning(f"门店列表查询失败: {e}")
        return jsonify({'success': True, 'data': []})

@app.route('/api/shops/<shop_id>', methods=['GET'])
def get_shop_detail(shop_id):
    """获取门店详情"""
    shop = db.get_one(
        "SELECT * FROM business_shops WHERE id=%s AND status='open' AND deleted=0",
        [shop_id]
    )
    if not shop:
        return jsonify({'success': False, 'msg': '门店不存在或已关闭'})
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
        'sales':      'p.sales_count DESC',
        'hot':        'p.view_count DESC',
        'new':        'p.created_at DESC',
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
    """获取商品详情，包含SKU规格，V27.0增加浏览足迹自动记录，V37.0增加会员价"""
    product = db.get_one(
        "SELECT p.*, s.shop_name, s.address as shop_address, s.phone as shop_phone "
        "FROM business_products p "
        "LEFT JOIN business_shops s ON p.shop_id=s.id "
        "WHERE p.id=%s AND p.status='active' AND p.deleted=0",
        [product_id]
    )
    if not product:
        return jsonify({'success': False, 'msg': '商品不存在或已下架'})

    bump_product_counter(product_id, 'view_count', 1)
    product['view_count'] = int(product.get('view_count') or 0) + 1
    
    # V27.0: 自动记录浏览足迹（异步，不影响返回速度）
    user = get_current_user()
    if user:
        try:
            images_list = []
            if product.get('images'):
                try:
                    images_list = json.loads(product['images']) if isinstance(product['images'], str) else product.get('images', [])
                except:
                    images_list = []
            
            db.execute("""
                INSERT INTO business_recently_viewed 
                (user_id, view_type, target_id, target_name, target_image, target_price, viewed_at)
                VALUES (%s, 'product', %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                target_name = VALUES(target_name),
                target_image = VALUES(target_image),
                target_price = VALUES(target_price),
                viewed_at = NOW()
            """, [
                user['user_id'], 
                product_id,
                product.get('product_name', ''),
                images_list[0] if images_list else '',
                product.get('price', 0)
            ])
        except Exception as e:
            logging.warning(f"记录商品浏览足迹失败: {e}")
        
        # V37.0: 计算会员价
        try:
            member = db.get_one(
                "SELECT member_level, member_grade FROM business_members WHERE user_id=%s",
                [user['user_id']]
            )
            if member:
                level_info = db.get_one(
                    "SELECT level_name, discount_rate FROM business_member_levels WHERE level_code=%s",
                    [member.get('member_level', 'L1')]
                )
                if level_info and level_info.get('discount_rate'):
                    discount_rate = float(level_info['discount_rate'])
                    if discount_rate < 1.0:  # 会员有折扣
                        regular_price = float(product.get('price', 0))
                        member_price = round(regular_price * discount_rate, 2)
                        product['member_price'] = member_price
                        product['member_discount'] = discount_rate
                        product['member_level_name'] = level_info['level_name']
                        product['member_grade'] = member.get('member_grade', level_info['level_name'])
                        product['member_savings'] = round(regular_price - member_price, 2)
                        product['is_member_price_active'] = True
        except Exception as e:
            logging.warning(f"计算会员价失败: {e}")
    
    # P1增强：获取商品SKU列表

    try:
        skus = db.get_all(
            """SELECT id, sku_name, sku_code, specs, price, original_price, stock, sales_count 
               FROM business_product_skus WHERE product_id=%s AND status=1 AND deleted=0""",
            [product_id]
        )
        product['skus'] = skus or []
        
        # V37.0: 为每个SKU计算会员价
        if user and product.get('is_member_price_active'):
            for sku in product['skus']:
                try:
                    sku_regular_price = float(sku.get('price', 0))
                    sku_member_price = round(sku_regular_price * discount_rate, 2)
                    sku['member_price'] = sku_member_price
                    sku['member_savings'] = round(sku_regular_price - sku_member_price, 2)
                except:
                    pass
    except Exception as e:
        product['skus'] = []
    
    return jsonify({'success': True, 'data': product})

# ============ 公告/通知系统 ============

@app.route('/api/notices', methods=['GET'])
def get_notices():
    """获取公告列表"""
    notice_type = request.args.get('type')
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    where = "status='published' AND deleted=0 AND (end_date IS NULL OR end_date >= CURDATE())"
    params = []
    if notice_type:
        where += " AND notice_type=%s"; params.append(notice_type)
    
    # 尝试从 business_notices 表获取，如果表不存在则返回空列表
    try:
        total = db.get_total("SELECT COUNT(*) FROM business_notices WHERE " + where, params)
        offset = (page - 1) * page_size
        notices = db.get_all(
            "SELECT id, title, content, notice_type, importance, created_at, end_date "
            "FROM business_notices WHERE " + where + " ORDER BY importance DESC, created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': notices or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
    except Exception as e:
        # 表不存在时返回空列表
        logging.warning(f"公告表查询失败: {e}")
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}})

@app.route('/api/notices/<notice_id>', methods=['GET'])
def get_notice_detail(notice_id):
    """获取公告详情"""
    try:
        notice = db.get_one(
            "SELECT * FROM business_notices WHERE id=%s AND status='published' AND deleted=0",
            [notice_id]
        )
        if not notice:
            return jsonify({'success': False, 'msg': '公告不存在或已下架'})
        return jsonify({'success': True, 'data': notice})
    except Exception as e:
        logging.warning(f"公告详情查询失败: {e}")
        return jsonify({'success': False, 'msg': '公告不存在'})

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
        except:
            pass
        return jsonify({'success': True, 'msg': '支付成功'})
    except Exception as e:
        logging.error(f"支付预约失败: {e}")
        return jsonify({'success': False, 'msg': '支付失败，请重试'})

# ============ 评价功能 ============

@app.route('/api/user/reviews', methods=['GET'])
@require_login
def get_my_reviews(user):
    """获取我的评价列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)

    where = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    total = db.get_total("SELECT COUNT(*) FROM business_reviews WHERE " + where, params)
    offset = (page - 1) * page_size

    try:
        items = db.get_all(
            """SELECT id, target_type, target_id, target_name, rating, content, images,
                      reply, replied_at, created_at
               FROM business_reviews WHERE """ + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
    except Exception as e:
        logging.warning(f"评价列表查询失败: {e}")
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}})

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
    except Exception as e:
        logging.warning(f"评价列表查询失败: {e}")
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
            except Exception as e:
                logging.warning(f"更新评分缓存失败: {e}")
        
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

    except Exception as e:
        logging.warning(f"提交评价失败: {e}")
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
    except Exception as e:
        logging.warning(f"追评失败: {e}")
        return jsonify({'success': False, 'msg': '追评失败'})


@app.route('/api/reviews/stats', methods=['GET'])
def get_review_stats():
    """获取评价统计（公开接口）"""
    target_type = request.args.get('target_type')
    target_id = request.args.get('target_id')

    if not target_type or not target_id:
        return jsonify({'success': False, 'msg': '缺少评价对象参数'})

    try:
        # 基础统计
        stats = db.get_one("""
            SELECT 
                COUNT(*) as total,
                ROUND(AVG(rating), 1) as avg_rating,
                SUM(CASE WHEN rating=5 THEN 1 ELSE 0 END) as rating_5,
                SUM(CASE WHEN rating=4 THEN 1 ELSE 0 END) as rating_4,
                SUM(CASE WHEN rating=3 THEN 1 ELSE 0 END) as rating_3,
                SUM(CASE WHEN rating=2 THEN 1 ELSE 0 END) as rating_2,
                SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END) as rating_1,
                SUM(CASE WHEN images IS NOT NULL AND images != '' THEN 1 ELSE 0 END) as has_images
            FROM business_reviews 
            WHERE target_type=%s AND target_id=%s AND deleted=0
        """, [target_type, target_id])

        return jsonify({'success': True, 'data': {
            'total': stats.get('total', 0) or 0,
            'avg_rating': float(stats.get('avg_rating', 0) or 0),
            'rating_distribution': {
                '5': stats.get('rating_5', 0) or 0,
                '4': stats.get('rating_4', 0) or 0,
                '3': stats.get('rating_3', 0) or 0,
                '2': stats.get('rating_2', 0) or 0,
                '1': stats.get('rating_1', 0) or 0,
            },
            'has_images': stats.get('has_images', 0) or 0
        }})
    except Exception as e:
        logging.warning(f"评价统计查询失败: {e}")
        return jsonify({'success': True, 'data': {'total': 0, 'avg_rating': 0, 'rating_distribution': {}, 'has_images': 0}})

# ============ 搜索历史功能 ============

@app.route('/api/user/search/history', methods=['GET'])
@require_login
def get_user_search_history(user):
    """获取我的搜索历史"""
    search_type = request.args.get('type')  # venue/shop/product
    limit = min(int(request.args.get('limit', 10)), 20)
    
    where = "user_id=%s"
    params = [user['user_id']]
    if search_type:
        where += " AND search_type=%s"
        params.append(search_type)
    
    try:
        items = db.get_all(
            """SELECT keyword, search_type, MAX(created_at) as last_searched 
               FROM business_search_history WHERE """ + where + 
            """ GROUP BY keyword, search_type ORDER BY last_searched DESC LIMIT %s""",
            params + [limit]
        )
        return jsonify({'success': True, 'data': {'items': items or []}})
    except Exception as e:
        # 表可能不存在，返回空列表
        return jsonify({'success': True, 'data': {'items': []}})


@app.route('/api/user/search/history', methods=['POST'])
@require_login
def add_search_history(user):
    """添加搜索历史"""
    data = request.get_json() or {}
    keyword = data.get('keyword', '').strip()
    search_type = data.get('type', 'product')  # 默认搜索商品
    
    if not keyword or len(keyword) > 50:
        return jsonify({'success': False, 'msg': '关键词无效'})
    
    try:
        # 检查是否已存在（更新搜索时间）
        existing = db.get_one(
            "SELECT id FROM business_search_history WHERE user_id=%s AND keyword=%s",
            [user['user_id'], keyword]
        )
        if existing:
            db.execute(
                "UPDATE business_search_history SET created_at=NOW() WHERE id=%s",
                [existing['id']]
            )
        else:
            db.execute(
                """INSERT INTO business_search_history (user_id, keyword, search_type) 
                   VALUES (%s, %s, %s)""",
                [user['user_id'], keyword, search_type]
            )
        
        # 保留最近20条搜索历史
        db.execute(
            """DELETE FROM business_search_history 
               WHERE user_id=%s AND id NOT IN (
                   SELECT id FROM (
                       SELECT id FROM business_search_history 
                       WHERE user_id=%s ORDER BY created_at DESC LIMIT 20
                   ) AS t
               )""",
            [user['user_id'], user['user_id']]
        )
        
        return jsonify({'success': True})
    except Exception as e:
        # 表可能不存在，忽略错误
        return jsonify({'success': True})


@app.route('/api/user/search/history', methods=['DELETE'])
@require_login
def clear_user_search_history(user):
    """清空搜索历史"""
    try:
        db.execute("DELETE FROM business_search_history WHERE user_id=%s", [user['user_id']])
        return jsonify({'success': True, 'msg': '搜索历史已清空'})
    except Exception as e:
        return jsonify({'success': True, 'msg': '搜索历史已清空'})


@app.route('/api/search/hot', methods=['GET'])
def get_hot_keywords():
    """获取热门搜索关键词"""
    search_type = request.args.get('type', 'product')
    
    try:
        items = db.get_all("""
            SELECT keyword, COUNT(*) as cnt 
            FROM business_search_history 
            WHERE search_type=%s 
            GROUP BY keyword 
            ORDER BY cnt DESC 
            LIMIT 10
        """, [search_type])
        return jsonify({'success': True, 'data': {'items': items or []}})
    except Exception as e:
        return jsonify({'success': True, 'data': {'items': []}})


# ============ 收藏功能 ============

@app.route('/api/user/favorites', methods=['GET'])
@require_login
def get_my_favorites(user):
    """获取我的收藏列表"""
    target_type = request.args.get('type')  # venue/shop/product
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    where = "user_id=%s"
    params = [user['user_id']]
    if target_type:
        where += " AND target_type=%s"
        params.append(target_type)
    
    total = db.get_total("SELECT COUNT(*) FROM business_favorites WHERE " + where, params)
    offset = (page - 1) * page_size
    
    items = db.get_all(
        """SELECT id, target_type, target_id, created_at 
           FROM business_favorites WHERE """ + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    
    # 补充收藏对象的详细信息
    for item in items or []:
        try:
            if item['target_type'] == 'venue':
                detail = db.get_one("SELECT venue_name, price, images FROM business_venues WHERE id=%s", [item['target_id']])
                if detail:
                    item['target_name'] = detail.get('venue_name', '')
                    item['price'] = detail.get('price')
                    item['images'] = detail.get('images')
            elif item['target_type'] == 'shop':
                detail = db.get_one("SELECT shop_name, address, phone FROM business_shops WHERE id=%s", [item['target_id']])
                if detail:
                    item['target_name'] = detail.get('shop_name', '')
                    item['address'] = detail.get('address')
                    item['phone'] = detail.get('phone')
            elif item['target_type'] == 'product':
                detail = db.get_one("SELECT product_name, price, images FROM business_products WHERE id=%s", [item['target_id']])
                if detail:
                    item['target_name'] = detail.get('product_name', '')
                    item['price'] = detail.get('price')
                    item['images'] = detail.get('images')
        except:
            pass
    
    return jsonify({'success': True, 'data': {
        'items': items or [],
        'total': total,
        'page': page,
        'page_size': page_size
    }})


@app.route('/api/user/favorites', methods=['POST'])
@require_login
def add_favorite(user):
    """添加收藏"""
    data = request.get_json() or {}
    target_type = data.get('target_type')  # venue/shop/product
    target_id = data.get('target_id')
    
    if target_type not in ('venue', 'shop', 'product'):
        return jsonify({'success': False, 'msg': '收藏对象类型无效'})
    if not target_id:
        return jsonify({'success': False, 'msg': '收藏对象ID不能为空'})
    
    # 获取对象名称
    target_name = ''
    if target_type == 'venue':
        obj = db.get_one("SELECT venue_name FROM business_venues WHERE id=%s AND deleted=0", [target_id])
        target_name = obj.get('venue_name', '') if obj else ''
    elif target_type == 'shop':
        obj = db.get_one("SELECT shop_name FROM business_shops WHERE id=%s AND deleted=0", [target_id])
        target_name = obj.get('shop_name', '') if obj else ''
    elif target_type == 'product':
        obj = db.get_one("SELECT product_name FROM business_products WHERE id=%s AND deleted=0", [target_id])
        target_name = obj.get('product_name', '') if obj else ''
    
    if not target_name:
        return jsonify({'success': False, 'msg': '收藏对象不存在或已下架'})
    
    existing = db.get_one(
        "SELECT id FROM business_favorites WHERE user_id=%s AND target_type=%s AND target_id=%s",
        [user['user_id'], target_type, target_id]
    )

    try:
        db.execute(
            """INSERT INTO business_favorites (user_id, user_name, target_type, target_id, target_name, ec_id, project_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE target_name=%s""",
            [user['user_id'], user.get('user_name', ''), target_type, target_id, target_name,
             user.get('ec_id'), user.get('project_id'), target_name]
        )
        if target_type == 'product' and not existing:
            bump_product_counter(target_id, 'favorite_count', 1)
        invalidate_user_cache(user['user_id'])
        return jsonify({'success': True, 'msg': '收藏成功'})
    except Exception as e:
        logging.warning(f"添加收藏失败: {e}")
        return jsonify({'success': False, 'msg': '收藏失败'})



@app.route('/api/user/favorites/<target_type>/<target_id>', methods=['DELETE'])
@require_login
def remove_favorite(user, target_type, target_id):
    """取消收藏"""
    if target_type not in ('venue', 'shop', 'product'):
        return jsonify({'success': False, 'msg': '收藏对象类型无效'})

    existing = db.get_one(
        "SELECT id FROM business_favorites WHERE user_id=%s AND target_type=%s AND target_id=%s",
        [user['user_id'], target_type, target_id]
    )
    if not existing:
        return jsonify({'success': True, 'msg': '已取消收藏'})
    
    db.execute(
        "DELETE FROM business_favorites WHERE user_id=%s AND target_type=%s AND target_id=%s",
        [user['user_id'], target_type, target_id]
    )
    if target_type == 'product':
        bump_product_counter(target_id, 'favorite_count', -1)
    invalidate_user_cache(user['user_id'])
    return jsonify({'success': True, 'msg': '已取消收藏'})



@app.route('/api/user/favorites/check', methods=['GET'])
@require_login
def check_favorite(user):
    """检查是否已收藏"""
    target_type = request.args.get('type')
    target_id = request.args.get('id')
    
    if not target_type or not target_id:
        return jsonify({'success': True, 'data': {'is_favorite': False}})
    
    exists = db.get_one(
        "SELECT id FROM business_favorites WHERE user_id=%s AND target_type=%s AND target_id=%s",
        [user['user_id'], target_type, target_id]
    )
    return jsonify({'success': True, 'data': {'is_favorite': bool(exists)}})


# ============ 浏览足迹功能 ============

@app.route('/api/user/recently-viewed', methods=['GET'])
@require_login
def get_recently_viewed(user):
    """V27.0: 获取用户浏览足迹列表"""
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 50)
    view_type = request.args.get('type')  # 可选: product/venue/shop
    
    where = "user_id=%s"
    params = [user['user_id']]
    
    if view_type:
        where += " AND view_type=%s"
        params.append(view_type)
    
    # 查询总数
    total = db.get_total(f"SELECT COUNT(*) FROM business_recently_viewed WHERE {where}", params)
    
    # 分页查询
    offset = (page - 1) * page_size
    items = db.get_all(f"""
        SELECT id, view_type, target_id, target_name, target_image, target_price, viewed_at
        FROM business_recently_viewed 
        WHERE {where}
        ORDER BY viewed_at DESC 
        LIMIT %s OFFSET %s
    """, params + [page_size, offset])
    
    return jsonify({'success': True, 'data': {
        'items': items or [],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})


@app.route('/api/user/recently-viewed', methods=['POST'])
@require_login
def add_recently_viewed(user):
    """V27.0: 添加浏览足迹（内部接口，供商品/场馆详情页调用）"""
    data = request.get_json() or {}
    view_type = data.get('view_type')
    target_id = data.get('target_id')
    target_name = data.get('target_name', '')
    target_image = data.get('target_image', '')
    target_price = data.get('target_price')
    
    if not view_type or not target_id:
        return jsonify({'success': False, 'msg': '参数不完整'})
    
    if view_type not in ('product', 'venue', 'shop'):
        return jsonify({'success': False, 'msg': '无效的浏览类型'})
    
    try:
        # 使用 REPLACE INTO 实现 upsert：如果已存在则更新浏览时间
        db.execute("""
            INSERT INTO business_recently_viewed 
            (user_id, view_type, target_id, target_name, target_image, target_price, viewed_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
            target_name = VALUES(target_name),
            target_image = VALUES(target_image),
            target_price = VALUES(target_price),
            viewed_at = NOW()
        """, [user['user_id'], view_type, target_id, target_name, target_image, target_price])
        
        return jsonify({'success': True, 'msg': '足迹已记录'})
    except Exception as e:
        logging.warning(f"记录浏览足迹失败: {e}")
        return jsonify({'success': False, 'msg': '记录失败'})


@app.route('/api/user/recently-viewed', methods=['DELETE'])
@require_login
def clear_recently_viewed(user):
    """V27.0: 清空浏览足迹"""
    view_type = request.args.get('type')  # 可选: product/venue/shop，不传则清空全部
    
    try:
        if view_type:
            db.execute(
                "DELETE FROM business_recently_viewed WHERE user_id=%s AND view_type=%s",
                [user['user_id'], view_type]
            )
        else:
            db.execute(
                "DELETE FROM business_recently_viewed WHERE user_id=%s",
                [user['user_id']]
            )
        return jsonify({'success': True, 'msg': '已清空浏览足迹'})
    except Exception as e:
        logging.warning(f"清空浏览足迹失败: {e}")
        return jsonify({'success': False, 'msg': '清空失败'})


@app.route('/api/user/recently-viewed/<int:record_id>', methods=['DELETE'])
@require_login
def delete_recently_viewed_item(user, record_id):
    """V27.0: 删除单条浏览足迹"""
    try:
        result = db.execute(
            "DELETE FROM business_recently_viewed WHERE id=%s AND user_id=%s",
            [record_id, user['user_id']]
        )
        return jsonify({'success': True, 'msg': '已删除'})
    except Exception as e:
        logging.warning(f"删除浏览足迹失败: {e}")
        return jsonify({'success': False, 'msg': '删除失败'})


@app.route('/api/user/achievements', methods=['GET'])
@require_login
def get_my_achievements(user):
    """V27.0: 获取用户成就列表"""
    # 获取所有成就定义
    achievements = db.get_all("""
        SELECT id, code, name, description, icon, category, condition_type, 
               condition_value, points_reward, badge_level, sort_order
        FROM business_achievements 
        WHERE status=1 
        ORDER BY sort_order, id
    """) or []
    
    # 获取用户已解锁的成就
    unlocked = db.get_all("""
        SELECT achievement_code, achievement_name, badge_icon, points_earned, earned_at
        FROM business_user_achievements 
        WHERE user_id=%s
    """, [user['user_id']]) or []
    
    unlocked_codes = {u['achievement_code'] for u in unlocked}
    
    # 构建返回数据
    result = []
    for ach in achievements:
        is_unlocked = ach['code'] in unlocked_codes
        user_ach = next((u for u in unlocked if u['achievement_code'] == ach['code']), None)
        
        result.append({
            'code': ach['code'],
            'name': ach['name'],
            'description': ach['description'],
            'icon': ach['icon'],
            'category': ach['category'],
            'badge_level': ach['badge_level'],
            'condition_type': ach['condition_type'],
            'condition_value': ach['condition_value'],
            'points_reward': ach['points_reward'],
            'is_unlocked': is_unlocked,
            'earned_at': user_ach['earned_at'] if user_ach else None
        })
    
    return jsonify({'success': True, 'data': {
        'achievements': result,
        'unlocked_count': len(unlocked_codes),
        'total_count': len(achievements)
    }})


@app.route('/api/user/checkin/rewards-config', methods=['GET'])
def get_checkin_rewards_config():
    """V27.0: 获取签到连续奖励配置"""
    configs = db.get_all("""
        SELECT streak_days, base_points, bonus_points, bonus_type, bonus_threshold, description
        FROM business_checkin_rewards_config 
        WHERE status=1 
        ORDER BY streak_days
    """) or []
    return jsonify({'success': True, 'data': configs})


# ============ 优惠券功能 ============

@app.route('/api/user/coupons/validate', methods=['POST'])
@require_login
def validate_coupon(user):
    """验证优惠券是否可用（用于下单时）"""
    data = request.get_json() or {}
    coupon_code = data.get('coupon_code', '').strip().upper()
    order_amount = float(data.get('order_amount', 0))
    
    if not coupon_code:
        return jsonify({'success': False, 'msg': '请输入优惠券码'})
    if order_amount <= 0:
        return jsonify({'success': False, 'msg': '订单金额无效'})
    
    try:
        # 查询用户拥有的未使用优惠券
        coupon = db.get_one("""
            SELECT uc.id as user_coupon_id, uc.coupon_code, uc.status,
                   c.id as coupon_id, c.coupon_name, c.coupon_type, c.discount_value, 
                   c.min_amount, c.max_discount, c.valid_from, c.valid_until
            FROM business_user_coupons uc
            LEFT JOIN business_coupons c ON uc.coupon_id = c.id
            WHERE uc.user_id=%s AND uc.coupon_code=%s AND uc.status='unused'
        """, [user['user_id'], coupon_code])
        
        if not coupon:
            return jsonify({'success': False, 'msg': '优惠券不存在或不可用'})
        
        # 检查状态
        if coupon.get('status') != 'unused':
            status_map = {'used': '已使用', 'expired': '已过期'}
            return jsonify({'success': False, 'msg': f"优惠券{status_map.get(coupon.get('status'), coupon.get('status'))}"})
        
        # 检查有效期
        from datetime import date
        today = date.today()
        if coupon.get('valid_from') and today < coupon['valid_from']:
            return jsonify({'success': False, 'msg': '优惠券尚未开始'})
        if coupon.get('valid_until') and today > coupon['valid_until']:
            return jsonify({'success': False, 'msg': '优惠券已过期'})
        
        # 检查最低消费
        min_amount = float(coupon.get('min_amount', 0) or 0)
        if order_amount < min_amount:
            return jsonify({'success': False, 'msg': f'订单金额需满{min_amount}元才可使用'})
        
        # 计算优惠金额
        discount = 0
        coupon_type = coupon.get('coupon_type')
        discount_value = float(coupon.get('discount_value', 0) or 0)
        
        if coupon_type == 'cash':
            discount = discount_value
        elif coupon_type == 'discount':
            discount = order_amount * (1 - discount_value)
            max_discount = float(coupon.get('max_discount') or 0)
            if max_discount > 0 and discount > max_discount:
                discount = max_discount
        # points类型不支持抵扣订单金额
        
        return jsonify({'success': True, 'data': {
            'coupon_id': coupon.get('coupon_id'),
            'user_coupon_id': coupon.get('user_coupon_id'),
            'coupon_name': coupon.get('coupon_name'),
            'coupon_type': coupon_type,
            'discount': round(discount, 2),
            'final_amount': round(order_amount - discount, 2)
        }})
    except Exception as e:
        logging.warning(f"优惠券验证失败: {e}")
        return jsonify({'success': False, 'msg': '优惠券验证失败'})


@app.route('/api/user/coupons', methods=['GET'])
@require_login
def get_my_coupons(user):
    """获取我的优惠券"""
    status = request.args.get('status', 'unused')  # unused/used/expired
    
    where = "uc.user_id=%s AND uc.status=%s"
    params = [user['user_id'], status]
    
    items = db.get_all(
        """SELECT uc.id, uc.coupon_code, uc.status, uc.used_at,
                  c.coupon_name, c.coupon_type, c.discount_amount as discount_value, c.min_amount, c.max_discount,
                  c.valid_from, c.valid_to as valid_until
           FROM business_user_coupons uc
           LEFT JOIN business_coupons c ON uc.coupon_id = c.id
           WHERE """ + where + " ORDER BY uc.received_at DESC",
        params
    )
    
    return jsonify({'success': True, 'data': {'items': items or []}})


@app.route('/api/user/coupons/exchange', methods=['POST'])
@require_login
def exchange_coupon(user):
    """积分兑换优惠券"""
    data = request.get_json() or {}
    coupon_id = data.get('coupon_id')
    
    if not coupon_id:
        return jsonify({'success': False, 'msg': '请选择要兑换的优惠券'})
    
    # 获取优惠券信息
    coupon = db.get_one(
        "SELECT * FROM business_coupons WHERE id=%s AND status='active'", 
        [coupon_id]
    )
    if not coupon:
        return jsonify({'success': False, 'msg': '优惠券不存在或已下架'})
    
    # 检查库存
    if coupon.get('total_count', 0) > 0 and coupon.get('used_count', 0) >= coupon.get('total_count', 0):
        return jsonify({'success': False, 'msg': '优惠券已领完'})
    
    # 检查有效期
    from datetime import date
    today = date.today()
    if coupon.get('valid_from') and today < coupon['valid_from']:
        return jsonify({'success': False, 'msg': '优惠券尚未开始发放'})
    if coupon.get('valid_until') and today > coupon['valid_until']:
        return jsonify({'success': False, 'msg': '优惠券已过期'})
    
    points_cost = coupon.get('points_cost', 0)
    
    # 获取用户积分
    member = db.get_one("SELECT points FROM business_members WHERE user_id=%s", [user['user_id']])
    if not member or (member.get('points', 0) < points_cost):
        return jsonify({'success': False, 'msg': f'积分不足，需要{points_cost}积分'})
    
    # 执行兑换
    import uuid
    coupon_code = uuid.uuid4().hex[:12].upper()
    
    conn = db.get_db()
    try:
        cursor = conn.cursor()
        conn.begin()
        
        # 扣减积分
        cursor.execute(
            "UPDATE business_members SET points=points-%s WHERE user_id=%s",
            [points_cost, user['user_id']]
        )
        
        # 记录积分日志
        cursor.execute(
            """INSERT INTO business_points_log (user_id, user_name, log_type, points, balance_after, description, ec_id, project_id)
               SELECT %s, %s, 'exchange', -%s, points, %s, %s, %s FROM business_members WHERE user_id=%s""",
            [user['user_id'], user.get('user_name', ''), points_cost, f'兑换优惠券：{coupon["coupon_name"]}',
             user.get('ec_id'), user.get('project_id'), user['user_id']]
        )
        
        # 发放优惠券
        cursor.execute(
            """INSERT INTO business_user_coupons (coupon_id, user_id, coupon_code, ec_id, project_id)
               VALUES (%s, %s, %s, %s, %s)""",
            [coupon_id, user['user_id'], coupon_code, user.get('ec_id'), user.get('project_id')]
        )
        
        # 更新已发放数量
        cursor.execute(
            "UPDATE business_coupons SET used_count=used_count+1 WHERE id=%s",
            [coupon_id]
        )
        
        conn.commit()
        return jsonify({'success': True, 'msg': '兑换成功', 'data': {'coupon_code': coupon_code}})
    except Exception as e:
        conn.rollback()
        logging.error(f"兑换优惠券失败: {e}")
        return jsonify({'success': False, 'msg': '兑换失败'})
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


@app.route('/api/coupons/available', methods=['GET'])
def get_available_coupons():
    """获取可兑换的优惠券列表（公开接口）"""
    from datetime import date
    today = date.today()
    
    items = db.get_all(
        """SELECT id, coupon_name, coupon_type, discount_value, min_amount, max_discount,
                  points_cost, total_count, used_count, valid_from, valid_until
           FROM business_coupons 
           WHERE status='active' 
             AND (valid_from IS NULL OR valid_from <= %s)
             AND (valid_until IS NULL OR valid_until >= %s)
             AND (total_count = 0 OR used_count < total_count)
           ORDER BY points_cost ASC""",
        [today, today]
    )
    
    return jsonify({'success': True, 'data': {'items': items or []}})


# ============ 通知系统 ============

@app.route('/api/user/notifications', methods=['GET'])
@require_login
def get_user_notifications(user):
    """获取用户通知列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    is_read = request.args.get('is_read')
    notify_type = request.args.get('type')
    
    if is_read is not None:
        is_read = is_read == 'true' or is_read == '1'
    
    result = notification.get_user_notifications(
        user['user_id'], page, page_size, is_read, notify_type
    )
    return jsonify({'success': True, 'data': result})


@app.route('/api/user/notifications/unread-count', methods=['GET'])
@require_login
def get_unread_count(user):
    """获取未读通知数量"""
    count = db.get_total(
        "SELECT COUNT(*) FROM business_notifications WHERE user_id=%s AND is_read=0 AND deleted=0",
        [user['user_id']]
    )
    return jsonify({'success': True, 'data': {'count': count}})


@app.route('/api/user/notifications/<nid>/read', methods=['POST'])
@require_login
def mark_notification_read(user, nid):
    """标记通知已读"""
    notification.mark_as_read(nid, user['user_id'])
    return jsonify({'success': True, 'msg': '已标记为已读'})


@app.route('/api/user/notifications/read-all', methods=['POST'])
@require_login
def mark_all_notifications_read(user):
    """全部标记已读（支持按类型）"""
    data = request.get_json() or {}
    notify_type = data.get('type', '').strip()
    uid = user['user_id']
    try:
        if notify_type:
            db.execute(
                "UPDATE business_notifications SET is_read=1, read_at=NOW() WHERE user_id=%s AND notify_type=%s AND is_read=0 AND deleted=0",
                [uid, notify_type]
            )
        else:
            notification.mark_all_as_read(uid)
        invalidate_user_cache(uid)
    except Exception as e:
        logging.warning(f"批量标已读失败: {e}")
    return jsonify({'success': True, 'msg': '全部已读'})


@app.route('/api/user/notifications/unread-counts', methods=['GET'])
@require_login
def get_unread_counts_by_type(user):
    """V31.0: 获取各类型未读消息数（用于分类角标展示）"""
    uid = user['user_id']
    try:
        rows = db.get_all(
            """SELECT notify_type, COUNT(*) as cnt 
               FROM business_notifications 
               WHERE user_id=%s AND is_read=0 AND deleted=0 
               GROUP BY notify_type""",
            [uid]
        ) or []
        counts = {r['notify_type']: r['cnt'] for r in rows if r.get('notify_type')}
        return jsonify({'success': True, 'data': counts})
    except Exception as e:
        logging.warning(f"获取分类未读数失败: {e}")
        return jsonify({'success': True, 'data': {}})


# ============ 意见反馈 ============

@app.route('/api/user/feedback', methods=['GET'])
@require_login
def get_my_feedback(user):
    """获取我的反馈列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    where = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    total = db.get_total("SELECT COUNT(*) FROM business_feedback WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id, feedback_type, title, content, status, reply, replied_at, created_at "
        "FROM business_feedback WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items or [], 'total': total, 'page': page, 'page_size': page_size
    }})


@app.route('/api/user/feedback', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=5, window_seconds=60)
def create_feedback(user):
    """提交意见反馈"""
    data = request.get_json() or {}
    feedback_type = data.get('feedback_type', 'suggestion')
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    contact = data.get('contact', '').strip()
    images = data.get('images', [])
    
    if not title or not content:
        return jsonify({'success': False, 'msg': '标题和内容不能为空'})
    if len(title) > 100:
        return jsonify({'success': False, 'msg': '标题不能超过100字'})
    if len(content) > 2000:
        return jsonify({'success': False, 'msg': '内容不能超过2000字'})
    if feedback_type not in ('suggestion', 'bug', 'complaint', 'praise'):
        feedback_type = 'suggestion'
    
    import html as html_mod
    title = html_mod.escape(title)
    content = html_mod.escape(content)
    
    try:
        db.execute(
            """INSERT INTO business_feedback 
               (user_id, user_name, feedback_type, title, content, contact, images, ec_id, project_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [user['user_id'], user.get('user_name', ''), feedback_type, title, content,
             contact, json.dumps(images), user.get('ec_id'), user.get('project_id')]
        )
        return jsonify({'success': True, 'msg': '反馈提交成功，感谢您的意见！'})
    except Exception as e:
        logging.error(f"提交反馈失败: {e}")
        return jsonify({'success': False, 'msg': '反馈提交失败'})


# ============ 支付接口(使用支付服务框架) ============

@app.route('/api/user/payments/create', methods=['POST'])
@require_login
def create_payment(user):
    """创建支付单 - P13修复：服务端金额校验"""
    data = request.get_json() or {}
    order_type = data.get('order_type')  # booking / order
    order_id = data.get('order_id')
    client_amount = float(data.get('amount', 0))
    
    if not order_type or not order_id or client_amount <= 0:
        return jsonify({'success': False, 'msg': '参数不完整'})
    
    # P13新增：服务端金额校验，防止客户端篡改
    try:
        if order_type == 'order':
            # 从订单表获取实际应付金额
            order = db.get_one(
                "SELECT actual_amount, order_status FROM business_orders WHERE id=%s AND user_id=%s AND ec_id=%s",
                [order_id, user['user_id'], user.get('ec_id')]
            )
            if not order:
                return jsonify({'success': False, 'msg': '订单不存在'})
            if order['order_status'] == 'paid':
                return jsonify({'success': False, 'msg': '订单已支付'})
            actual_amount = float(order['actual_amount'] or 0)
            
        elif order_type == 'booking':
            # 从预约表获取实际应付金额
            booking = db.get_one(
                "SELECT total_price, status, pay_status FROM business_venue_bookings WHERE id=%s AND user_id=%s AND ec_id=%s",
                [order_id, user['user_id'], user.get('ec_id')]
            )
            if not booking:
                return jsonify({'success': False, 'msg': '预约不存在'})
            if booking['pay_status'] == 'paid':
                return jsonify({'success': False, 'msg': '预约已支付'})
            actual_amount = float(booking['total_price'] or 0)
        else:
            return jsonify({'success': False, 'msg': '不支持的订单类型'})
        
        # 金额校验：允许浮点数精度误差 0.01元
        if abs(client_amount - actual_amount) > 0.01:
            logging.warning(f"支付金额校验失败: client={client_amount}, actual={actual_amount}, order_id={order_id}")
            return jsonify({'success': False, 'msg': '金额校验失败，请刷新页面重试'})
            
    except Exception as e:
        logging.error(f"金额校验异常: {e}")
        return jsonify({'success': False, 'msg': '金额校验失败'})
    
    return jsonify(payment_service.payment.create_payment(
        order_type=order_type,
        order_id=order_id,
        amount=actual_amount,  # 使用服务端计算的金额
        user_id=user['user_id'],
        user_name=user.get('user_name', ''),
        channel='mock',
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    ))


@app.route('/api/user/payments/<pay_no>/confirm', methods=['POST'])
@require_login
def confirm_payment(user, pay_no):
    """确认支付"""
    return jsonify(payment_service.payment.confirm_payment(pay_no))


@app.route('/api/user/payments/<pay_no>', methods=['GET'])
@require_login
def get_payment_status(user, pay_no):
    """查询支付状态"""
    return jsonify(payment_service.payment.get_payment_status(pay_no))


# ============ V29.0 新增: 支付回调接口 ============

@app.route('/api/payment/callback/wechat', methods=['POST'])
def wechat_payment_callback():
    """
    微信支付回调接口
    V29.0 新增：完善回调处理逻辑
    """
    try:
        import json as json_mod
        data = request.get_json()

        if not data:
            return jsonify({'code': 'FAIL', 'message': '无效的回调数据'})

        # 获取签名头
        signature = request.headers.get('Wechatpay-Signature', '')
        timestamp = request.headers.get('Wechatpay-Timestamp', '')
        nonce = request.headers.get('Wechatpay-Nonce', '')

        # 验证并处理回调
        result = payment_service.payment.handle_payment_callback(
            'wechat',
            data,
            wechat_signature=signature,
            wechat_timestamp=timestamp,
            wechat_nonce=nonce
        )

        if result.get('success'):
            return jsonify({'code': 'SUCCESS', 'message': '处理成功'})
        else:
            return jsonify({'code': 'FAIL', 'message': result.get('msg', '处理失败')})

    except Exception as e:
        logging.error(f"微信支付回调处理异常: {e}")
        return jsonify({'code': 'FAIL', 'message': '系统异常'})


@app.route('/api/payment/callback/alipay', methods=['POST'])
def alipay_payment_callback():
    """
    支付宝支付回调接口
    V29.0 新增：完善回调处理逻辑
    """
    try:
        data = request.form.to_dict()

        if not data:
            return 'fail'

        # 处理回调
        result = payment_service.payment.handle_payment_callback(
            'alipay',
            data
        )

        if result.get('success'):
            return 'success'
        else:
            return 'fail'

    except Exception as e:
        logging.error(f"支付宝支付回调处理异常: {e}")
        return 'fail'


@app.route('/api/user/payments/<pay_no>/query', methods=['GET'])
@require_login
def query_external_payment(user, pay_no):
    """
    V29.0 新增: 查询外部支付渠道状态
    """
    return jsonify(payment_service.payment.query_external_payment(pay_no))


@app.route('/api/user/payments/<pay_no>/logs', methods=['GET'])
@require_login
def get_payment_logs(user, pay_no):
    """
    V29.0 新增: 获取支付操作日志
    """
    return jsonify(payment_service.payment.get_payment_logs(pay_no))


# ============ V29.0 新增: 物流回调接口 ============

@app.route('/api/logistics/callback/subscribe', methods=['POST'])
def logistics_subscribe_callback():
    """
    物流订阅回调接口
    V29.0 新增：处理快递100订阅推送
    """
    try:
        data = request.form.to_dict() or request.get_json() or {}

        result = logistics_service.logistics.handle_subscribe_callback(data)

        if result.get('success'):
            return jsonify({'success': True, 'message': '处理成功'})
        else:
            return jsonify({'success': False, 'message': result.get('msg', '处理失败')})

    except Exception as e:
        logging.error(f"物流订阅回调处理异常: {e}")
        return jsonify({'success': False, 'message': '系统异常'})


# ============ 健康检查 ============

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'user-h5', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})


@app.route('/api/health/detailed')
def health_detailed():
    """V17.0新增：详细健康检查接口"""
    try:
        from business_common.health_check import HealthCheck
        checker = HealthCheck()
        result = checker.get_summary()
        return jsonify({
            'success': True,
            'data': result
        })
    except ImportError:
        return jsonify({
            'success': True,
            'data': {
                'status': 'healthy',
                'message': '健康检查模块不可用'
            }
        })
    except Exception as e:
        logging.warning(f"健康检查失败: {e}")
        return jsonify({
            'success': True,
            'data': {
                'status': 'degraded',
                'message': f'健康检查异常: {str(e)}'
            }
        })



# ============ 下单功能 ============

@app.route('/api/user/orders', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def create_order(user):
    """P13优化：创建订单（支持从购物车下单或直接下单）
    V37.0增强：支持积分抵扣"""
    data = request.get_json() or {}
    order_type = data.get('order_type', 'product')  # product / service
    items = data.get('items', [])   # [{product_id, quantity}]
    cart_ids = data.get('cart_ids', [])  # 从购物车下单时传购物车ID列表
    coupon_code = data.get('coupon_code', '').strip()
    remark = data.get('remark', '').strip()
    # V37.0: 积分抵扣
    use_points = abs(int(data.get('use_points', 0)))

    uid = user['user_id']

    # 整理商品列表（预校验商品存在性和状态）
    order_items = []
    if cart_ids:
        # 从购物车下单
        for cid in cart_ids:
            cart = db.get_one(
                """SELECT c.*, p.product_name, p.price, p.status as p_status
                   FROM business_cart c LEFT JOIN business_products p ON c.product_id=p.id
                   WHERE c.id=%s AND c.user_id=%s""",
                [cid, uid]
            )
            if cart and cart.get('p_status') == 'active':
                order_items.append({
                    'product_id': cart['product_id'],
                    'product_name': cart['product_name'],
                    'price': float(cart.get('price') or 0),
                    'quantity': int(cart.get('quantity') or 1)
                })
    elif items:
        # 直接下单
        for item in items:
            product = db.get_one(
                "SELECT id, product_name, price, status FROM business_products WHERE id=%s AND deleted=0",
                [item.get('product_id')]
            )
            if product and product.get('status') == 'active':
                order_items.append({
                    'product_id': product['id'],
                    'product_name': product['product_name'],
                    'price': float(product.get('price') or 0),
                    'quantity': max(1, int(item.get('quantity', 1)))
                })

    if not order_items:
        return jsonify({'success': False, 'msg': '没有可下单的商品'})

    # 计算总价（预计算，用于前端展示）
    total_amount = sum(i['price'] * i['quantity'] for i in order_items)
    actual_amount = total_amount
    coupon_discount = 0

    # 优惠券验证
    used_coupon_id = None
    if coupon_code:
        try:
            coupon = db.get_one("""
                SELECT uc.id as user_coupon_id, uc.coupon_id,
                       c.coupon_name, c.coupon_type, c.discount_value, c.min_amount, c.max_discount
                FROM business_user_coupons uc
                LEFT JOIN business_coupons c ON uc.coupon_id = c.id
                WHERE uc.user_id=%s AND uc.coupon_code=%s AND uc.status='unused'
            """, [uid, coupon_code])
            if coupon:
                min_amount = float(coupon.get('min_amount') or 0)
                if total_amount >= min_amount:
                    coupon_type = coupon.get('coupon_type')
                    dv = float(coupon.get('discount_value') or 0)
                    if coupon_type == 'cash':
                        coupon_discount = dv
                    elif coupon_type == 'discount':
                        coupon_discount = total_amount * (1 - dv)
                        max_d = float(coupon.get('max_discount') or 0)
                        if max_d > 0:
                            coupon_discount = min(coupon_discount, max_d)
                    actual_amount = max(0, total_amount - coupon_discount)
                    used_coupon_id = coupon.get('user_coupon_id')
        except Exception as e:
            logging.warning(f"优惠券应用失败: {e}")

    # V37.0: 积分抵扣处理
    points_deduction = 0
    if use_points > 0 and actual_amount > 0:
        try:
            # 获取用户积分
            member = db.get_one(
                "SELECT points FROM business_members WHERE user_id=%s",
                [uid]
            )
            if member:
                user_points = int(member.get('points', 0))
                # 积分兑换比例：100积分=1元
                points_rate = 100
                max_points_use = min(user_points, points_rate * actual_amount)
                use_points = min(use_points, max_points_use)
                points_deduction = use_points / points_rate
                actual_amount = max(0, actual_amount - points_deduction)
                logging.info(f"[Order] 积分抵扣: use_points={use_points}, deduction={points_deduction:.2f}")
        except Exception as e:
            logging.warning(f"积分抵扣处理失败: {e}")

    # V9.0：收货地址集成
    address_id = data.get('address_id')
    address_snapshot = None
    if address_id:
        addr = db.get_one(
            "SELECT * FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
            [address_id, uid]
        )
        if addr:
            address_snapshot = f"{addr.get('province','')}{addr.get('city','')}{addr.get('district','')}{addr.get('address','')}"
            if addr.get('contact_name'):
                address_snapshot = f"{addr['contact_name']} {addr.get('contact_phone','')} {address_snapshot}"

    # P13优化：库存校验与扣减在同一事务内，使用 FOR UPDATE 防止超卖
    order_no = utils.generate_no('ORD')
    conn = db.get_db()
    try:
        cursor = conn.cursor()
        conn.begin()

        # P13优化：收集所有需要锁定的商品ID
        product_ids = [item['product_id'] for item in order_items]
        placeholders = ','.join(['%s'] * len(product_ids))
        
        # 先锁定所有商品记录（按ID排序保证加锁顺序一致，防止死锁）
        cursor.execute(
            f"SELECT id, product_name, stock FROM business_products WHERE id IN ({placeholders}) AND deleted=0 ORDER BY id",
            product_ids
        )
        locked_products = {row['id']: row for row in cursor.fetchall()}
        
        # 校验库存并准备扣减
        for item in order_items:
            product_id = item['product_id']
            quantity = item['quantity']
            if product_id not in locked_products:
                conn.rollback()
                return jsonify({'success': False, 'msg': f"商品不存在: {item['product_name']}"})
            
            current_stock = int(locked_products[product_id].get('stock') or 0)
            if current_stock < quantity:
                conn.rollback()
                return jsonify({'success': False, 'msg': f"商品库存不足: {item['product_name']}（当前库存 {current_stock}，需要 {quantity}）"})

        # 创建订单
        now = datetime.now()
        expire_time = now + timedelta(minutes=ORDER_EXPIRE_MINUTES)
        cursor.execute(
            """INSERT INTO business_orders
               (order_no, order_type, user_id, user_name, user_phone, total_amount, actual_amount,
                discount_amount, points_deduction, order_status, pay_status, remark, shipping_address, ec_id, project_id,
                created_at, updated_at, expire_time)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending','unpaid',%s,%s,%s,%s,%s,%s,%s)""",
            [order_no, order_type, uid, user.get('user_name', ''), user.get('phone'),
             round(total_amount, 2), round(actual_amount, 2), round(coupon_discount, 2),
             round(points_deduction, 2),
             remark, address_snapshot or '', user.get('ec_id'), user.get('project_id'),
             now, now, expire_time]
        )
        order_id = cursor.lastrowid


        # 保存订单明细并扣减库存（使用带条件的UPDATE确保不会超卖）
        for item in order_items:
            cursor.execute(
                """INSERT INTO business_order_items (order_id, product_id, product_name, price, quantity, subtotal)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                [order_id, item['product_id'], item['product_name'],
                 item['price'], item['quantity'], round(item['price'] * item['quantity'], 2)]
            )
            # P13优化：带库存校验条件的库存扣减，防止超卖
            affected = cursor.execute(
                "UPDATE business_products SET stock=stock-%s, sales_count=sales_count+%s WHERE id=%s AND stock>=%s",
                [item['quantity'], item['quantity'], item['product_id'], item['quantity']]
            )
            if affected == 0:
                conn.rollback()
                logging.warning(f"库存扣减失败: product_id={item['product_id']}, quantity={item['quantity']}")
                return jsonify({'success': False, 'msg': f"商品库存不足: {item['product_name']}"})
            
            # 更新本地缓存的库存（用于后续校验，但实际校验已在SQL层面完成）
            latest_stock = int(locked_products[item['product_id']].get('stock') or 0)
            locked_products[item['product_id']]['stock'] = latest_stock - item['quantity']


        # 标记优惠券已使用
        if used_coupon_id:
            cursor.execute(
                "UPDATE business_user_coupons SET status='used', used_at=NOW() WHERE id=%s",
                [used_coupon_id]
            )

        # V37.0: 扣除用户积分
        if use_points > 0 and points_deduction > 0:
            cursor.execute(
                "UPDATE business_members SET points=points-%s WHERE user_id=%s",
                [use_points, uid]
            )
            # 记录积分变动日志
            cursor.execute(
                """INSERT INTO business_points_log
                   (user_id, points, change_type, change_reason, balance_before, balance_after, order_no,
                    ec_id, project_id, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                [uid, -use_points, 'order_deduction', f'订单抵扣', user_points - use_points, user_points - use_points,
                 order_no, user.get('ec_id'), user.get('project_id')]
            )
            logging.info(f"[Order] 积分已扣除: user_id={uid}, points={use_points}, order_no={order_no}")

        # 清除购物车（已下单的商品）
        if cart_ids:
            placeholders = ','.join(['%s'] * len(cart_ids))
            cursor.execute(
                f"DELETE FROM business_cart WHERE id IN ({placeholders}) AND user_id=%s",
                cart_ids + [uid]
            )

        conn.commit()

        try:
            push_service.send_message(
                template_code='order_created',
                user_id=uid,
                params={
                    'order_no': order_no,
                    'amount': f"{round(actual_amount, 2):.2f}",
                    'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S')
                },
                ec_id=user.get('ec_id'),
                project_id=user.get('project_id')
            )
        except Exception as push_err:
            logging.warning(f"下单提醒发送失败: {push_err}")

        return jsonify({'success': True, 'msg': '下单成功', 'data': {
            'order_id': order_id,
            'order_no': order_no,
            'total_amount': round(total_amount, 2),
            'actual_amount': round(actual_amount, 2),
            'discount_amount': round(coupon_discount, 2),
            'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S')
        }})

    except Exception as e:
        conn.rollback()
        logging.error(f"创建订单失败: {e}")
        return jsonify({'success': False, 'msg': '下单失败，请稍后重试'})
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# ============ 个人中心 ============

@app.route('/api/user/profile', methods=['GET'])
@require_login
def get_user_profile(user):
    """获取个人中心综合信息"""
    from business_common.user_service import get_user_service
    user_service = get_user_service()
    return jsonify(user_service.get_user_profile(user['user_id']))


@app.route('/api/user/notification-preferences', methods=['GET'])
@require_login
def get_notification_preferences(user):
    """获取用户通知偏好"""
    data = user_settings_service.get_notification_preferences(
        user_id=user['user_id'],
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    )
    return jsonify({'success': True, 'data': data})


@app.route('/api/user/notification-preferences', methods=['PUT'])
@require_login
def update_notification_preferences(user):
    """更新用户通知偏好"""
    payload = request.get_json() or {}
    allowed_fields = {
        'notif_order', 'notif_coupon', 'notif_system',
        'channel_in_app', 'channel_wechat', 'channel_sms', 'channel_email',
        'wechat_openid', 'email'
    }
    data = {k: payload.get(k) for k in allowed_fields if k in payload}
    if not data:
        latest = user_settings_service.get_notification_preferences(
            user_id=user['user_id'],
            ec_id=user.get('ec_id'),
            project_id=user.get('project_id')
        )
        return jsonify({'success': True, 'msg': '未检测到变更字段', 'data': latest})

    result = user_settings_service.update_notification_preferences(
        user_id=user['user_id'],
        data=data,
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    )
    return jsonify(result)


# ============ 用户收货地址管理 ============


@app.route('/api/user/addresses', methods=['GET'])
@require_login
def get_user_addresses(user):
    """获取用户收货地址列表"""
    uid = user['user_id']
    try:
        items = db.get_all(
            """SELECT id, user_name, phone, province, city, area, address, is_default, tag 
               FROM business_user_addresses WHERE user_id=%s AND deleted=0 ORDER BY is_default DESC, created_at DESC""",
            [uid]
        )
        return jsonify({'success': True, 'data': {'items': items or []}})
    except Exception as e:
        logging.warning(f"获取收货地址失败: {e}")
        return jsonify({'success': True, 'data': {'items': []}})


@app.route('/api/user/addresses', methods=['POST'])
@require_login
def create_address(user):
    """新增收货地址"""
    data = request.get_json() or {}
    user_name = data.get('user_name', '').strip()
    phone = data.get('phone', '').strip()
    province = data.get('province', '').strip()
    city = data.get('city', '').strip()
    area = data.get('area', '').strip()
    address = data.get('address', '').strip()
    is_default = int(data.get('is_default', 0))
    tag = data.get('tag', '').strip()
    
    if not user_name or not phone or not address:
        return jsonify({'success': False, 'msg': '请填写完整的收货信息'})
    if len(address) > 200:
        return jsonify({'success': False, 'msg': '详细地址不能超过200字'})
    
    # 校验手机号格式
    import re
    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({'success': False, 'msg': '请输入正确的手机号'})
    
    uid = user['user_id']
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        # 如果设为默认地址，先取消其他默认地址
        if is_default:
            db.execute(
                "UPDATE business_user_addresses SET is_default=0 WHERE user_id=%s AND deleted=0",
                [uid]
            )
        
        db.execute(
            """INSERT INTO business_user_addresses 
               (user_id, user_name, phone, province, city, area, address, is_default, tag, ec_id, project_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [uid, user_name, phone, province, city, area, address, is_default, tag, ec_id, project_id]
        )
        return jsonify({'success': True, 'msg': '地址添加成功'})
    except Exception as e:
        logging.warning(f"添加收货地址失败: {e}")
        return jsonify({'success': False, 'msg': '添加地址失败'})


@app.route('/api/user/addresses/<int:addr_id>', methods=['PUT'])
@require_login
def update_address(user, addr_id):
    """更新收货地址"""
    data = request.get_json() or {}
    user_name = data.get('user_name', '').strip()
    phone = data.get('phone', '').strip()
    province = data.get('province', '').strip()
    city = data.get('city', '').strip()
    area = data.get('area', '').strip()
    address = data.get('address', '').strip()
    is_default = data.get('is_default')
    tag = data.get('tag', '').strip()
    
    if not user_name or not phone or not address:
        return jsonify({'success': False, 'msg': '请填写完整的收货信息'})
    
    uid = user['user_id']
    
    # 验证地址归属
    check = db.get_one(
        "SELECT id FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
        [addr_id, uid]
    )
    if not check:
        return jsonify({'success': False, 'msg': '地址不存在'})
    
    try:
        # 如果设为默认地址，先取消其他默认地址
        if is_default:
            db.execute(
                "UPDATE business_user_addresses SET is_default=0 WHERE user_id=%s AND deleted=0",
                [uid]
            )
        
        db.execute(
            """UPDATE business_user_addresses 
               SET user_name=%s, phone=%s, province=%s, city=%s, area=%s, 
                   address=%s, is_default=%s, tag=%s, updated_at=NOW()
               WHERE id=%s AND user_id=%s""",
            [user_name, phone, province, city, area, address, 
             is_default if is_default is not None else 0, tag, addr_id, uid]
        )
        return jsonify({'success': True, 'msg': '地址更新成功'})
    except Exception as e:
        logging.warning(f"更新收货地址失败: {e}")
        return jsonify({'success': False, 'msg': '更新地址失败'})


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
        )
        return jsonify({'success': True, 'msg': '地址已删除'})
    except Exception as e:
        logging.warning(f"删除收货地址失败: {e}")
        return jsonify({'success': False, 'msg': '删除地址失败'})


@app.route('/api/user/addresses/<int:addr_id>/default', methods=['POST'])
@require_login
def set_default_address(user, addr_id):
    """设置默认收货地址"""
    uid = user['user_id']
    
    # 验证地址归属
    check = db.get_one(
        "SELECT id FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
        [addr_id, uid]
    )
    if not check:
        return jsonify({'success': False, 'msg': '地址不存在'})
    
    try:
        # 取消其他默认地址
        db.execute(
            "UPDATE business_user_addresses SET is_default=0 WHERE user_id=%s AND deleted=0",
            [uid]
        )
        # 设置新的默认地址
        db.execute(
            "UPDATE business_user_addresses SET is_default=1, updated_at=NOW() WHERE id=%s AND user_id=%s",
            [addr_id, uid]
        )
        return jsonify({'success': True, 'msg': '已设为默认地址'})
    except Exception as e:
        logging.warning(f"设置默认地址失败: {e}")
        return jsonify({'success': False, 'msg': '设置失败'})






@app.route('/api/user/orders/<int:order_id>/confirm', methods=['POST'])
@require_login
def confirm_order(user, order_id):
    """用户确认收货"""
    uid = user['user_id']
    order = db.get_one(
        "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
        [order_id, uid]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    status = order.get('order_status') or ''
    if status != 'shipped':
        return jsonify({'success': False, 'msg': '只有已发货的订单才可确认收货'})

    try:
        db.execute(
            "UPDATE business_orders SET order_status='completed', completed_at=NOW(), updated_at=NOW() WHERE id=%s",
            [order_id]
        )
        from business_common.cache_service import cache_delete
        cache_delete(f"user_stats_{uid}")
        return jsonify({'success': True, 'msg': '已确认收货'})
    except Exception as e:
        logging.warning(f"确认收货失败: {e}")
        return jsonify({'success': False, 'msg': '操作失败'})


# ============ V9.0 商品分类与排序 ============

@app.route('/api/user/products/categories', methods=['GET'])
def get_product_categories():
    """获取商品分类列表"""
    try:
        categories = db.get_all(
            "SELECT DISTINCT category FROM business_products WHERE deleted=0 AND category IS NOT NULL AND category!='' ORDER BY category"
        )
        # 统计每个分类下的商品数量
        result = []
        for cat in (categories or []):
            count = db.get_total(
                "SELECT COUNT(*) FROM business_products WHERE deleted=0 AND status='active' AND category=%s",
                [cat['category']]
            )
            result.append({'name': cat['category'], 'count': count})
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.warning(f"获取商品分类失败: {e}")
        return jsonify({'success': True, 'data': []})


# ============ V9.0 签到系统 ============

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
        except:
            pass
        logging.error(f"签到失败: {e}")
        return jsonify({'success': False, 'msg': '签到失败，请稍后重试'})
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


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
    except Exception as e:
        logging.warning(f"检查成就失败: {e}")


@app.route('/api/user/checkin/status', methods=['GET'])
@require_login
def get_checkin_status(user):
    """获取签到状态"""
    uid = user['user_id']
    today = time.strftime('%Y-%m-%d')

    try:
        # 今天是否已签到
        today_checkin = db.get_one(
            "SELECT * FROM business_checkin_logs WHERE user_id=%s AND checkin_date=%s",
            [uid, today]
        )

        # 最近7天签到记录
        week_ago = time.strftime('%Y-%m-%d', time.localtime(time.time() - 7 * 86400))
        recent = db.get_all(
            "SELECT checkin_date, continuous_days, reward_points FROM business_checkin_logs "
            "WHERE user_id=%s AND checkin_date BETWEEN %s AND %s ORDER BY checkin_date",
            [uid, week_ago, today]
        )

        # 本月签到次数
        month_start = today[:8] + '01'
        month_count = db.get_total(
            "SELECT COUNT(*) FROM business_checkin_logs WHERE user_id=%s AND checkin_date BETWEEN %s AND %s",
            [uid, month_start, today]
        )

        # 累计签到天数
        total_days = db.get_total(
            "SELECT COUNT(*) FROM business_checkin_logs WHERE user_id=%s",
            [uid]
        )

        # 当前连续天数
        continuous = 0
        if today_checkin:
            continuous = today_checkin.get('continuous_days') or 0
        else:
            yesterday = time.strftime('%Y-%m-%d', time.localtime(time.time() - 86400))
            yesterday_record = db.get_one(
                "SELECT continuous_days FROM business_checkin_logs WHERE user_id=%s AND checkin_date=%s",
                [uid, yesterday]
            )
            if yesterday_record:
                continuous = yesterday_record['continuous_days']

        return jsonify({'success': True, 'data': {
            'checked_in': bool(today_checkin),
            'continuous_days': continuous,
            'month_count': month_count,
            'total_days': total_days,
            'recent': recent or [],
            'today_reward': min(continuous + 1, 7) + (10 if continuous + 1 >= 7 else 0) if not today_checkin else 0
        }})
    except Exception as e:
        logging.warning(f"获取签到状态失败: {e}")
        return jsonify({'success': True, 'data': {
            'checked_in': False, 'continuous_days': 0, 'month_count': 0,
            'total_days': 0, 'recent': [], 'today_reward': 1
        }})


@app.route('/api/user/checkin/rank', methods=['GET'])
@require_login
def get_checkin_rank(user):
    """签到排行榜"""
    try:
        today = time.strftime('%Y-%m-%d')
        month_start = today[:8] + '01'
        rank = db.get_all(
            """SELECT m.user_name, m.member_level,
                      COUNT(cl.id) as checkin_days,
                      MAX(cl.continuous_days) as max_continuous
               FROM business_checkin_logs cl
               LEFT JOIN business_members m ON cl.user_id = m.user_id
               WHERE cl.checkin_date BETWEEN %s AND %s
               GROUP BY cl.user_id
               ORDER BY checkin_days DESC, max_continuous DESC
               LIMIT 20""",
            [month_start, today]
        )
        return jsonify({'success': True, 'data': rank or []})
    except Exception as e:
        logging.warning(f"获取签到排行榜失败: {e}")
        return jsonify({'success': True, 'data': []})











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
    except Exception as e:
        logging.warning(f"获取营销活动失败: {e}")
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
    except Exception as e:
        logging.warning(f"活动详情查询失败: {e}")
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
    except Exception as e:
        logging.error(f"促销计算失败: {e}")
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
    except Exception as e:
        logging.error(f"获取秒杀活动失败: {e}")
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
    except Exception as e:
        logging.error(f"秒杀下单失败: {e}")
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
    except Exception as e:
        logging.error(f"获取秒杀订单失败: {e}")
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
    except Exception as e:
        logging.error(f"评价提交失败: {e}")
        return jsonify({'success': False, 'msg': '评价提交失败'})


def _update_review_stats(target_type, target_id):
    """更新评价统计"""
    try:
        if target_type == 'shop':
            # 更新门店评分
            stats = db.get_one("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
                FROM business_reviews WHERE target_type='shop' AND target_id=%s AND deleted=0
            """, [target_id])
            if stats:
                db.execute("""
                    UPDATE business_shops SET rating=%s, review_count=%s WHERE id=%s
                """, [round(float(stats['avg_rating'] or 0), 1), stats['review_count'], target_id])
        
        elif target_type == 'product':
            # 更新商品评分
            stats = db.get_one("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
                FROM business_reviews WHERE target_type='product' AND target_id=%s AND deleted=0
            """, [target_id])
            if stats:
                db.execute("""
                    UPDATE business_products SET rating=%s, review_count=%s WHERE id=%s
                """, [round(float(stats['avg_rating'] or 0), 1), stats['review_count'], target_id])
        
        elif target_type == 'venue':
            # 更新场馆评分
            stats = db.get_one("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
                FROM business_reviews WHERE target_type='venue' AND target_id=%s AND deleted=0
            """, [target_id])
            if stats:
                db.execute("""
                    UPDATE business_venues SET rating=%s, review_count=%s WHERE id=%s
                """, [round(float(stats['avg_rating'] or 0), 1), stats['review_count'], target_id])
    except Exception as e:
        logging.warning(f"更新评价统计失败: {e}")


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
    """删除我的评价"""
    review = db.get_one(
        "SELECT * FROM business_reviews WHERE id=%s AND user_id=%s AND deleted=0",
        [review_id, user['user_id']]
    )
    if not review:
        return jsonify({'success': False, 'msg': '评价不存在'})
    
    db.execute("UPDATE business_reviews SET deleted=1 WHERE id=%s", [review_id])
    return jsonify({'success': True, 'msg': '评价已删除'})


# ============ 会员权益 V21.0新增 ============

@app.route('/api/user/member/benefits', methods=['GET'])
@require_login
def get_member_benefits(user):
    """获取会员权益信息"""
    uid = user['user_id']
    
    try:
        # 获取会员信息
        member = db.get_one("""
            SELECT m.*, ml.level_name, ml.discount_rate, ml.points_rate, ml.privileges
            FROM business_members m
            LEFT JOIN business_member_levels ml ON m.member_level = ml.level_code
            WHERE m.user_id=%s
        """, [uid])
        
        if not member:
            # 自动创建会员
            db.execute("""
                INSERT INTO business_members (user_id, user_name, phone, points, member_level, ec_id, project_id)
                VALUES (%s, %s, %s, 0, 'L1', %s, %s)
            """, [uid, user.get('user_name', ''), user.get('phone'), user.get('ec_id'), user.get('project_id')])
            
            member = {
                'user_id': uid,
                'points': 0,
                'total_points': 0,
                'balance': 0,
                'member_level': 'L1',
                'level_name': '普通会员',
                'discount_rate': 1.00,
                'points_rate': 1.00,
                'privileges': '[]'
            }
        
        # 获取等级列表
        levels = db.get_all("""
            SELECT level_code, level_name, min_amount, max_amount, discount_rate, points_rate, privileges
            FROM business_member_levels
            WHERE status='active'
            ORDER BY sort_order
        """) or []
        
        # 解析权益JSON
        for level in levels:
            try:
                level['privileges'] = json.loads(level.get('privileges') or '[]')
            except:
                level['privileges'] = []
        
        # 当前会员特权
        privileges = []
        try:
            privileges = json.loads(member.get('privileges') or '[]')
        except:
            privileges = []
        
        # 计算距下一等级还需消费
        next_level = None
        amount_to_next = 0
        current_consume = float(member.get('total_consume') or 0)
        
        for level in levels:
            min_amt = float(level.get('min_amount') or 0)
            if min_amt > current_consume:
                next_level = level
                amount_to_next = min_amt - current_consume
                break
        
        result = {
            'member_level': member.get('member_level'),
            'level_name': member.get('level_name') or '普通会员',
            'discount_rate': float(member.get('discount_rate') or 1.0),
            'points_rate': float(member.get('points_rate') or 1.0),
            'total_consume': current_consume,
            'points': member.get('points', 0),
            'total_points': member.get('total_points', 0),
            'balance': member.get('balance', 0),
            'privileges': privileges,
            'levels': levels,
            'next_level': next_level,
            'amount_to_next': amount_to_next
        }
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.error(f"获取会员权益失败: {e}")
        return jsonify({'success': False, 'msg': '获取失败'})


# ============ 物流查询 V22.0 ============

@app.route('/api/user/orders/<int:order_id>/logistics', methods=['GET'])
@require_login
def get_order_logistics(user, order_id):
    """获取订单物流信息"""
    order = db.get_one(
        "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
        [order_id, user['user_id']]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})

    # 检查订单是否已发货
    if order.get('order_status') not in ['shipped', 'completed']:
        return jsonify({'success': True, 'data': None, 'msg': '订单尚未发货'})

    # 使用物流服务查询
    result = logistics.get_order_logistics(order_id)
    return jsonify(result)


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
    """V42.0: 获取积分兑换记录"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)

    try:
        total = db.get_total(
            "SELECT COUNT(*) FROM business_points_exchanges WHERE user_id=%s",
            [user['user_id']]
        )
        offset = (page - 1) * page_size
        items = db.get_all(
            """SELECT e.*, g.goods_name, g.goods_image
               FROM business_points_exchanges e
               LEFT JOIN business_points_goods g ON e.goods_id = g.id
               WHERE e.user_id=%s
               ORDER BY e.created_at DESC
               LIMIT %s OFFSET %s""",
            [user['user_id'], page_size, offset]
        ) or []
        return jsonify({'success': True, 'data': {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
    except Exception as e:
        logging.error(f"获取兑换记录失败: {e}")
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}})


# ============ V42.0 限时秒杀倒计时 ============

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
    except Exception as e:
        logging.error(f"获取秒杀倒计时失败: {e}")
        return jsonify({'success': True, 'data': []})


@app.route('/api/user/products/<int:product_id>/reviews', methods=['GET'])
def get_product_reviews(product_id):
    """V42.0: 获取商品评价列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    rating = request.args.get('rating')  # 可选：筛选星级

    where = "target_type='product' AND target_id=%s AND deleted=0"
    params = [product_id]
    if rating:
        where += " AND rating=%s"
        params.append(int(rating))

    total = db.get_total(f"SELECT COUNT(*) FROM business_reviews WHERE {where}", params)
    offset = (page - 1) * page_size
    reviews = db.get_all(f"""
        SELECT r.*,
               CASE WHEN r.images IS NOT NULL AND r.images != '' THEN 1 ELSE 0 END as has_images
        FROM business_reviews r
        WHERE {where}
        ORDER BY r.created_at DESC
        LIMIT %s OFFSET %s
    """, params + [page_size, offset]) or []

    return jsonify({'success': True, 'data': {
        'reviews': reviews,
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})


@app.route('/api/user/member/card', methods=['GET'])
@require_login
def get_member_card(user):
    """V42.0: 获取会员数字卡信息"""
    uid = user['user_id']
    member = db.get_one("""
        SELECT m.*, ml.level_name, ml.discount_rate, ml.privileges
        FROM business_members m
        LEFT JOIN business_member_levels ml ON m.member_level = ml.level_code
        WHERE m.user_id=%s
    """, [uid])

    if not member:
        return jsonify({'success': False, 'msg': '会员不存在'})

    # 生成会员卡号（脱敏展示）
    card_no = f"{member['user_id']:010d}"

    # 获取最近消费
    recent_order = db.get_one("""
        SELECT actual_amount, created_at FROM business_orders
        WHERE user_id=%s AND order_status='completed'
        ORDER BY created_at DESC LIMIT 1
    """, [uid])

    # 获取权益列表
    privileges = []
    try:
        privileges = json.loads(member.get('privileges') or '[]')
    except:
        privileges = []

    return jsonify({'success': True, 'data': {
        'card_no': card_no,
        'member_name': member.get('user_name', ''),
        'phone': member.get('phone', ''),
        'level': member.get('member_level', 'L1'),
        'level_name': member.get('level_name', '普通会员'),
        'points': member.get('points', 0),
        'total_points': member.get('total_points', 0),
        'balance': member.get('balance', 0),
        'discount_rate': float(member.get('discount_rate') or 1.0),
        'privileges': privileges,
        'join_date': str(member.get('created_at', ''))[:10] if member.get('created_at') else '',
        'last_consume': str(recent_order['created_at'])[:10] if recent_order else None,
        'last_amount': float(recent_order['actual_amount'] or 0) if recent_order else 0
    }})


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
    """V28.0: 获取用户成就列表"""
    uid = user.get('user_id')
    
    # 获取所有成就定义
    achievements = db.get_all(
        "SELECT id, code, name, description, condition_type, condition_value, points_reward, icon FROM business_achievements WHERE is_active=1 ORDER BY condition_value ASC"
    ) or []
    
    # 获取用户已解锁的成就
    user_achievements = db.get_all(
        "SELECT achievement_code, earned_at FROM business_user_achievements WHERE user_id=%s",
        [uid]
    ) or []
    earned_map = {ua['achievement_code']: ua['earned_at'] for ua in user_achievements}
    
    # 获取用户统计
    member = db.get_one(
        "SELECT total_orders, total_consume, checkin_streak FROM business_members WHERE user_id=%s",
        [uid]
    ) or {}
    
    result = []
    for ach in achievements:
        earned = earned_map.get(ach.get('code'))
        progress = 0
        
        # 计算进度
        if ach.get('condition_type') == 'order_count':
            current = int(member.get('total_orders') or 0)
            target = int(ach.get('condition_value') or 1)
            progress = min(100, int(current / target * 100))
        elif ach.get('condition_type') == 'order_amount':
            current = float(member.get('total_consume') or 0)
            target = float(ach.get('condition_value') or 1)
            progress = min(100, int(current / target * 100))
        elif ach.get('condition_type') == 'checkin_days':
            current = int(member.get('checkin_streak') or 0)
            target = int(ach.get('condition_value') or 1)
            progress = min(100, int(current / target * 100))
        
        result.append({
            'id': ach.get('id'),
            'code': ach.get('code'),
            'name': ach.get('name'),
            'description': ach.get('description'),
            'icon': ach.get('icon') or '🏆',
            'points_reward': ach.get('points_reward'),
            'condition_type': ach.get('condition_type'),
            'condition_value': ach.get('condition_value'),
            'is_earned': earned is not None,
            'earned_at': earned,
            'progress': progress
        })
    
    earned_count = sum(1 for r in result if r['is_earned'])
    return jsonify({'success': True, 'data': {
        'items': result,
        'earned_count': earned_count,
        'total_count': len(result)
    }})


# ============ V28.0 积分商城兑换记录 ============

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
    except Exception as e:
        logging.error(f"确认收货失败: {e}")
        return jsonify({'success': False, 'msg': '操作失败'})


# ============ V33.0 发票管理 ============

@app.route('/api/user/invoice/titles', methods=['GET'])
@require_login
def get_invoice_titles(user):
    """V33.0: 获取用户的发票抬头列表"""
    uid = user.get('user_id')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        titles = db.get_all(
            """SELECT id, title_type, title_name, tax_no, bank_name, bank_account,
                      address, phone, is_default, created_at
               FROM business_invoice_titles
               WHERE user_id=%s AND deleted=0
               ORDER BY is_default DESC, created_at DESC""",
            [uid]
        )
        return jsonify({'success': True, 'data': titles or []})
    except Exception as e:
        logging.warning(f"发票抬头查询失败: {e}")
        return jsonify({'success': True, 'data': []})


@app.route('/api/user/invoice/titles', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=20, window_seconds=60)
def create_invoice_title(user):
    """V33.0: 创建发票抬头"""
    uid = user.get('user_id')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    data = request.get_json() or {}
    
    title_type = data.get('title_type', 'personal')
    title_name = data.get('title_name', '').strip()
    tax_no = data.get('tax_no', '')
    bank_name = data.get('bank_name', '')
    bank_account = data.get('bank_account', '')
    address = data.get('address', '')
    phone = data.get('phone', '')
    is_default = data.get('is_default', False)
    
    if not title_name:
        return jsonify({'success': False, 'msg': '请填写发票抬头'})
    
    if title_type == 'enterprise' and not tax_no:
        return jsonify({'success': False, 'msg': '企业抬头必须填写税号'})
    
    try:
        # 如果设置为默认，先取消其他默认
        if is_default:
            db.execute(
                "UPDATE business_invoice_titles SET is_default=0 WHERE user_id=%s AND deleted=0",
                [uid]
            )
        
        title_id = db.execute(
            """INSERT INTO business_invoice_titles
               (user_id, title_type, title_name, tax_no, bank_name, bank_account, address, phone, is_default, ec_id, project_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [uid, title_type, title_name, tax_no, bank_name, bank_account, address, phone, 1 if is_default else 0, ec_id, project_id]
        )
        
        return jsonify({'success': True, 'msg': '发票抬头创建成功', 'data': {'title_id': title_id}})
    except Exception as e:
        logging.error(f"创建发票抬头失败: {e}")
        return jsonify({'success': False, 'msg': '创建失败'})


@app.route('/api/user/invoice/titles/<int:title_id>', methods=['PUT'])
@require_login
def update_invoice_title(user, title_id):
    """V33.0: 更新发票抬头"""
    uid = user.get('user_id')
    data = request.get_json() or {}
    
    # 检查抬头是否存在
    title = db.get_one(
        "SELECT * FROM business_invoice_titles WHERE id=%s AND user_id=%s AND deleted=0",
        [title_id, uid]
    )
    if not title:
        return jsonify({'success': False, 'msg': '发票抬头不存在'})
    
    # 构建更新字段
    update_fields = []
    params = []
    
    allowed = ['title_type', 'title_name', 'tax_no', 'bank_name', 'bank_account', 'address', 'phone', 'is_default']
    for field in allowed:
        if field in data:
            if field == 'is_default' and data[field]:
                db.execute("UPDATE business_invoice_titles SET is_default=0 WHERE user_id=%s AND deleted=0", [uid])
            update_fields.append(f"{field}=%s")
            params.append(data[field])
    
    if not update_fields:
        return jsonify({'success': False, 'msg': '没有需要更新的字段'})
    
    params.extend([title_id])
    
    try:
        db.execute(
            f"UPDATE business_invoice_titles SET {', '.join(update_fields)}, updated_at=NOW() WHERE id=%s",
            params
        )
        return jsonify({'success': True, 'msg': '更新成功'})
    except Exception as e:
        logging.error(f"更新发票抬头失败: {e}")
        return jsonify({'success': False, 'msg': '更新失败'})


@app.route('/api/user/invoice/titles/<int:title_id>', methods=['DELETE'])
@require_login
def delete_invoice_title(user, title_id):
    """V33.0: 删除发票抬头"""
    uid = user.get('user_id')
    
    title = db.get_one(
        "SELECT * FROM business_invoice_titles WHERE id=%s AND user_id=%s AND deleted=0",
        [title_id, uid]
    )
    if not title:
        return jsonify({'success': False, 'msg': '发票抬头不存在'})
    
    try:
        db.execute("UPDATE business_invoice_titles SET deleted=1 WHERE id=%s", [title_id])
        return jsonify({'success': True, 'msg': '删除成功'})
    except Exception as e:
        logging.error(f"删除发票抬头失败: {e}")
        return jsonify({'success': False, 'msg': '删除失败'})


@app.route('/api/user/invoices', methods=['GET'])
@require_login
def get_user_invoices(user):
    """V33.0: 获取用户的发票列表"""
    uid = user.get('user_id')
    status = request.args.get('status')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 50)
    
    where = "user_id=%s AND deleted=0"
    params = [uid]
    if status:
        where += " AND invoice_status=%s"
        params.append(status)
    
    total = db.get_total(f"SELECT COUNT(*) FROM business_invoices WHERE {where}", params)
    offset = (page - 1) * page_size
    
    items = db.get_all(
        f"""SELECT i.*, t.title_type, t.title_name, t.tax_no
            FROM business_invoices i
            LEFT JOIN business_invoice_titles t ON i.title_id = t.id
            WHERE {where}
            ORDER BY i.created_at DESC
            LIMIT %s OFFSET %s""",
        params + [page_size, offset]
    )
    
    return jsonify({'success': True, 'data': {
        'items': items or [],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})


@app.route('/api/user/invoices/<int:invoice_id>', methods=['GET'])
@require_login
def get_user_invoice_detail(user, invoice_id):
    """V33.0: 获取发票详情"""
    uid = user.get('user_id')
    
    invoice = db.get_one(
        """SELECT i.*, t.title_type, t.title_name, t.tax_no, t.bank_name, t.bank_account, t.address, t.phone,
                  o.actual_amount, o.pay_time
           FROM business_invoices i
           LEFT JOIN business_invoice_titles t ON i.title_id = t.id
           LEFT JOIN business_orders o ON i.order_id = o.id
           WHERE i.id=%s AND i.user_id=%s AND i.deleted=0""",
        [invoice_id, uid]
    )
    
    if not invoice:
        return jsonify({'success': False, 'msg': '发票不存在'})
    
    return jsonify({'success': True, 'data': invoice})


@app.route('/api/user/orders/<int:order_id>/invoice/apply', methods=['POST'])
@require_login
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def apply_invoice_from_order(user, order_id):
    """V33.0: 申请发票（从订单）"""
    uid = user.get('user_id')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    data = request.get_json() or {}
    
    title_id = data.get('title_id')
    invoice_type = data.get('invoice_type', 'electronic')
    content = data.get('content', '商品明细')
    remark = data.get('remark', '')
    
    if not title_id:
        return jsonify({'success': False, 'msg': '请选择发票抬头'})
    
    # 验证订单
    order = db.get_one(
        "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
        [order_id, uid]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    
    if order.get('pay_status') != 'paid':
        return jsonify({'success': False, 'msg': '仅已支付订单可申请发票'})
    
    # 检查是否已申请
    existing = db.get_one(
        "SELECT id FROM business_invoices WHERE order_id=%s AND deleted=0 AND invoice_status != 'cancelled'",
        [order_id]
    )
    if existing:
        return jsonify({'success': False, 'msg': '该订单已申请过发票'})
    
    # 验证抬头
    title = db.get_one(
        "SELECT * FROM business_invoice_titles WHERE id=%s AND user_id=%s AND deleted=0",
        [title_id, uid]
    )
    if not title:
        return jsonify({'success': False, 'msg': '发票抬头不存在'})
    
    # 计算金额
    amount = order.get('actual_amount', 0)
    tax_rate = 0.06
    tax_amount = amount * tax_rate
    
    # 生成发票号
    import uuid
    invoice_no = f"INV{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
    
    try:
        invoice_id = db.execute(
            """INSERT INTO business_invoices
               (invoice_no, order_id, order_no, user_id, title_id, title_type, title_name, tax_no,
                invoice_type, invoice_status, amount, tax_amount, tax_rate, content, remark, ec_id, project_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [invoice_no, order_id, order.get('order_no'), uid, title_id, title['title_type'],
             title['title_name'], title.get('tax_no'), invoice_type, 'pending', amount, tax_amount,
             tax_rate, content, remark, ec_id, project_id]
        )
        
        return jsonify({
            'success': True,
            'msg': '发票申请成功',
            'data': {'invoice_id': invoice_id, 'invoice_no': invoice_no}
        })
    except Exception as e:
        logging.error(f"申请发票失败: {e}")
        return jsonify({'success': False, 'msg': '申请失败'})


@app.route('/api/user/invoices/<int:invoice_id>/cancel', methods=['POST'])
@require_login
def cancel_invoice(user, invoice_id):
    """V33.0: 取消发票申请"""
    uid = user.get('user_id')
    data = request.get_json() or {}
    reason = data.get('reason', '用户取消')
    
    invoice = db.get_one(
        "SELECT * FROM business_invoices WHERE id=%s AND user_id=%s AND invoice_status='pending' AND deleted=0",
        [invoice_id, uid]
    )
    
    if not invoice:
        return jsonify({'success': False, 'msg': '发票不存在或状态不允许取消'})
    
    try:
        db.execute(
            "UPDATE business_invoices SET invoice_status='cancelled', remark=CONCAT(IFNULL(remark,''), ' 取消原因:', %s) WHERE id=%s",
            [reason, invoice_id]
        )
        return jsonify({'success': True, 'msg': '发票申请已取消'})
    except Exception as e:
        logging.error(f"取消发票失败: {e}")
        return jsonify({'success': False, 'msg': '操作失败'})


# ============ V38.0 成长任务 ============

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
    except Exception as e:
        logging.warning(f"获取成长任务失败: {e}")
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
    except Exception as e:
        logging.error(f"领取奖励失败: {e}")
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
    except Exception as e:
        logging.warning(f"获取奖励规则失败: {e}")
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
    except Exception as e:
        logging.warning(f"获取评价统计失败: {e}")
        return jsonify({'success': True, 'data': {
            'total_reviews': 0, 'rewarded_reviews': 0,
            'total_points_earned': 0, 'total_growth_earned': 0, 'avg_rating': 0
        }})


# ============ V38.0 最优折扣计算 ============

@app.route('/api/user/discount/optimal', methods=['GET'])
@require_login
def get_optimal_discount(user):
    """V38.0: 计算最优优惠券+积分组合"""
    uid = user.get('user_id')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    order_amount = float(request.args.get('amount', 0))
    if order_amount <= 0:
        return jsonify({'success': False, 'msg': '请提供订单金额'})
    
    # 获取用户积分
    member = db.get_one("SELECT points FROM business_members WHERE user_id=%s", [uid])
    user_points = member.get('points', 0) if member else 0
    
    try:
        from business_common.discount_calculator_service import discount_calculator
        result = discount_calculator.calculate_optimal_discount(
            uid, order_amount, user_points, ec_id, project_id
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.warning(f"计算最优折扣失败: {e}")
        return jsonify({'success': True, 'data': {
            'order_amount': order_amount,
            'user_points': user_points,
            'optimal_plan': {
                'use_points': 0, 'points_deduction': 0,
                'total_discount': 0, 'final_amount': order_amount
            }
        }})


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
    except Exception as e:
        logging.warning(f"预览折扣失败: {e}")
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
            except:
                pass
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.warning(f"记录分享失败: {e}")
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
    except Exception as e:
        logging.warning(f"记录点击失败: {e}")
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
    except Exception as e:
        logging.warning(f"获取分享统计失败: {e}")
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
    except Exception as e:
        logging.warning(f"获取分享历史失败: {e}")
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
    except Exception as e:
        logging.warning(f"获取海报配置失败: {e}")
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
    """V29.0: 获取常用申请列表"""
    items = db.get_all(
        """SELECT id, app_no, app_type, title, form_data, created_at
           FROM business_applications
           WHERE user_id=%s AND is_favorite=1 AND deleted=0
           ORDER BY updated_at DESC
           LIMIT 20""",
        [user.get('user_id')]
    ) or []
    
    # 获取类型名称
    type_map = {}
    types = db.get_all("SELECT type_code, type_name, icon FROM business_application_types WHERE is_active=1")
    for t in types or []:
        type_map[t['type_code']] = {'name': t['type_name'], 'icon': t['icon']}
    
    for item in items:
        type_info = type_map.get(item.get('app_type'), {})
        item['type_name'] = type_info.get('name', item.get('app_type'))
        item['type_icon'] = type_info.get('icon', '')
        if item.get('form_data'):
            try:
                item['form_data'] = json.loads(item['form_data'])
            except:
                item['form_data'] = {}
    
    return jsonify({'success': True, 'data': {'items': items}})


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
    except Exception as e:
        logging.error(f"[GuestV2] 异常: {e}")
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
            
    except Exception as e:
        logging.error(f"[GuestV2] 详情异常: {e}")
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
    except Exception as e:
        logging.error(f"[RoomV2] 异常: {e}")
        return jsonify({'success': False, 'msg': f'获取房间列表失败: {str(e)}', 'data': []})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22311, debug=False)


