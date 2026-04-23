#!/usr/bin/env python3
"""
社区商业 - 管理端 Web 服务
端口: 22313
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import config, db, auth, utils

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ============ 管理员认证 ============

def get_current_admin():
    """获取当前管理员"""
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    # 管理员必须有员工身份
    return auth.verify_staff(token, isdev) if token else None

def require_admin(f):
    """管理员登录装饰器"""
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
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    status = request.args.get('status')
    app_type = request.args.get('app_type')
    keyword = request.args.get('keyword', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    where = "1=1"
    params = []
    
    if status:
        where += " AND status=%s"
        params.append(status)
    if app_type:
        where += " AND app_type=%s"
        params.append(app_type)
    if keyword:
        where += " AND (title LIKE %s OR content LIKE %s OR user_name LIKE %s OR app_no LIKE %s)"
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw])
    if start_date:
        where += " AND created_at >= %s"
        params.append(start_date)
    if end_date:
        where += " AND created_at <= %s"
        params.append(end_date + ' 23:59:59')
    
    total = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {where} AND deleted=0", params)
    
    offset = (page - 1) * page_size
    sql = f"SELECT * FROM business_applications WHERE {where} AND deleted=0 ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    items = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size
    }})

@app.route('/api/admin/applications/<app_id>', methods=['GET'])
@require_admin
def get_application(user, app_id):
    """申请单详情"""
    app = db.get_one("SELECT * FROM business_applications WHERE id=%s", [app_id])
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    return jsonify({'success': True, 'data': app})

@app.route('/api/admin/applications/<app_id>', methods=['PUT'])
@require_admin
def update_application(user, app_id):
    """修改申请单"""
    data = request.get_json() or {}
    
    fields = ['title', 'content', 'status', 'priority', 'result', 'assignee_id', 'assignee_name']
    updates = []
    params = []
    
    for field in fields:
        if field in data:
            updates.append(f"{field}=%s")
            params.append(data[field])
    
    if not updates:
        return jsonify({'success': False, 'msg': '无更新内容'})
    
    params.append(app_id)
    db.execute(f"UPDATE business_applications SET {','.join(updates)}, updated_at=NOW() WHERE id=%s", params)
    
    return jsonify({'success': True, 'msg': '修改成功'})

@app.route('/api/admin/applications/<app_id>', methods=['DELETE'])
@require_admin
def delete_application(user, app_id):
    """删除申请单"""
    db.execute("UPDATE business_applications SET deleted=1 WHERE id=%s", [app_id])
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 订单管理 ============

@app.route('/api/admin/orders', methods=['GET'])
@require_admin
def list_orders(user):
    """订单列表"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    status = request.args.get('status')
    keyword = request.args.get('keyword', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    where = "deleted=0"
    params = []
    
    if status:
        where += " AND status=%s"
        params.append(status)
    if keyword:
        where += " AND (order_no LIKE %s OR user_name LIKE %s)"
        kw = f"%{keyword}%"
        params.extend([kw, kw])
    if start_date:
        where += " AND create_time >= %s"
        params.append(start_date)
    if end_date:
        where += " AND create_time <= %s"
        params.append(end_date + ' 23:59:59')
    
    total = db.get_total(f"SELECT COUNT(*) FROM business_orders WHERE {where}", params)
    
    offset = (page - 1) * page_size
    sql = f"SELECT * FROM business_orders WHERE {where} ORDER BY create_time DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    orders = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {
        'items': orders,
        'total': total,
        'page': page,
        'page_size': page_size
    }})

@app.route('/api/admin/orders/<order_id>', methods=['GET'])
@require_admin
def get_order(user, order_id):
    """订单详情"""
    order = db.get_one("SELECT * FROM business_orders WHERE id=%s", [order_id])
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    
    items = db.get_all("SELECT * FROM business_order_items WHERE order_id=%s", [order_id])
    
    return jsonify({'success': True, 'data': {'order': order, 'items': items}})

@app.route('/api/admin/orders/<order_id>', methods=['PUT'])
@require_admin
def update_order(user, order_id):
    """修改订单"""
    data = request.get_json() or {}
    
    fields = ['status', 'pay_status', 'total_amount', 'remark']
    updates = []
    params = []
    
    for field in fields:
        if field in data:
            updates.append(f"{field}=%s")
            params.append(data[field])
    
    if not updates:
        return jsonify({'success': False, 'msg': '无更新内容'})
    
    params.append(order_id)
    db.execute(f"UPDATE business_orders SET {','.join(updates)} WHERE id=%s", params)
    
    return jsonify({'success': True, 'msg': '修改成功'})

@app.route('/api/admin/orders/<order_id>', methods=['DELETE'])
@require_admin
def delete_order(user, order_id):
    """删除订单"""
    db.execute("UPDATE business_orders SET deleted=1 WHERE id=%s", [order_id])
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 门店管理 ============

@app.route('/api/admin/shops', methods=['GET'])
@require_admin
def list_shops(user):
    """门店列表"""
    shops = db.get_all("SELECT * FROM business_shops WHERE deleted=0 ORDER BY id")
    return jsonify({'success': True, 'data': shops})

@app.route('/api/admin/shops/<shop_id>', methods=['GET'])
@require_admin
def get_shop(user, shop_id):
    """门店详情"""
    shop = db.get_one("SELECT * FROM business_shops WHERE id=%s", [shop_id])
    return jsonify({'success': True, 'data': shop})

@app.route('/api/admin/shops', methods=['POST'])
@require_admin
def create_shop(user):
    """创建门店"""
    data = request.get_json() or {}
    sql = """INSERT INTO business_shops (shop_name, shop_type, address, phone, status)
        VALUES (%s, %s, %s, %s, %s)"""
    shop_id = db.execute(sql, [data.get('shop_name'), data.get('shop_type'), data.get('address'), data.get('phone'), data.get('status', 'open')])
    return jsonify({'success': True, 'msg': '创建成功', 'data': {'id': shop_id}})

@app.route('/api/admin/shops/<shop_id>', methods=['PUT'])
@require_admin
def update_shop(user, shop_id):
    """修改门店"""
    data = request.get_json() or {}
    fields = ['shop_name', 'shop_type', 'address', 'phone', 'status', 'description']
    updates = []
    params = []
    for field in fields:
        if field in data:
            updates.append(f"{field}=%s")
            params.append(data[field])
    if updates:
        params.append(shop_id)
        db.execute(f"UPDATE business_shops SET {','.join(updates)} WHERE id=%s", params)
    return jsonify({'success': True, 'msg': '修改成功'})

@app.route('/api/admin/shops/<shop_id>', methods=['DELETE'])
@require_admin
def delete_shop(user, shop_id):
    """删除门店"""
    db.execute("UPDATE business_shops SET deleted=1 WHERE id=%s", [shop_id])
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 统计数据 ============

@app.route('/api/admin/statistics', methods=['GET'])
@require_admin
def get_statistics(user):
    """综合统计"""
    # 申请单统计
    app_stats = db.get_all("SELECT status, COUNT(*) as cnt FROM business_applications WHERE deleted=0 GROUP BY status")
    
    # 订单统计
    order_stats = db.get_all("SELECT status, COUNT(*) as cnt, SUM(total_amount) as total FROM business_orders WHERE deleted=0 GROUP BY status")
    
    # 今日数据
    today_apps = db.get_one("SELECT COUNT(*) as cnt FROM business_applications WHERE DATE(created_at)=CURDATE() AND deleted=0")
    today_orders = db.get_one("SELECT COUNT(*) as cnt, COALESCE(SUM(total_amount),0) as total FROM business_orders WHERE DATE(create_time)=CURDATE() AND deleted=0")
    
    return jsonify({'success': True, 'data': {
        'application_stats': app_stats,
        'order_stats': order_stats,
        'today': {
            'applications': today_apps['cnt'] if today_apps else 0,
            'orders': today_orders['cnt'] if today_orders else 0,
            'income': float(today_orders['total']) if today_orders else 0
        }
    }})

# ============ 用户管理 ============

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def list_users(user):
    """用户列表"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    keyword = request.args.get('keyword', '')
    
    where = "1=1"
    params = []
    if keyword:
        where += " AND (user_name LIKE %s OR phone LIKE %s)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    
    total = db.get_total(f"SELECT COUNT(*) FROM business_members WHERE {where}", params)
    
    offset = (page - 1) * page_size
    sql = f"SELECT * FROM business_members WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    users = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {'items': users, 'total': total}})

# ============ 健康检查 ============

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'module': 'admin-web', 'status': 'ok'})

# ============ 静态文件 ============

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

# ============ 启动 ============

if __name__ == '__main__':
    print(f"管理端 Web 服务启动在端口 {config.PORTS['admin']}")
    app.run(host='0.0.0.0', port=config.PORTS['admin'], debug=False)
