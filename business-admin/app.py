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
