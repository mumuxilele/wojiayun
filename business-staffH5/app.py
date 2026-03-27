#!/usr/bin/env python3
"""
社区商业 - 员工端 H5 服务
端口: 22312
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import config, db, auth, utils

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ============ 员工认证 ============

def get_current_staff():
    """获取当前员工"""
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_staff(token, isdev) if token else None

def require_staff(f):
    """员工登录装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_staff()
        if not user:
            return jsonify({'success': False, 'msg': '请使用员工账号登录'})
        return f(user, *args, **kwargs)
    return decorated

# ============ 申请单 API ============

@app.route('/api/staff/applications', methods=['GET'])
@require_staff
def get_all_applications(user):
    """获取所有申请列表"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    status = request.args.get('status')
    app_type = request.args.get('app_type')
    keyword = request.args.get('keyword', '')
    
    where = "deleted=0"
    params = []
    
    if status:
        where += " AND status=%s"
        params.append(status)
    if app_type:
        where += " AND app_type=%s"
        params.append(app_type)
    if keyword:
        where += " AND (title LIKE %s OR content LIKE %s OR user_name LIKE %s)"
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])
    
    # 获取总数
    total = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {where}", params)
    
    # 获取列表
    offset = (page - 1) * page_size
    sql = f"SELECT * FROM business_applications WHERE {where} ORDER BY priority DESC, created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    items = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size
    }})

@app.route('/api/staff/applications/<app_id>', methods=['GET'])
@require_staff
def get_application_detail(user, app_id):
    """获取申请详情"""
    sql = "SELECT * FROM business_applications WHERE id=%s AND deleted=0"
    app = db.get_one(sql, [app_id])
    
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    
    return jsonify({'success': True, 'data': app})

@app.route('/api/staff/applications/<app_id>/process', methods=['POST'])
@require_staff
def process_application(user, app_id):
    """处理申请"""
    data = request.get_json() or {}
    action = data.get('action')  # process/reject/complete
    result = data.get('result', '')
    
    sql = "SELECT * FROM business_applications WHERE id=%s AND deleted=0"
    app = db.get_one(sql, [app_id])
    
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    
    if action == 'process':
        new_status = 'processing'
    elif action == 'reject':
        new_status = 'rejected'
    elif action == 'complete':
        new_status = 'completed'
    else:
        return jsonify({'success': False, 'msg': '无效操作'})
    
    sql = """UPDATE business_applications 
        SET status=%s, result=%s, assignee_id=%s, assignee_name=%s, 
            updated_at=NOW(), completed_at=NOW() WHERE id=%s"""
    db.execute(sql, [new_status, result, user['user_id'], user['user_name'], app_id])
    
    return jsonify({'success': True, 'msg': '处理成功'})

# ============ 订单 API ============

@app.route('/api/staff/orders', methods=['GET'])
@require_staff
def get_all_orders(user):
    """获取所有订单"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    status = request.args.get('status')
    
    where = "deleted=0"
    params = []
    
    if status:
        where += " AND status=%s"
        params.append(status)
    
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

@app.route('/api/staff/orders/<order_id>', methods=['GET'])
@require_staff
def get_order_detail(user, order_id):
    """获取订单详情"""
    order = db.get_one("SELECT * FROM business_orders WHERE id=%s AND deleted=0", [order_id])
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    
    items = db.get_all("SELECT * FROM business_order_items WHERE order_id=%s", [order_id])
    
    return jsonify({'success': True, 'data': {'order': order, 'items': items}})

# ============ 统计数据 ============

@app.route('/api/staff/statistics', methods=['GET'])
@require_staff
def get_statistics(user):
    """获取统计数据"""
    # 待处理申请数
    pending_apps = db.get_one("SELECT COUNT(*) as cnt FROM business_applications WHERE status='pending' AND deleted=0")
    
    # 处理中申请数
    processing_apps = db.get_one("SELECT COUNT(*) as cnt FROM business_applications WHERE status='processing' AND deleted=0")
    
    # 今日订单
    today_orders = db.get_one("""SELECT COUNT(*) as cnt FROM business_orders 
        WHERE DATE(create_time)=CURDATE() AND deleted=0""")
    
    # 今日收入
    today_income = db.get_one("""SELECT COALESCE(SUM(total_amount),0) as total FROM business_orders 
        WHERE DATE(create_time)=CURDATE() AND status='paid' AND deleted=0""")
    
    return jsonify({'success': True, 'data': {
        'pending_applications': pending_apps['cnt'] if pending_apps else 0,
        'processing_applications': processing_apps['cnt'] if processing_apps else 0,
        'today_orders': today_orders['cnt'] if today_orders else 0,
        'today_income': float(today_income['total']) if today_income else 0
    }})

# ============ 会员/优惠券 ============

@app.route('/api/staff/members', methods=['GET'])
@require_staff
def get_members(user):
    """获取会员列表"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    keyword = request.args.get('keyword', '')
    
    where = "1=1"
    params = []
    if keyword:
        where += " AND (user_name LIKE %s OR phone LIKE %s)"
        params.append(f"%{keyword}%")
    
    total = db.get_total(f"SELECT COUNT(*) FROM business_members WHERE {where}", params)
    
    offset = (page - 1) * page_size
    sql = f"SELECT * FROM business_members WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    members = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {'items': members, 'total': total}})

# ============ 健康检查 ============

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'module': 'staff-h5', 'status': 'ok'})

# ============ 静态文件 ============

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

# ============ 启动 ============

if __name__ == '__main__':
    print(f"员工端 H5 服务启动在端口 {config.PORTS['staff']}")
    app.run(host='0.0.0.0', port=config.PORTS['staff'], debug=False)
