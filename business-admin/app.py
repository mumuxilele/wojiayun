#!/usr/bin/env python3
"""
社区商业 - 管理端 Web 服务（MVC 架构）
端口: 22313
路由层仅处理 HTTP 请求/响应，业务逻辑委托给 AdminService
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import config, auth, error_handler
from business_common.services import AdminService

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

error_handler.register_error_handlers(app)


# ============ 管理员认证 ============

def get_current_admin():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_staff(token, isdev) if token else None


def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_admin()
        if not user:
            return jsonify({'success': False, 'msg': '请使用管理员账号登录'})
        return f(user, *args, **kwargs)
    return decorated


# ============ 申请单管理 ============

@app.route('/api/admin/applications', methods=['GET'])
@require_admin
def list_applications(user):
    """申请单列表"""
    svc = AdminService()
    return jsonify(svc.list_applications(
        status=request.args.get('status'),
        app_type=request.args.get('app_type'),
        keyword=request.args.get('keyword', ''),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/admin/applications/<int:app_id>', methods=['GET'])
@require_admin
def get_application(user, app_id):
    """申请单详情"""
    svc = AdminService()
    return jsonify(svc.get_application(app_id))


@app.route('/api/admin/applications/<int:app_id>', methods=['PUT'])
@require_admin
def update_application(user, app_id):
    """修改申请单"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.update_application(app_id, data))


@app.route('/api/admin/applications/<int:app_id>', methods=['DELETE'])
@require_admin
def delete_application(user, app_id):
    """删除申请单"""
    svc = AdminService()
    return jsonify(svc.delete_application(app_id))


# ============ 订单管理 ============

@app.route('/api/admin/orders', methods=['GET'])
@require_admin
def list_orders(user):
    """订单列表"""
    svc = AdminService()
    return jsonify(svc.list_orders(
        status=request.args.get('status'),
        keyword=request.args.get('keyword', ''),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/admin/orders/<int:order_id>', methods=['GET'])
@require_admin
def get_order(user, order_id):
    """订单详情"""
    svc = AdminService()
    return jsonify(svc.get_order(order_id))


@app.route('/api/admin/orders/<int:order_id>', methods=['PUT'])
@require_admin
def update_order(user, order_id):
    """修改订单"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.update_order(order_id, data))


@app.route('/api/admin/orders/<int:order_id>', methods=['DELETE'])
@require_admin
def delete_order(user, order_id):
    """删除订单"""
    svc = AdminService()
    return jsonify(svc.delete_order(order_id))


# ============ 商品管理 ============

@app.route('/api/admin/products', methods=['GET'])
@require_admin
def list_products(user):
    """商品列表"""
    from business_common.services.product_service import ProductService
    svc = ProductService()
    return jsonify(svc.get_all_products(
        status=request.args.get('status'),
        keyword=request.args.get('keyword', ''),
        shop_id=request.args.get('shop_id'),
        category_name=request.args.get('category'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/admin/products/<int:product_id>', methods=['GET'])
@require_admin
def get_product(user, product_id):
    """商品详情"""
    from business_common.services.product_service import ProductService
    svc = ProductService()
    return jsonify(svc.get_product_by_id(product_id))


@app.route('/api/admin/products', methods=['POST'])
@require_admin
def create_product(user):
    """新增商品"""
    data = request.get_json() or {}
    from business_common.services.product_service import ProductService
    svc = ProductService()
    return jsonify(svc.create_product(data))


@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
@require_admin
def update_product(user, product_id):
    """更新商品"""
    data = request.get_json() or {}
    from business_common.services.product_service import ProductService
    svc = ProductService()
    return jsonify(svc.update_product(product_id, data))


@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
@require_admin
def delete_product(user, product_id):
    """删除商品"""
    from business_common.services.product_service import ProductService
    svc = ProductService()
    return jsonify(svc.delete_product(product_id))


@app.route('/api/admin/products/import', methods=['POST'])
@require_admin
def import_products(user):
    """导入商品（支持 JSON 批量）"""
    data = request.get_json() or {}
    products = data.get('products', [])
    if not products:
        return jsonify({'success': False, 'msg': '没有可导入的数据'})
    from business_common.services.product_service import ProductService
    svc = ProductService()
    return jsonify(svc.import_products(products))


@app.route('/api/admin/product-categories', methods=['GET'])
@require_admin
def get_product_categories(user):
    """获取商品分类列表"""
    from business_common.services.product_category_service import ProductCategoryService
    svc = ProductCategoryService()
    level = request.args.get('level')
    parent_id = request.args.get('parent_id')
    if level:
        return jsonify(svc.get_category_list(level=int(level)))
    elif parent_id is not None:
        return jsonify(svc.get_category_list(parent_id=int(parent_id)))
    return jsonify(svc.get_all_categories())


@app.route('/api/admin/product-categories/tree', methods=['GET'])
@require_admin
def get_product_category_tree(user):
    """获取商品分类树（带层级）"""
    from business_common.services.product_category_service import ProductCategoryService
    svc = ProductCategoryService()
    return jsonify(svc.get_category_tree())


@app.route('/api/admin/product-categories/<int:category_id>', methods=['GET'])
@require_admin
def get_product_category(user, category_id):
    """获取商品分类详情"""
    from business_common.services.product_category_service import ProductCategoryService
    svc = ProductCategoryService()
    return jsonify(svc.get_category_by_id(category_id))


@app.route('/api/admin/product-categories', methods=['POST'])
@require_admin
def create_product_category(user):
    """新增商品分类"""
    data = request.get_json() or {}
    from business_common.services.product_category_service import ProductCategoryService
    svc = ProductCategoryService()
    return jsonify(svc.create_category(data))


@app.route('/api/admin/product-categories/<int:category_id>', methods=['PUT'])
@require_admin
def update_product_category(user, category_id):
    """更新商品分类"""
    data = request.get_json() or {}
    from business_common.services.product_category_service import ProductCategoryService
    svc = ProductCategoryService()
    return jsonify(svc.update_category(category_id, data))


@app.route('/api/admin/product-categories/<int:category_id>', methods=['DELETE'])
@require_admin
def delete_product_category(user, category_id):
    """删除商品分类"""
    from business_common.services.product_category_service import ProductCategoryService
    svc = ProductCategoryService()
    return jsonify(svc.delete_category(category_id))


@app.route('/api/admin/product-categories/<int:category_id>/status', methods=['POST'])
@require_admin
def toggle_category_status(user, category_id):
    """切换分类状态"""
    data = request.get_json() or {}
    from business_common.services.product_category_service import ProductCategoryService
    svc = ProductCategoryService()
    return jsonify(svc.toggle_status(category_id, data.get('status')))


@app.route('/api/admin/products/<int:product_id>/status', methods=['POST'])
@require_admin
def toggle_product_status(user, product_id):
    """切换商品状态（上架/下架）"""
    data = request.get_json() or {}
    from business_common.services.product_service import ProductService
    svc = ProductService()
    return jsonify(svc.toggle_product_status(product_id, data.get('status')))


# ============ 门店管理 ============

@app.route('/api/admin/shops', methods=['GET'])
@require_admin
def list_shops(user):
    """门店列表"""
    svc = AdminService()
    return jsonify(svc.list_shops())


@app.route('/api/admin/shops/<int:shop_id>', methods=['GET'])
@require_admin
def get_shop(user, shop_id):
    """门店详情"""
    svc = AdminService()
    return jsonify(svc.get_shop(shop_id))


@app.route('/api/admin/shops', methods=['POST'])
@require_admin
def create_shop(user):
    """创建门店"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.create_shop(data))


@app.route('/api/admin/shops/<int:shop_id>', methods=['PUT'])
@require_admin
def update_shop(user, shop_id):
    """修改门店"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.update_shop(shop_id, data))


@app.route('/api/admin/shops/<int:shop_id>', methods=['DELETE'])
@require_admin
def delete_shop(user, shop_id):
    """删除门店"""
    svc = AdminService()
    return jsonify(svc.delete_shop(shop_id))


# ============ 统计数据 ============

@app.route('/api/admin/statistics', methods=['GET'])
@require_admin
def get_statistics(user):
    """综合统计"""
    svc = AdminService()
    return jsonify(svc.get_statistics())


@app.route('/api/admin/statistics/refund-analysis', methods=['GET'])
@require_admin
def get_refund_analysis(user):
    """退款分析统计"""
    from business_common import db
    from datetime import datetime, timedelta
    
    # 获取最近30天的退款数据
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    cursor = db.get_cursor()
    
    # 退款统计
    sql = """
        SELECT 
            COUNT(*) as total_refunds,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_refunds,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_refunds,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_refunds
        FROM business_refunds 
        WHERE deleted = 0 AND created_at >= %s
    """
    cursor.execute(sql, (thirty_days_ago,))
    result = cursor.fetchone()
    cursor.close()
    
    return jsonify({
        'success': True,
        'data': {
            'total_refunds': result['total_refunds'] if result else 0,
            'completed_refunds': result['completed_refunds'] if result else 0,
            'pending_refunds': result['pending_refunds'] if result else 0,
            'rejected_refunds': result['rejected_refunds'] if result else 0,
            'refund_rate': round(result['completed_refunds'] / result['total_refunds'] * 100, 2) if result and result['total_refunds'] > 0 else 0
        }
    })


# ============ 场地管理 ============

@app.route('/api/admin/venues', methods=['GET'])
@require_admin
def list_venues(user):
    """场地列表"""
    from business_common import db
    from math import ceil
    
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    keyword = request.args.get('keyword', '')
    venue_type = request.args.get('type', '')
    status = request.args.get('status', '')
    
    conditions = ["deleted=0"]
    params = []
    
    if keyword:
        conditions.append("(name LIKE %s OR address LIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if venue_type:
        conditions.append("type=%s")
        params.append(venue_type)
    if status:
        conditions.append("status=%s")
        params.append(status)
    
    where_clause = " AND ".join(conditions)
    
    # 查询总数
    count_sql = f"SELECT COUNT(*) as total FROM business_venues WHERE {where_clause}"
    cursor = db.get_cursor()
    cursor.execute(count_sql, params)
    total = cursor.fetchone()['total']
    
    # 查询列表
    offset = (page - 1) * page_size
    list_sql = f"""
        SELECT id, name, type, address, capacity, status, price, images, 
               opening_hours, contact_phone, created_at
        FROM business_venues 
        WHERE {where_clause}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    cursor.execute(list_sql, params)
    rows = cursor.fetchall()
    cursor.close()
    
    return jsonify({
        'success': True,
        'data': {
            'list': rows,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': ceil(total / page_size) if total > 0 else 0
        }
    })


@app.route('/api/admin/venues/<int:venue_id>', methods=['GET'])
@require_admin
def get_venue(user, venue_id):
    """获取场地详情"""
    from business_common import db
    
    cursor = db.get_cursor()
    cursor.execute("SELECT * FROM business_venues WHERE id=%s AND deleted=0", (venue_id,))
    venue = cursor.fetchone()
    cursor.close()
    
    if not venue:
        return jsonify({'success': False, 'message': '场地不存在'}), 404
    
    return jsonify({'success': True, 'data': venue})


@app.route('/api/admin/venues', methods=['POST'])
@require_admin
def create_venue(user):
    """创建场地"""
    from business_common import db
    
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'message': '场地名称不能为空'}), 400
    
    cursor = db.get_cursor()
    cursor.execute("""
        INSERT INTO business_venues (name, type, address, capacity, status, price, images, opening_hours, contact_phone, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """, (
        name,
        data.get('type', ''),
        data.get('address', ''),
        data.get('capacity', 0),
        data.get('status', 1),
        data.get('price', 0),
        data.get('images', ''),
        data.get('opening_hours', ''),
        data.get('contact_phone', '')
    ))
    venue_id = cursor.lastrowid
    cursor.commit()
    cursor.close()
    
    return jsonify({'success': True, 'data': {'id': venue_id}})


@app.route('/api/admin/venues/<int:venue_id>', methods=['PUT'])
@require_admin
def update_venue(user, venue_id):
    """更新场地"""
    from business_common import db
    
    data = request.get_json() or {}
    
    cursor = db.get_cursor()
    cursor.execute("SELECT id FROM business_venues WHERE id=%s AND deleted=0", (venue_id,))
    if not cursor.fetchone():
        cursor.close()
        return jsonify({'success': False, 'message': '场地不存在'}), 404
    
    cursor.execute("""
        UPDATE business_venues 
        SET name=%s, type=%s, address=%s, capacity=%s, status=%s, price=%s, 
            images=%s, opening_hours=%s, contact_phone=%s, updated_at=NOW()
        WHERE id=%s
    """, (
        data.get('name'),
        data.get('type'),
        data.get('address'),
        data.get('capacity'),
        data.get('status'),
        data.get('price'),
        data.get('images'),
        data.get('opening_hours'),
        data.get('contact_phone'),
        venue_id
    ))
    cursor.commit()
    cursor.close()
    
    return jsonify({'success': True})


@app.route('/api/admin/venues/<int:venue_id>', methods=['DELETE'])
@require_admin
def delete_venue(user, venue_id):
    """删除场地"""
    from business_common import db
    
    cursor = db.get_cursor()
    cursor.execute("UPDATE business_venues SET deleted=1 WHERE id=%s", (venue_id,))
    cursor.commit()
    cursor.close()
    
    return jsonify({'success': True})


# ============ 用户管理 ============

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def list_users(user):
    """用户列表"""
    svc = AdminService()
    return jsonify(svc.list_members(
        keyword=request.args.get('keyword', ''),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


# ============ 健康检查 ============

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'module': 'admin-web', 'status': 'ok'})


# ============ 用户信息 ============

@app.route('/api/admin/userinfo', methods=['GET'])
def get_user_info():
    """获取当前登录用户信息"""
    from business_common.auth import verify_staff
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev', '0')
    
    if not token:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    user = verify_staff(token, isdev)
    if not user:
        return jsonify({'success': False, 'message': '登录已过期'}), 401
    
    # 返回用户信息，包含 user_name 字段
    return jsonify({
        'success': True,
        'data': {
            'user_id': user.get('user_id') or user.get('id'),
            'user_name': user.get('user_name') or user.get('name') or user.get('raw_data', {}).get('empName') or '管理员',
            'phone': user.get('phone') or user.get('mobile'),
            'is_staff': user.get('is_staff', True),
            'avatar': user.get('avatar') or user.get('avatar_url')
        }
    })


# ============ 逾期申请 ============

@app.route('/api/staff/applications/overdue', methods=['GET'])
def get_overdue_applications():
    """获取逾期未处理的申请单"""
    from business_common.auth import verify_staff
    from business_common import db
    from datetime import datetime, timedelta
    
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev', '0')
    
    if not token:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    user = verify_staff(token, isdev)
    if not user:
        return jsonify({'success': False, 'message': '登录已过期'}), 401
    
    # 查询逾期申请（超过3天未处理的待处理申请）
    overdue_threshold = datetime.now() - timedelta(days=3)
    
    sql = """
        SELECT COUNT(*) as count 
        FROM business_applications 
        WHERE status = 'pending' 
          AND deleted = 0 
          AND created_at < %s
    """
    cursor = db.get_cursor()
    cursor.execute(sql, (overdue_threshold,))
    result = cursor.fetchone()
    cursor.close()
    
    overdue_count = result['count'] if result else 0
    
    return jsonify({
        'success': True,
        'data': {
            'total_overdue': overdue_count,
            'overdue_list': []
        }
    })


# ============ 静态文件 ============

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


# ============ 公告管理 ============

@app.route('/api/admin/notices', methods=['GET'])
@require_admin
def list_notices(user):
    """公告列表"""
    from business_common import db
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    keyword = request.args.get('keyword', '')
    status = request.args.get('status', '')
    notice_type = request.args.get('notice_type', '')
    
    conditions = ["deleted=0"]
    params = []
    
    if keyword:
        conditions.append("title LIKE %s")
        params.append(f"%{keyword}%")
    if status:
        conditions.append("status=%s")
        params.append(status)
    if notice_type:
        conditions.append("notice_type=%s")
        params.append(notice_type)
    
    where = " AND ".join(conditions)
    
    try:
        count_result = db.get_one(f"SELECT COUNT(*) as cnt FROM business_notices WHERE {where}", params)
        total = count_result['cnt'] if count_result else 0
        
        offset = (page - 1) * page_size
        items = db.get_all(
            f"SELECT * FROM business_notices WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        ) or []
        
        return jsonify({'success': True, 'data': {'items': items, 'total': total}})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})


@app.route('/api/admin/notices/<int:notice_id>', methods=['GET'])
@require_admin
def get_notice(user, notice_id):
    """公告详情"""
    from business_common import db
    try:
        notice = db.get_one("SELECT * FROM business_notices WHERE id=%s AND deleted=0", [notice_id])
        if not notice:
            return jsonify({'success': False, 'msg': '公告不存在'})
        return jsonify({'success': True, 'data': notice})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})


@app.route('/api/admin/notices', methods=['POST'])
@require_admin
def create_notice(user):
    """创建公告"""
    from business_common import db
    data = request.get_json() or {}
    
    if not data.get('title'):
        return jsonify({'success': False, 'msg': '请填写公告标题'})
    if not data.get('content'):
        return jsonify({'success': False, 'msg': '请填写公告内容'})
    
    try:
        db.execute("""
            INSERT INTO business_notices (title, content, notice_type, importance, status, start_date, end_date, created_by, created_by_name, ec_id, project_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            data.get('title'),
            data.get('content'),
            data.get('notice_type', 'general'),
            data.get('importance', 0),
            data.get('status', 'draft'),
            data.get('start_date'),
            data.get('end_date'),
            user.get('id'),
            user.get('name', ''),
            user.get('ec_id'),
            user.get('project_id')
        ])
        return jsonify({'success': True, 'msg': '创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})


@app.route('/api/admin/notices/<int:notice_id>', methods=['PUT'])
@require_admin
def update_notice(user, notice_id):
    """更新公告"""
    from business_common import db
    data = request.get_json() or {}
    
    try:
        # 检查公告是否存在
        notice = db.get_one("SELECT id FROM business_notices WHERE id=%s AND deleted=0", [notice_id])
        if not notice:
            return jsonify({'success': False, 'msg': '公告不存在'})
        
        # 构建更新语句
        updates = []
        params = []
        
        for field in ['title', 'content', 'notice_type', 'importance', 'status', 'start_date', 'end_date']:
            if field in data:
                updates.append(f"{field}=%s")
                params.append(data[field])
        
        if not updates:
            return jsonify({'success': False, 'msg': '没有要更新的内容'})
        
        params.append(notice_id)
        db.execute(f"UPDATE business_notices SET {', '.join(updates)} WHERE id=%s", params)
        
        return jsonify({'success': True, 'msg': '更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})


@app.route('/api/admin/notices/<int:notice_id>', methods=['DELETE'])
@require_admin
def delete_notice(user, notice_id):
    """删除公告（软删除）"""
    from business_common import db
    try:
        notice = db.get_one("SELECT id FROM business_notices WHERE id=%s AND deleted=0", [notice_id])
        if not notice:
            return jsonify({'success': False, 'msg': '公告不存在'})
        
        db.execute("UPDATE business_notices SET deleted=1 WHERE id=%s", [notice_id])
        return jsonify({'success': True, 'msg': '删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})


# ============ 泰山城投模块 ============
from taishan_routes import taishan_admin_bp
app.register_blueprint(taishan_admin_bp)

# ============ 启动 ============

if __name__ == '__main__':
    print("管理端 Web 服务启动在端口 " + str(config.PORTS['admin']))
    app.run(host='0.0.0.0', port=config.PORTS['admin'], debug=False)
