#!/usr/bin/env python3
"""Staff H5 Service - V7.0 Enhanced"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import time
import json
import base64
import uuid
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import config, db, auth, utils, error_handler, notification, rate_limiter, OrderStatusTransition
from business_common.cache_service import cache_get, cache_set, cache_delete
from business_common.employee_sync_service import employee_sync, init_employee_sync

# 图片上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# 注册全局错误处理器
error_handler.register_error_handlers(app)

# 初始化员工同步服务
init_employee_sync(db, cache_get and cache_set and type('cache', (), {'get': cache_get, 'set': cache_set}) or None)

@app.after_request
def add_headers(response):
    response.headers['X-Response-Time'] = str(int(time.time() * 1000))
    return response

def get_current_staff():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_staff(token, isdev) if token else None

def require_staff(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_staff()
        if not user:
            return jsonify({'success': False, 'msg': '请使用员工账号登录'})
        return f(user, *args, **kwargs)
    return decorated

@app.route('/api/staff/stats', methods=['GET'])
@require_staff
def get_staff_stats(user):
    """员工端统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().get_staff_stats(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': stats})


@app.route('/api/staff/statistics', methods=['GET'])
@require_staff
def get_staff_statistics(user):
    """员工端统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().get_staff_statistics(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': stats})


@app.route('/api/staff/statistics/trend', methods=['GET'])
@require_staff
def get_staff_statistics_trend(user):
    """V14新增：统计趋势数据（近N天的订单和收入趋势）"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    rng = request.args.get('range', 'today')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if not date_from or not date_to:
        date_from, date_to = _get_date_range(rng)
        if not date_from:
            date_from = date_to = time.strftime('%Y-%m-%d')

    scope = "deleted=0"
    p = []
    if ec_id:
        scope += " AND ec_id=%s"; p.append(ec_id)
    if project_id:
        scope += " AND project_id=%s"; p.append(project_id)

    # 订单趋势（含收入）
    order_trend = []
    try:
        date_scope, date_p = _build_scope_with_date(scope, p.copy(), date_from, date_to)
        rows = db.get_all(
            f"SELECT DATE(created_at) as date, COUNT(*) as order_cnt, "
            f"COALESCE(SUM(CASE WHEN order_status IN ('paid','completed') THEN actual_amount ELSE 0 END),0) as income "
            f"FROM business_orders WHERE {date_scope} "
            f"GROUP BY DATE(created_at) ORDER BY date ASC",
            date_p
        )
        # 填充缺失日期
        from datetime import date, timedelta
        date_map = {}
        for r in (rows or []):
            k = str(r['date']) if r.get('date') else ''
            if k:
                date_map[k] = {'date': k, 'order_cnt': r['order_cnt'], 'income': float(r['income'] or 0)}
        d_from = date.fromisoformat(date_from)
        d_to = date.fromisoformat(date_to)
        for i in range((d_to - d_from).days + 1):
            d = str(d_from + timedelta(days=i))
            if d in date_map:
                order_trend.append(date_map[d])
            else:
                order_trend.append({'date': d, 'order_cnt': 0, 'income': 0})
    # 申请趋势
    app_trend = []
    try:
        date_scope, date_p = _build_scope_with_date(scope, p.copy(), date_from, date_to)
        rows = db.get_all(
            f"SELECT DATE(created_at) as date, COUNT(*) as app_cnt "
            f"FROM business_applications WHERE {date_scope} "
            f"GROUP BY DATE(created_at) ORDER BY date ASC",
            date_p
        )
        app_map = {str(r['date']): r['app_cnt'] for r in (rows or []) if r.get('date')}
        for item in order_trend:
            item['app_cnt'] = app_map.get(item['date'], 0)
    return jsonify({'success': True, 'data': {'trend': order_trend}})

@app.route('/api/staff/statistics/performance', methods=['GET'])
@require_staff
def get_staff_performance(user):
    """V14新增：个人绩效数据"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    staff_id = user.get('user_id')
    rng = request.args.get('range', 'today')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if not date_from or not date_to:
        date_from, date_to = _get_date_range(rng)
        if not date_from:
            date_from = date_to = time.strftime('%Y-%m-%d')

    # 我处理的申请数
    processed_count = 0
    try:
        scope = "deleted=0 AND assignee_id=%s"
        params = [staff_id]
        scope, params = _build_scope_with_date(scope, params, date_from, date_to)
        processed_count = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {scope}", params)
    except Exception:
        pass

    # 我完成的订单数（发货+确认完成）
    completed_orders = 0
    try:
        # 通过审计日志查询
        scope2 = "action IN ('ship_order','update_order','complete_booking') AND user_id=%s"
        params2 = [staff_id]
        scope2, params2 = _build_scope_with_date(scope2, params2, date_from, date_to)
        completed_orders = db.get_total(f"SELECT COUNT(*) FROM business_staff_operation_logs WHERE {scope2}", params2)
    except Exception:
        pass

    # 申请完成率
    completion_rate = 0
    try:
        my_total = db.get_total(
            "SELECT COUNT(*) FROM business_applications WHERE deleted=0 AND assignee_id=%s",
            [staff_id]
        )
        my_completed = db.get_total(
            "SELECT COUNT(*) FROM business_applications WHERE deleted=0 AND assignee_id=%s AND status='completed'",
            [staff_id]
        )
        completion_rate = round(my_completed / my_total * 100, 1) if my_total > 0 else 0
    except Exception:
        pass

    return jsonify({'success': True, 'data': {
        'processed_count': processed_count,
        'completed_orders': completed_orders,
        'completion_rate': completion_rate
    }})

@app.route('/api/staff/statistics/members', methods=['GET'])
@require_staff
def get_staff_member_activity(user):
    """会员活动统计"""
    from business_common.statistics_service import get_stats_service
    days = int(request.args.get('days', 7))
    stats = get_stats_service().get_staff_member_activity(
        user.get('ec_id'), user.get('project_id'), days
    )
    return jsonify({'success': True, 'data': stats})


@app.route('/api/staff/applications', methods=['GET'])
@require_staff
def get_all_applications(user):
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    app_type = request.args.get('app_type')
    keyword = request.args.get('keyword', '')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    where = "deleted=0"
    params = []
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)
    if status:
        where += " AND status=%s"; params.append(status)
    if app_type:
        where += " AND app_type=%s"; params.append(app_type)
    if keyword:
        where += " AND (title LIKE %s OR content LIKE %s OR user_name LIKE %s)"
        kw = "%" + keyword + "%"
        params.extend([kw, kw, kw])
    
    total = db.get_total("SELECT COUNT(*) FROM business_applications WHERE " + where, params)
    offset = (page - 1) * page_size
    sql = "SELECT id, app_no, app_type, title, status, user_name, user_phone, priority, created_at, assignee_name FROM business_applications WHERE " + where + " ORDER BY priority DESC, created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    items = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size, 'pages': (total + page_size - 1) // page_size}})

@app.route('/api/staff/applications/<app_id>', methods=['GET'])
@require_staff
def get_application_detail(user, app_id):
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    # 修复：添加数据范围过滤，防止跨项目查看申请单
    sql = "SELECT * FROM business_applications WHERE id=%s AND deleted=0"
    params = [app_id]
    if ec_id:
        sql += " AND ec_id=%s"
        params.append(ec_id)
    if project_id:
        sql += " AND project_id=%s"
        params.append(project_id)
    app = db.get_one(sql, params)
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    if app.get('images'):
        try:
            app['images_list'] = json.loads(app['images'])
        except:
            app['images_list'] = []
    
    # 获取处理记录 - 按时间降序，最新的在前
    logs = db.get_all(
        "SELECT id, action, handler_id, handler_name, remark, images, created_at "
        "FROM business_application_logs WHERE application_id=%s ORDER BY created_at DESC",
        [app_id]
    )
    for log in logs or []:
        if log.get('images'):
            try:
                log['images_list'] = json.loads(log['images'])
            except:
                log['images_list'] = []
        else:
            log['images_list'] = []
    
    app['process_logs'] = logs or []
    
    return jsonify({'success': True, 'data': app})

@app.route('/api/staff/applications/<app_id>/process', methods=['POST'])
@require_staff
@rate_limiter.rate_limit(limit=30, window_seconds=60)
def process_application(user, app_id):
    data = request.get_json() or {}
    action = data.get('action')
    result = data.get('result', '')
    images = data.get('images', [])  # 处理时上传的图片
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    # 修复：添加数据范围过滤
    sql = "SELECT * FROM business_applications WHERE id=%s AND deleted=0"
    params = [app_id]
    if ec_id:
        sql += " AND ec_id=%s"
        params.append(ec_id)
    if project_id:
        sql += " AND project_id=%s"
        params.append(project_id)
    app = db.get_one(sql, params)
    
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    
    if action == 'process':
        new_status = 'processing'
    elif action == 'reject':
        new_status = 'rejected'
    elif action == 'complete':
        new_status = 'completed'
    elif action == 'comment':
        # 仅添加备注，不改变状态
        new_status = None
    else:
        return jsonify({'success': False, 'msg': '无效操作'})
    
    # 保存处理记录
    log_images = json.dumps(images) if images else None
    db.execute(
        "INSERT INTO business_application_logs (application_id, action, handler_id, handler_name, remark, images) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        [app_id, action, user['user_id'], user['user_name'], result, log_images]
    )
    
    # 更新申请状态
    if new_status:
        if new_status == 'completed':
            sql = "UPDATE business_applications SET status=%s, result=%s, assignee_id=%s, assignee_name=%s, updated_at=NOW(), completed_at=NOW() WHERE id=%s"
        else:
            sql = "UPDATE business_applications SET status=%s, result=%s, assignee_id=%s, assignee_name=%s, updated_at=NOW() WHERE id=%s"
        db.execute(sql, [new_status, result, user['user_id'], user['user_name'], app_id])
        # 状态变更时通知用户
        if new_status in ('processing', 'completed', 'rejected'):
            try:
                notification.notify_application_status(
                    app.get('user_id', ''), app.get('app_no', ''), new_status, app.get('status', '')
                )
    
    return jsonify({'success': True, 'msg': '处理成功'})

@app.route('/api/staff/orders', methods=['GET'])
@require_staff
def get_all_orders(user):
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    where = "deleted=0"
    params = []
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)
    if status:
        where += " AND order_status=%s"; params.append(status)
    
    total = db.get_total("SELECT COUNT(*) FROM business_orders WHERE " + where, params)
    offset = (page - 1) * page_size
    sql = "SELECT id, order_no, order_status, user_name, user_phone, total_amount, actual_amount, created_at FROM business_orders WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    orders = db.get_all(sql, params)
    
    return jsonify({'success': True, 'data': {'items': orders, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/staff/orders/<order_id>', methods=['GET'])
@require_staff
def get_order_detail(user, order_id):
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    # 修复：添加数据范围过滤
    sql = "SELECT * FROM business_orders WHERE id=%s AND deleted=0"
    params = [order_id]
    if ec_id:
        sql += " AND ec_id=%s"
        params.append(ec_id)
    if project_id:
        sql += " AND project_id=%s"
        params.append(project_id)
    order = db.get_one(sql, params)
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在或无权限查看'})
    return jsonify({'success': True, 'data': order})

@app.route('/api/staff/orders/<order_id>/status', methods=['POST'])
@require_staff
def update_order_status(user, order_id):
    """P13修复：添加订单状态流转校验"""
    data = request.get_json() or {}
    status = data.get('status')
    
    if not status:
        return jsonify({'success': False, 'msg': '请提供状态'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    # 验证订单是否属于当前员工管辖范围
    check_sql = "SELECT order_status FROM business_orders WHERE id=%s AND deleted=0"
    check_params = [order_id]
    if ec_id:
        check_sql += " AND ec_id=%s"
        check_params.append(ec_id)
    if project_id:
        check_sql += " AND project_id=%s"
        check_params.append(project_id)
    
    order = db.get_one(check_sql, check_params)
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在或无权限操作'})
    
    old_status = order.get('order_status') or 'pending'
    
    # P13新增：状态流转校验
    allowed, error_msg = OrderStatusTransition.can_transition(old_status, status)
    if not allowed:
        return jsonify({'success': False, 'msg': error_msg or '不允许的状态流转'})
    
    sql = "UPDATE business_orders SET order_status=%s, updated_at=NOW() WHERE id=%s"
    db.execute(sql, [status, order_id])
    
    return jsonify({'success': True, 'msg': '更新成功'})

ALLOWED_IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_UPLOAD_SIZE_MB = 5  # 限制5MB

@app.route('/api/staff/upload', methods=['POST'])
@require_staff
def upload_image(user):
    """上传图片（安全版：文件类型白名单 + 大小限制）"""
    try:
        data = request.get_json() or {}
        file_data = data.get('file')
        if not file_data:
            return jsonify({'success': False, 'msg': '没有图片数据'})
        
        # 解析base64数据并校验大小
        raw = file_data
        if ',' in file_data:
            header, raw = file_data.split(',', 1)
        
        # 检查文件大小（base64约比原始大33%）
        estimated_bytes = len(raw) * 3 // 4
        if estimated_bytes > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            return jsonify({'success': False, 'msg': f'文件超过{MAX_UPLOAD_SIZE_MB}MB限制'})
        
        # 校验扩展名
        ext = (data.get('ext', 'jpg') or 'jpg').lower().lstrip('.')
        if ext not in ALLOWED_IMAGE_EXTS:
            return jsonify({'success': False, 'msg': f'不支持的文件类型，仅允许：{", ".join(ALLOWED_IMAGE_EXTS)}'})
        
        # 生成安全文件名（不使用用户提供的文件名）
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        import base64 as b64
        decoded = b64.b64decode(raw)
        
        # 二次校验：检查文件头魔数（防止伪造扩展名）
        magic_map = {
            b'\xff\xd8\xff': ['jpg', 'jpeg'],
            b'\x89PNG': ['png'],
            b'GIF8': ['gif'],
            b'RIFF': ['webp'],
        }
        valid_magic = False
        for magic, exts in magic_map.items():
            if decoded[:len(magic)] == magic and ext in exts:
                valid_magic = True
                break
        if not valid_magic:
            return jsonify({'success': False, 'msg': '文件内容与扩展名不匹配'})
        
        with open(filepath, 'wb') as f:
            f.write(decoded)
        
        url = f"/uploads/{filename}"
        return jsonify({'success': True, 'data': {'url': url, 'filename': filename}})
        return jsonify({'success': False, 'msg': '上传失败，请重试'})

@app.route('/uploads/<filename>')
def serve_upload(filename):
    """访问上传的图片"""
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'staff-h5', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})

# ============ V27.0 客户标签管理 ============

@app.route('/api/staff/customer-tags', methods=['GET'])
@require_staff
def get_customer_tags(user):
    """V27.0: 获取客户标签列表"""
    try:
        tags = db.get_all("""
            SELECT id, tag_name, tag_color, tag_type, description, sort_order, status
            FROM business_customer_tags 
            WHERE status=1 
            ORDER BY sort_order, id
        """) or []
        
        # 获取各标签下的客户数量
        staff_id = user.get('user_id')
        for tag in tags:
            count = db.get_total("""
                SELECT COUNT(*) FROM business_customer_tag_relations 
                WHERE staff_id=%s AND tag_id=%s
            """, [staff_id, tag['id']])
            tag['customer_count'] = count
        
        return jsonify({'success': True, 'data': tags})
        return jsonify({'success': True, 'data': []})

@app.route('/api/staff/customer-tags', methods=['POST'])
@require_staff
def create_customer_tag(user):
    """V27.0: 创建客户标签"""
    data = request.get_json() or {}
    tag_name = data.get('tag_name', '').strip()
    tag_color = data.get('tag_color', '#1890ff')
    description = data.get('description', '')
    
    if not tag_name:
        return jsonify({'success': False, 'msg': '标签名称不能为空'})
    
    if len(tag_name) > 20:
        return jsonify({'success': False, 'msg': '标签名称不能超过20个字符'})
    
    try:
        # 获取当前最大排序值
        max_order = db.get_one("SELECT MAX(sort_order) as max_order FROM business_customer_tags")
        sort_order = (max_order['max_order'] or 0) + 1
        
        tag_id = db.execute("""
            INSERT INTO business_customer_tags 
            (tag_name, tag_color, tag_type, description, sort_order, status, created_by)
            VALUES (%s, %s, 'custom', %s, %s, 1, %s)
        """, [tag_name, tag_color, description, sort_order, user.get('user_name', '')])
        
        return jsonify({'success': True, 'msg': '标签创建成功', 'data': {'id': tag_id}})
        return jsonify({'success': False, 'msg': '创建失败'})

@app.route('/api/staff/customer-tags/<int:tag_id>', methods=['PUT'])
@require_staff
def update_customer_tag(user, tag_id):
    """V27.0: 更新客户标签"""
    data = request.get_json() or {}
    tag_name = data.get('tag_name', '').strip()
    tag_color = data.get('tag_color')
    description = data.get('description')
    
    # 检查标签是否存在且属于自定义标签
    tag = db.get_one("SELECT * FROM business_customer_tags WHERE id=%s AND status=1", [tag_id])
    if not tag:
        return jsonify({'success': False, 'msg': '标签不存在'})
    
    if tag.get('tag_type') == 'system':
        return jsonify({'success': False, 'msg': '系统标签不可修改'})
    
    try:
        updates = []
        params = []
        if tag_name:
            if len(tag_name) > 20:
                return jsonify({'success': False, 'msg': '标签名称不能超过20个字符'})
            updates.append("tag_name=%s")
            params.append(tag_name)
        if tag_color:
            updates.append("tag_color=%s")
            params.append(tag_color)
        if description is not None:
            updates.append("description=%s")
            params.append(description)
        
        if updates:
            params.append(tag_id)
            db.execute(f"UPDATE business_customer_tags SET {', '.join(updates)} WHERE id=%s", params)
        
        return jsonify({'success': True, 'msg': '标签更新成功'})
        return jsonify({'success': False, 'msg': '更新失败'})

@app.route('/api/staff/customer-tags/<int:tag_id>', methods=['DELETE'])
@require_staff
def delete_customer_tag(user, tag_id):
    """V27.0: 删除客户标签"""
    # 检查标签是否存在且属于自定义标签
    tag = db.get_one("SELECT * FROM business_customer_tags WHERE id=%s AND status=1", [tag_id])
    if not tag:
        return jsonify({'success': False, 'msg': '标签不存在'})
    
    if tag.get('tag_type') == 'system':
        return jsonify({'success': False, 'msg': '系统标签不可删除'})
    
    try:
        # 删除标签关联关系
        db.execute("DELETE FROM business_customer_tag_relations WHERE tag_id=%s", [tag_id])
        # 删除标签
        db.execute("UPDATE business_customer_tags SET status=0 WHERE id=%s", [tag_id])
        return jsonify({'success': True, 'msg': '标签已删除'})
        return jsonify({'success': False, 'msg': '删除失败'})

@app.route('/api/staff/customers', methods=['GET'])
@require_staff
def get_my_customers(user):
    """V27.0: 获取我的客户列表（带标签）"""
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 100)
    tag_id = request.args.get('tag_id')  # 可选：按标签筛选
    keyword = request.args.get('keyword', '').strip()  # 可选：搜索用户名/手机
    
    staff_id = user.get('user_id')
    
    # 构建查询
    where = "r.staff_id=%s"
    params = [staff_id]
    
    if tag_id:
        where += " AND r.tag_id=%s"
        params.append(tag_id)
    
    if keyword:
        where += " AND (m.user_name LIKE %s OR m.phone LIKE %s)"
        kw = f'%{keyword}%'
        params.extend([kw, kw])
    
    # 查询总数
    total = db.get_total(f"""
        SELECT COUNT(DISTINCT r.customer_user_id) 
        FROM business_customer_tag_relations r
        LEFT JOIN business_members m ON r.customer_user_id = m.user_id
        WHERE {where}
    """, params)
    
    # 分页查询
    offset = (page - 1) * page_size
    customers = db.get_all(f"""
        SELECT DISTINCT r.customer_user_id, m.user_name, m.phone, m.member_level,
               m.total_consume, m.checkin_streak, m.last_checkin_date,
               r.updated_at as tagged_at
        FROM business_customer_tag_relations r
        LEFT JOIN business_members m ON r.customer_user_id = m.user_id
        WHERE {where}
        ORDER BY r.updated_at DESC
        LIMIT %s OFFSET %s
    """, params + [page_size, offset])
    
    # 查询每个客户的标签
    for customer in (customers or []):
        tags = db.get_all("""
            SELECT ct.id, ct.tag_name, ct.tag_color
            FROM business_customer_tag_relations r
            JOIN business_customer_tags ct ON r.tag_id = ct.id
            WHERE r.staff_id=%s AND r.customer_user_id=%s AND ct.status=1
        """, [staff_id, customer['customer_user_id']])
        customer['tags'] = tags or []
    
    return jsonify({'success': True, 'data': {
        'items': customers or [],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/staff/customers/<int:customer_user_id>/tags', methods=['GET'])
@require_staff
def get_customer_tags_by_user(user, customer_user_id):
    """V27.0: 获取指定客户的所有标签"""
    staff_id = user.get('user_id')
    
    tags = db.get_all("""
        SELECT ct.id, ct.tag_name, ct.tag_color, ct.tag_type, r.note, r.created_at as tagged_at
        FROM business_customer_tag_relations r
        JOIN business_customer_tags ct ON r.tag_id = ct.id
        WHERE r.staff_id=%s AND r.customer_user_id=%s AND ct.status=1
    """, [staff_id, customer_user_id])
    
    return jsonify({'success': True, 'data': tags or []})

@app.route('/api/staff/customers/<int:customer_user_id>/tags', methods=['POST'])
@require_staff
def add_customer_tag(user, customer_user_id):
    """V27.0: 给客户添加标签"""
    data = request.get_json() or {}
    tag_id = data.get('tag_id')
    note = data.get('note', '')
    
    if not tag_id:
        return jsonify({'success': False, 'msg': '请选择标签'})
    
    staff_id = user.get('user_id')
    
    # 检查标签是否存在
    tag = db.get_one("SELECT * FROM business_customer_tags WHERE id=%s AND status=1", [tag_id])
    if not tag:
        return jsonify({'success': False, 'msg': '标签不存在'})
    
    # 检查是否已添加过该标签
    exists = db.get_one("""
        SELECT id FROM business_customer_tag_relations 
        WHERE staff_id=%s AND customer_user_id=%s AND tag_id=%s
    """, [staff_id, customer_user_id, tag_id])
    
    if exists:
        return jsonify({'success': False, 'msg': '该标签已添加'})
    
    try:
        db.execute("""
            INSERT INTO business_customer_tag_relations 
            (staff_id, customer_user_id, tag_id, note)
            VALUES (%s, %s, %s, %s)
        """, [staff_id, customer_user_id, tag_id, note])
        return jsonify({'success': True, 'msg': '标签添加成功'})
        return jsonify({'success': False, 'msg': '添加失败'})

@app.route('/api/staff/customers/<int:customer_user_id>/tags/<int:tag_id>', methods=['DELETE'])
@require_staff
def remove_customer_tag(user, customer_user_id, tag_id):
    """V27.0: 移除客户标签"""
    staff_id = user.get('user_id')
    
    try:
        result = db.execute("""
            DELETE FROM business_customer_tag_relations 
            WHERE staff_id=%s AND customer_user_id=%s AND tag_id=%s
        """, [staff_id, customer_user_id, tag_id])
        return jsonify({'success': True, 'msg': '标签已移除'})
        return jsonify({'success': False, 'msg': '移除失败'})

@app.route('/api/staff/customers/<int:customer_user_id>/tags/batch', methods=['PUT'])
@require_staff
def batch_update_customer_tags(user, customer_user_id):
    """V27.0: 批量更新客户标签"""
    data = request.get_json() or {}
    tag_ids = data.get('tag_ids', [])  # 要保留的标签ID列表
    
    staff_id = user.get('user_id')
    
    try:
        # 删除不在列表中的标签
        if tag_ids:
            placeholders = ','.join(['%s'] * len(tag_ids))
            db.execute(f"""
                DELETE FROM business_customer_tag_relations 
                WHERE staff_id=%s AND customer_user_id=%s AND tag_id NOT IN ({placeholders})
            """, [staff_id, customer_user_id] + tag_ids)
        else:
            # 空列表表示清空所有标签
            db.execute("""
                DELETE FROM business_customer_tag_relations 
                WHERE staff_id=%s AND customer_user_id=%s
            """, [staff_id, customer_user_id])
        
        return jsonify({'success': True, 'msg': '标签更新成功'})
        return jsonify({'success': False, 'msg': '更新失败'})

@app.route('/api/staff/customers/all', methods=['GET'])
@require_staff
def get_all_customer_stats(user):
    """V27.0: 获取员工客户统计"""
    staff_id = user.get('user_id')
    
    # 总客户数
    total_customers = db.get_total("""
        SELECT COUNT(DISTINCT customer_user_id) 
        FROM business_customer_tag_relations 
        WHERE staff_id=%s
    """, [staff_id])
    
    # 各标签客户数
    tag_stats = db.get_all("""
        SELECT ct.id, ct.tag_name, ct.tag_color, COUNT(r.customer_user_id) as count
        FROM business_customer_tags ct
        LEFT JOIN business_customer_tag_relations r ON ct.id = r.tag_id AND r.staff_id=%s
        WHERE ct.status=1
        GROUP BY ct.id, ct.tag_name, ct.tag_color
        ORDER BY count DESC
    """, [staff_id]) or []
    
    # 最近新增客户
    recent_customers = db.get_all("""
        SELECT m.user_name, m.phone, m.member_level, r.created_at
        FROM business_customer_tag_relations r
        JOIN business_members m ON r.customer_user_id = m.user_id
        WHERE r.staff_id=%s
        ORDER BY r.created_at DESC
        LIMIT 10
    """, [staff_id]) or []
    
    return jsonify({'success': True, 'data': {
        'total_customers': total_customers,
        'tag_stats': tag_stats,
        'recent_customers': recent_customers
    }})

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
        return jsonify({
            'success': True,
            'data': {
                'status': 'degraded',
                'message': f'健康检查异常: {str(e)}'
            }
        })

# ============ 通知功能 ============

@app.route('/api/staff/notifications', methods=['GET'])
@require_staff
def staff_get_notifications(user):
    """获取员工通知列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    is_read = request.args.get('is_read')
    
    where = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    if is_read is not None and is_read != '':
        read_val = 1 if is_read in ('true', '1') else 0
        where += " AND is_read=%s"; params.append(read_val)
    
    try:
        total = db.get_total("SELECT COUNT(*) FROM business_notifications WHERE " + where, params)
        unread = db.get_total("SELECT COUNT(*) FROM business_notifications WHERE user_id=%s AND is_read=0 AND deleted=0", [user['user_id']])
        offset = (page - 1) * page_size
        items = db.get_all(
            "SELECT id, title, content, notify_type, is_read, created_at "
            "FROM business_notifications WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [], 'total': total, 'page': page, 'page_size': page_size,
            'unread_count': unread
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'unread_count': 0}})

@app.route('/api/staff/notifications/<nid>/read', methods=['POST'])
@require_staff
def staff_mark_read(user, nid):
    """标记通知已读"""
    try:
        notification.mark_as_read(nid, user['user_id'])
    return jsonify({'success': True, 'msg': '已读'})

@app.route('/api/staff/notifications/read-all', methods=['POST'])
@require_staff
def staff_mark_all_read(user):
    """全部标记已读"""
    try:
        notification.mark_all_as_read(user['user_id'])
    return jsonify({'success': True, 'msg': '全部已读'})

# ============ 反馈功能 ============

@app.route('/api/staff/feedback', methods=['GET'])
@require_staff
def staff_list_feedback(user):
    """员工查看反馈列表（本管辖范围内的）"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    feedback_type = request.args.get('feedback_type')

    where = "deleted=0"
    params = []
    if status:
        where += " AND status=%s"; params.append(status)
    if feedback_type:
        where += " AND feedback_type=%s"; params.append(feedback_type)
    # 数据隔离
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    try:
        total = db.get_total("SELECT COUNT(*) FROM business_feedback WHERE " + where, params)
        offset = (page - 1) * page_size
        items = db.get_all(
            "SELECT id, user_name, feedback_type, title, content, contact, status, reply, replied_at, created_at "
            "FROM business_feedback WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [], 'total': total, 'page': page, 'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}})

@app.route('/api/staff/feedback/<fb_id>/reply', methods=['POST'])
@require_staff
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def staff_reply_feedback(user, fb_id):
    """员工回复反馈"""
    data = request.get_json() or {}
    reply = data.get('reply', '').strip()
    if not reply:
        return jsonify({'success': False, 'msg': '回复内容不能为空'})
    try:
        db.execute(
            "UPDATE business_feedback SET reply=%s, replied_by=%s, replied_at=NOW(), status='replied' WHERE id=%s",
            [reply, user.get('user_name', ''), fb_id]
        )
        # 通知用户
        try:
            fb = db.get_one("SELECT user_id, title FROM business_feedback WHERE id=%s", [fb_id])
            if fb:
                notification.send_notification(
                    fb['user_id'], '您的意见反馈已回复',
                    f"关于「{fb['title']}」的反馈已回复：{reply[:100]}",
                    notify_type='system', ref_id=str(fb_id), ref_type='feedback'
                )
        return jsonify({'success': True, 'msg': '回复成功'})
        return jsonify({'success': False, 'msg': '回复失败'})

# ============ 预约核销 ============

@app.route('/api/staff/bookings', methods=['GET'])
@require_staff
def staff_list_bookings(user):
    """员工查看预约列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    venue_id = request.args.get('venue_id')

    where = "vb.deleted=0"
    params = []
    if status:
        where += " AND vb.status=%s"; params.append(status)
    if venue_id:
        where += " AND vb.venue_id=%s"; params.append(venue_id)
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    if ec_id:
        where += " AND vb.ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND vb.project_id=%s"; params.append(project_id)

    try:
        total = db.get_total("SELECT COUNT(*) FROM business_venue_bookings vb WHERE " + where, params)
        offset = (page - 1) * page_size
        items = db.get_all(
            "SELECT vb.id, vb.venue_id, vb.user_name, vb.user_phone, vb.book_date, "
            "CAST(vb.start_time AS CHAR) as start_time, CAST(vb.end_time AS CHAR) as end_time, "
            "vb.total_price, vb.status, vb.pay_status, vb.verify_code, vb.created_at, "
            "v.venue_name, v.venue_type "
            "FROM business_venue_bookings vb "
            "LEFT JOIN business_venues v ON vb.venue_id=v.id "
            "WHERE " + where + " ORDER BY vb.book_date DESC, vb.start_time ASC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [], 'total': total, 'page': page, 'page_size': page_size
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

@app.route('/api/staff/bookings/<booking_id>/complete', methods=['POST'])
@require_staff
def staff_complete_booking(user, booking_id):
    """员工完成预约（核销）- V17.0修复：添加完整数据隔离验证"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    # V17.0 P0修复：添加完整的数据隔离验证
    where = "id=%s AND deleted=0"
    params = [booking_id]
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)
    
    booking = db.get_one(
        "SELECT id, status, user_id FROM business_venue_bookings WHERE " + where, params
    )
    if not booking:
        return jsonify({'success': False, 'msg': '预约不存在或无权操作'})
    if booking.get('status') != 'confirmed':
        return jsonify({'success': False, 'msg': '只有已确认的预约才能完成核销'})
    
    # V17.0：添加审计日志
    try:
        from business_common.audit_log import audit_log
        audit_log.log_action(
            user['user_id'], user.get('user_name', ''),
            'complete_booking', f'核销预约ID:{booking_id}',
            ref_type='booking', ref_id=str(booking_id)
        )
    
    db.execute(
        "UPDATE business_venue_bookings SET status='completed', updated_at=NOW() WHERE id=%s",
        [booking_id]
    )
    
    # 发送核销成功通知
    try:
        notification.send_notification(
            booking.get('user_id', ''), '预约已核销',
            f"您的场地预约已完成核销，感谢使用！",
            notify_type='booking', ref_id=str(booking_id), ref_type='booking'
        )
    
    return jsonify({'success': True, 'msg': '核销成功'})

@app.route('/api/staff/bookings/verify', methods=['POST'])
@require_staff
@rate_limiter.rate_limit(limit=30, window_seconds=60)
def staff_verify_booking(user):
    """核销码验证"""
    data = request.get_json() or {}
    verify_code = (data.get('verify_code') or '').strip().upper()
    if not verify_code:
        return jsonify({'success': False, 'msg': '请输入核销码'})
    
    where = "verify_code=%s AND deleted=0"
    params = [verify_code]
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)
    
    booking = db.get_one(
        "SELECT vb.*, v.venue_name FROM business_venue_bookings vb "
        "LEFT JOIN business_venues v ON vb.venue_id=v.id "
        "WHERE vb." + where, params
    )
    if not booking:
        return jsonify({'success': False, 'msg': '核销码无效'})
    if booking.get('status') == 'completed':
        return jsonify({'success': False, 'msg': '该预约已核销'})
    if booking.get('status') == 'cancelled':
        return jsonify({'success': False, 'msg': '该预约已取消'})
    if booking.get('status') == 'pending':
        return jsonify({'success': False, 'msg': '该预约尚未确认，无法核销'})
    
    db.execute("UPDATE business_venue_bookings SET status='completed', updated_at=NOW() WHERE id=%s", [booking['id']])
    return jsonify({'success': True, 'msg': '核销成功', 'data': booking})

# ============ V11.0 员工端新增功能 ============

@app.route('/api/staff/orders/<order_id>/ship', methods=['POST'])
@require_staff
@rate_limiter.rate_limit(limit=20, window_seconds=60)
def staff_ship_order(user, order_id):
    """员工端订单发货"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    data = request.get_json() or {}
    tracking_no = (data.get('tracking_no') or '').strip()
    logistics_company = (data.get('logistics_company') or '').strip()

    where = "id=%s AND deleted=0"
    params = [order_id]
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    order = db.get_one("SELECT * FROM business_orders WHERE " + where, params)
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在或无权操作'})
    if order.get('order_status') != 'paid':
        return jsonify({'success': False, 'msg': '只有已支付订单可以发货'})

    try:
        db.execute(
            """UPDATE business_orders SET order_status='shipped', tracking_no=%s,
               logistics_company=%s, shipped_at=NOW(), updated_at=NOW() WHERE id=%s""",
            [tracking_no, logistics_company, order_id]
        )
        # 发送用户通知
        try:
            notification.send_notification(
                order.get('user_id', ''), '您的订单已发货',
                f"订单 {order.get('order_no','')} 已发货，物流：{logistics_company or '未填写'} 单号：{tracking_no or '未填写'}",
                notify_type='order', ref_id=str(order_id), ref_type='order'
            )
        return jsonify({'success': True, 'msg': '发货成功'})
        return jsonify({'success': False, 'msg': '发货失败'})

@app.route('/api/staff/orders/<order_id>/refund', methods=['POST'])
@require_staff
@rate_limiter.rate_limit(limit=20, window_seconds=60)
def staff_process_refund(user, order_id):
    """员工端处理退款申请（批准/拒绝）"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    data = request.get_json() or {}
    action = data.get('action')  # 'approve' or 'reject'
    remark = (data.get('remark') or '').strip()

    if action not in ('approve', 'reject'):
        return jsonify({'success': False, 'msg': '无效操作，必须为approve或reject'})

    where = "id=%s AND deleted=0 AND order_status='refunding'"
    params = [order_id]
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    order = db.get_one("SELECT * FROM business_orders WHERE " + where, params)
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在或状态不是退款中'})

    # V15安全校验：退款金额不能超过实付金额
    actual_amount = float(order.get('actual_amount') or 0)

    try:
        conn = db.get_db()
        cursor = conn.cursor()
        conn.begin()

        if action == 'approve':
            cursor.execute(
                "UPDATE business_orders SET order_status='refunded', pay_status='refunded', refunded_at=NOW(), updated_at=NOW() WHERE id=%s",
                [order_id]
            )
            msg = '退款已批准'
            notify_msg = f"订单 {order.get('order_no','')} 退款申请已批准，款项将退回原支付方式"

            # V23.0: 退款时回收该订单产生的积分
            try:
                points_earned = cursor.execute(
                    """SELECT COALESCE(SUM(points), 0) as earned
                       FROM business_points_log
                       WHERE ref_id=%s AND ref_type='payment' AND log_type='earn' AND points > 0""",
                    [str(order_id)]
                )
                row = cursor.fetchone()
                if row and row[0] and row[0] > 0:
                    earned = int(row[0])
                    user_id_refund = order.get('user_id')
                    cursor.execute(
                        "UPDATE business_members SET points=GREATEST(0, points-%s) WHERE user_id=%s",
                        [earned, user_id_refund]
                    )
                    cursor.execute(
                        """INSERT INTO business_points_log
                           (user_id, user_name, log_type, points, balance_after, description, ref_id, ref_type, ec_id, project_id)
                           SELECT %s, %s, 'refund_deduct', -%s, points, %s, %s, 'refund', %s, %s
                           FROM business_members WHERE user_id=%s""",
                        [user_id_refund, order.get('user_name', ''), earned,
                         f'订单退款积分回收', str(order_id),
                         ec_id, project_id, user_id_refund]
                    )
        else:
            # 拒绝退款，回滚状态到 paid
            cursor.execute(
                "UPDATE business_orders SET order_status='paid', refund_reason=NULL, updated_at=NOW() WHERE id=%s",
                [order_id]
            )
            # 重新扣减库存（用户申请退款时已回滚库存，拒绝后需重新扣减，sales_count保持不变）
            items = db.get_all("SELECT product_id, quantity FROM business_order_items WHERE order_id=%s", [order_id])
            if items:
                for item in items:
                    cursor.execute(
                        "UPDATE business_products SET stock=GREATEST(0, stock-%s) WHERE id=%s",
                        [item['quantity'], item['product_id']]
                    )
            msg = '退款已拒绝'
            notify_msg = f"订单 {order.get('order_no','')} 退款申请被拒绝" + (f"：{remark}" if remark else "")

        conn.commit()

        # 发送通知给用户
        try:
            notification.send_notification(
                order.get('user_id', ''), f'退款{"批准" if action == "approve" else "拒绝"}通知',
                notify_msg,
                notify_type='order', ref_id=str(order_id), ref_type='order'
            )

        return jsonify({'success': True, 'msg': msg})
    except Exception as e:
        try:
            conn.rollback()
        logging.error(f"处理退款失败: {e}")
        return jsonify({'success': False, 'msg': '操作失败，请稍后重试'})
    finally:
        try:
            cursor.close()
            conn.close()

@app.route('/api/staff/orders/<order_id>/complete', methods=['POST'])
@require_staff
def staff_complete_order(user, order_id):
    """员工端确认完成订单"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    where = "id=%s AND deleted=0"
    params = [order_id]
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    order = db.get_one("SELECT * FROM business_orders WHERE " + where, params)
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    if order.get('order_status') not in ('shipped', 'paid'):
        return jsonify({'success': False, 'msg': '当前状态不可完成'})

    try:
        db.execute(
            "UPDATE business_orders SET order_status='completed', completed_at=NOW(), updated_at=NOW() WHERE id=%s",
            [order_id]
        )
        return jsonify({'success': True, 'msg': '订单已完成'})
        return jsonify({'success': False, 'msg': '操作失败'})

@app.route('/api/staff/members', methods=['GET'])
@require_staff
def staff_list_members(user):
    """员工端会员列表查询"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    keyword = request.args.get('keyword', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)

    where = "1=1"
    params = []
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)
    if keyword:
        where += " AND (user_name LIKE %s OR phone LIKE %s)"
        kw = f'%{keyword}%'
        params.extend([kw, kw])

    try:
        total = db.get_total("SELECT COUNT(*) FROM business_members WHERE " + where, params)
        offset = (page - 1) * page_size
        items = db.get_all(
            "SELECT user_id, user_name, phone, member_level, points, total_points, balance, created_at "
            "FROM business_members WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {'items': items or [], 'total': total, 'page': page, 'page_size': page_size}})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

@app.route('/api/staff/checkin/stats', methods=['GET'])
@require_staff
def staff_checkin_stats(user):
    """员工端签到统计（今日/本周/本月签到人数）"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    today = time.strftime('%Y-%m-%d')
    week_ago = time.strftime('%Y-%m-%d', time.localtime(time.time() - 7 * 86400))
    month_start = today[:8] + '01'

    # 需要通过members关联取到当前项目的用户
    member_where = "1=1"
    member_params = []
    if ec_id:
        member_where += " AND ec_id=%s"; member_params.append(ec_id)
    if project_id:
        member_where += " AND project_id=%s"; member_params.append(project_id)

    try:
        today_count = db.get_total(
            f"SELECT COUNT(*) FROM business_checkin_logs cl "
            f"INNER JOIN business_members m ON cl.user_id=m.user_id "
            f"WHERE {member_where.replace('1=1 AND', '').replace('1=1', 'm.user_id IS NOT NULL')} AND cl.checkin_date=%s",
            member_params + [today]
        )
        week_count = db.get_total(
            f"SELECT COUNT(DISTINCT cl.user_id) FROM business_checkin_logs cl "
            f"INNER JOIN business_members m ON cl.user_id=m.user_id "
            f"WHERE cl.checkin_date BETWEEN %s AND %s",
            [week_ago, today]
        )
        month_count = db.get_total(
            f"SELECT COUNT(DISTINCT cl.user_id) FROM business_checkin_logs cl "
            f"INNER JOIN business_members m ON cl.user_id=m.user_id "
            f"WHERE cl.checkin_date BETWEEN %s AND %s",
            [month_start, today]
        )
        # 本月签到次数Top5
        top_users = db.get_all(
            """SELECT m.user_name, m.phone, COUNT(cl.id) as checkin_count, MAX(cl.continuous_days) as max_continuous
               FROM business_checkin_logs cl
               INNER JOIN business_members m ON cl.user_id=m.user_id
               WHERE cl.checkin_date BETWEEN %s AND %s
               GROUP BY cl.user_id ORDER BY checkin_count DESC LIMIT 5""",
            [month_start, today]
        )
        return jsonify({'success': True, 'data': {
            'today_count': today_count,
            'week_active_users': week_count,
            'month_active_users': month_count,
            'top_users': top_users or []
        }})
        return jsonify({'success': True, 'data': {'today_count': 0, 'week_active_users': 0, 'month_active_users': 0, 'top_users': []}})

@app.route('/api/staff/orders/pending-refunds', methods=['GET'])
@require_staff
def staff_pending_refunds(user):
    """待处理退款"""
    from business_common.statistics_service import get_stats_service
    result = get_stats_service().staff_pending_refunds(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': result})


@app.route('/api/staff/audit-logs', methods=['GET'])
@require_staff
def staff_audit_logs(user):
    """V17.0新增：操作日志查询"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 100)
    
    # 筛选参数
    action = request.args.get('action', '').strip()
    keyword = request.args.get('keyword', '').strip()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    result = []
    total = 0
    
    try:
        from business_common.audit_log import get_audit_logs
        
        logs = get_audit_logs(
            ec_id=ec_id,
            project_id=project_id,
            action=action if action else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
            page=page,
            page_size=page_size
        )
        result = logs.get('items', [])
        total = logs.get('total', 0)
        
        # 关键词过滤（内存过滤）
        if keyword and result:
            result = [
                log for log in result
                if keyword.lower() in str(log.get('action', '')).lower()
                or keyword.lower() in str(log.get('user_name', '')).lower()
                or keyword.lower() in str(log.get('details', '')).lower()
            ]
    return jsonify({'success': True, 'data': {
        'items': result,
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/staff/audit-logs/actions', methods=['GET'])
@require_staff
def staff_audit_action_stats(user):
    """V17.0新增：操作类型统计"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    try:
        where = "1=1"
        params = []
        if ec_id:
            where += " AND ec_id=%s"; params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"; params.append(project_id)
        if date_from:
            where += " AND DATE(created_at)>=%s"; params.append(date_from)
        if date_to:
            where += " AND DATE(created_at)<=%s"; params.append(date_to)
        
        stats = db.get_all(
            f"""SELECT action, COUNT(*) as cnt 
                FROM system_audit_log WHERE {where}
                GROUP BY action ORDER BY cnt DESC LIMIT 20""",
            params
        )
        return jsonify({'success': True, 'data': {'items': stats or []}})
        return jsonify({'success': True, 'data': {'items': []}})

@app.route('/api/staff/statistics/dashboard', methods=['GET'])
@require_staff
def staff_dashboard_stats(user):
    """员工端仪表盘统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().staff_dashboard_stats(
        user.get('user_id'), user.get('ec_id'), user.get('project_id')
    )
    return jsonify({'success': True, 'data': stats})


@app.route('/api/staff/products', methods=['GET'])
@require_staff
def staff_list_products(user):
    """员工端商品列表（查看库存和状态）- V18.0增强：支持状态筛选"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    keyword = request.args.get('keyword', '').strip()
    status_filter = request.args.get('status', '')  # V18: active/inactive/low_stock/out_of_stock
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)

    where = "deleted=0"
    params = []
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)
    if keyword:
        where += " AND product_name LIKE %s"
        params.append(f'%{keyword}%')
    # V18: 状态筛选
    if status_filter == 'active':
        where += " AND status='active'"
    elif status_filter == 'inactive':
        where += " AND status='inactive'"
    elif status_filter == 'low_stock':
        where += " AND stock > 0 AND stock <= 10"
    elif status_filter == 'out_of_stock':
        where += " AND stock = 0"

    try:
        total = db.get_total("SELECT COUNT(*) FROM business_products WHERE " + where, params)
        offset = (page - 1) * page_size
        items = db.get_all(
            "SELECT id, product_name, category, price, original_price, stock, sales_count, status, image, created_at "
            "FROM business_products WHERE " + where + " ORDER BY stock ASC, created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        # V18: 统计各状态数量
        low_stock_count = db.get_total(
            "SELECT COUNT(*) FROM business_products WHERE deleted=0 AND stock > 0 AND stock <= 10" +
            (" AND ec_id=%s" if ec_id else "") + (" AND project_id=%s" if project_id else ""),
            ([ec_id] if ec_id else []) + ([project_id] if project_id else [])
        )
        out_of_stock_count = db.get_total(
            "SELECT COUNT(*) FROM business_products WHERE deleted=0 AND stock = 0" +
            (" AND ec_id=%s" if ec_id else "") + (" AND project_id=%s" if project_id else ""),
            ([ec_id] if ec_id else []) + ([project_id] if project_id else [])
        )
        return jsonify({'success': True, 'data': {
            'items': items or [], 'total': total, 'page': page, 'page_size': page_size,
            'low_stock_count': low_stock_count, 'out_of_stock_count': out_of_stock_count
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

@app.route('/api/staff/products/<int:product_id>/stock', methods=['POST'])
@require_staff
def staff_adjust_stock(user, product_id):
    """V18.0新增：员工端商品库存调整"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    data = request.get_json() or {}

    adjust_type = data.get('adjust_type')  # add / subtract / set
    quantity = data.get('quantity')
    reason = data.get('reason', '').strip()

    if adjust_type not in ('add', 'subtract', 'set'):
        return jsonify({'success': False, 'msg': '操作类型无效，仅支持 add/subtract/set'})
    if quantity is None or not isinstance(quantity, (int, float)) or int(quantity) < 0:
        return jsonify({'success': False, 'msg': '数量参数无效'})
    quantity = int(quantity)

    # 校验商品归属
    product = db.get_one(
        "SELECT id, product_name, stock FROM business_products WHERE id=%s AND deleted=0" +
        (" AND ec_id=%s" if ec_id else "") + (" AND project_id=%s" if project_id else ""),
        [product_id] + ([ec_id] if ec_id else []) + ([project_id] if project_id else [])
    )
    if not product:
        return jsonify({'success': False, 'msg': '商品不存在'})

    old_stock = int(product['stock'] or 0)

    if adjust_type == 'add':
        new_stock = old_stock + quantity
    elif adjust_type == 'subtract':
        new_stock = max(0, old_stock - quantity)
    else:  # set
        new_stock = quantity

    try:
        db.execute(
            "UPDATE business_products SET stock=%s, updated_at=NOW() WHERE id=%s",
            [new_stock, product_id]
        )
        # 写入操作日志
        try:
            from business_common import audit_log
            audit_log.log_action(
                user_id=user.get('user_id'),
                user_name=user.get('user_name', ''),
                action='adjust_stock',
                details=f"商品[{product['product_name']}] 库存调整: {old_stock} -> {new_stock} ({adjust_type} {quantity}) 原因: {reason}",
                ip=request.remote_addr,
                ec_id=ec_id,
                project_id=project_id
            )
        except Exception:
            pass
        logging.info(f"库存调整: product={product_id}, {old_stock} -> {new_stock}, staff={user.get('user_id')}")
        return jsonify({'success': True, 'msg': '库存调整成功', 'data': {'old_stock': old_stock, 'new_stock': new_stock}})
        return jsonify({'success': False, 'msg': '库存调整失败'})

@app.route('/api/staff/products/<int:product_id>/status', methods=['POST'])
@require_staff
def staff_toggle_product_status(user, product_id):
    """V18.0新增：员工端切换商品上/下架状态"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    data = request.get_json() or {}
    new_status = data.get('status')

    if new_status not in ('active', 'inactive'):
        return jsonify({'success': False, 'msg': '状态值无效'})

    product = db.get_one(
        "SELECT id, product_name, status FROM business_products WHERE id=%s AND deleted=0" +
        (" AND ec_id=%s" if ec_id else "") + (" AND project_id=%s" if project_id else ""),
        [product_id] + ([ec_id] if ec_id else []) + ([project_id] if project_id else [])
    )
    if not product:
        return jsonify({'success': False, 'msg': '商品不存在'})

    try:
        db.execute(
            "UPDATE business_products SET status=%s, updated_at=NOW() WHERE id=%s",
            [new_status, product_id]
        )
        try:
            from business_common import audit_log
            audit_log.log_action(
                user_id=user.get('user_id'),
                user_name=user.get('user_name', ''),
                action='toggle_product_status',
                details=f"商品[{product['product_name']}] 状态: {product['status']} -> {new_status}",
                ip=request.remote_addr,
                ec_id=ec_id,
                project_id=project_id
            )
        except Exception:
            pass
        return jsonify({'success': True, 'msg': f"商品已{'上架' if new_status == 'active' else '下架'}"})
        return jsonify({'success': False, 'msg': '操作失败'})

@app.route('/api/staff/applications/overdue', methods=['GET'])
@require_staff
def get_overdue_applications(staff):
    """V19.0: 获取超时申请单统计"""
    from business_common.application_monitor import get_overdue_statistics
    
    ec_id = staff.get('ec_id')
    project_id = staff.get('project_id')
    
    stats = get_overdue_statistics(ec_id=ec_id, project_id=project_id)
    return jsonify({'success': True, 'data': stats})

@app.route('/api/staff/applications/<app_id>/timeline', methods=['GET'])
@require_staff
def get_application_timeline(staff, app_id):
    """V19.0: 获取申请单处理时间线"""
    from business_common.application_monitor import get_application_timeline as get_timeline
    
    timeline = get_timeline(app_id)
    if not timeline:
        return jsonify({'success': False, 'msg': '申请单不存在'})
    
    return jsonify({'success': True, 'data': timeline})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# ============ 评价管理 V21.0新增 ============

@app.route('/api/staff/reviews', methods=['GET'])
@require_staff
def staff_list_reviews(user):
    """员工端评价列表"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    keyword = request.args.get('keyword', '').strip()
    rating = request.args.get('rating', '')  # 1-5星
    target_type = request.args.get('target_type', '')  # order/shop/product/venue
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    where = "deleted=0"
    params = []
    
    if ec_id:
        where += " AND (ec_id=%s OR ec_id IS NULL)"
        params.append(ec_id)
    if project_id:
        where += " AND (project_id=%s OR project_id IS NULL)"
        params.append(project_id)
    if keyword:
        where += " AND (user_name LIKE %s OR content LIKE %s)"
        kw = f'%{keyword}%'
        params.extend([kw, kw])
    if rating:
        where += " AND rating=%s"
        params.append(int(rating))
    if target_type:
        where += " AND target_type=%s"
        params.append(target_type)
    
    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_reviews WHERE {where}", params)
        offset = (page - 1) * page_size
        items = db.get_all(f"""
            SELECT r.*,
                   CASE r.target_type
                       WHEN 'order' THEN (SELECT order_no FROM business_orders WHERE id=r.target_id)
                       WHEN 'shop' THEN (SELECT shop_name FROM business_shops WHERE id=r.target_id)
                       WHEN 'product' THEN (SELECT product_name FROM business_products WHERE id=r.target_id)
                       WHEN 'venue' THEN (SELECT venue_name FROM business_venues WHERE id=r.target_id)
                       ELSE '未知'
                   END as target_name
            FROM business_reviews r
            WHERE {where}
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

@app.route('/api/staff/reviews/<int:review_id>/reply', methods=['POST'])
@require_staff
def staff_reply_review(user, review_id):
    """员工端回复评价"""
    data = request.get_json() or {}
    reply_content = (data.get('reply_content') or '').strip()
    
    if not reply_content:
        return jsonify({'success': False, 'msg': '请输入回复内容'})
    
    if len(reply_content) > 300:
        return jsonify({'success': False, 'msg': '回复内容不能超过300字'})
    
    try:
        review = db.get_one(
            "SELECT * FROM business_reviews WHERE id=%s AND deleted=0",
            [review_id]
        )
        if not review:
            return jsonify({'success': False, 'msg': '评价不存在'})
        
        db.execute("""
            UPDATE business_reviews
            SET reply_content=%s, replied_at=NOW(), reply_user_id=%s, reply_user_name=%s
            WHERE id=%s
        """, [reply_content, user.get('user_id'), user.get('user_name'), review_id])
        
        # 发送通知给用户
        from business_common.notification import send_notification
        send_notification(
            user_id=review.get('user_id'),
            title='您的评价已收到回复',
            content=f"商家已回复您的评价: {reply_content[:50]}...",
            notify_type='review_reply',
            ec_id=review.get('ec_id'),
            project_id=review.get('project_id')
        )
        
        return jsonify({'success': True, 'msg': '回复成功'})
        return jsonify({'success': False, 'msg': '回复失败'})

@app.route('/api/staff/reviews/statistics', methods=['GET'])
@require_staff
def staff_review_statistics(user):
    """员工端评价统计"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    where = "deleted=0"
    params = []
    if ec_id:
        where += " AND (ec_id=%s OR ec_id IS NULL)"
        params.append(ec_id)
    if project_id:
        where += " AND (project_id=%s OR project_id IS NULL)"
        params.append(project_id)
    
    try:
        # 总体统计
        total = db.get_total(f"SELECT COUNT(*) FROM business_reviews WHERE {where}", params)
        avg_rating_row = db.get_one(f"SELECT AVG(rating) as avg FROM business_reviews WHERE {where}", params)
        avg_rating = round(float(avg_rating_row.get('avg') or 0), 1)
        
        # 评分分布
        rating_dist = db.get_all(f"""
            SELECT rating, COUNT(*) as count
            FROM business_reviews WHERE {where}
            GROUP BY rating
            ORDER BY rating DESC
        """, params) or []
        
        # 类型分布
        type_dist = db.get_all(f"""
            SELECT target_type, COUNT(*) as count
            FROM business_reviews WHERE {where}
            GROUP BY target_type
        """, params) or []
        
        # 今日新增
        today_count = db.get_total(
            f"SELECT COUNT(*) FROM business_reviews WHERE {where} AND DATE(created_at)=CURDATE()",
            params
        )
        
        # 待回复
        unreplied = db.get_total(
            f"SELECT COUNT(*) FROM business_reviews WHERE {where} AND (reply_content IS NULL OR reply_content='')",
            params
        )
        
        return jsonify({'success': True, 'data': {
            'total_reviews': total,
            'avg_rating': avg_rating,
            'rating_distribution': {str(r['rating']): r['count'] for r in rating_dist},
            'type_distribution': {r['target_type']: r['count'] for r in type_dist},
            'today_new': today_count,
            'unreplied': unreplied
        }})
        return jsonify({'success': False, 'msg': '统计失败'})

@app.route('/api/staff/reviews/<int:review_id>', methods=['DELETE'])
@require_staff
def staff_delete_review(user, review_id):
    """员工端删除评价"""
    try:
        review = db.get_one(
            "SELECT * FROM business_reviews WHERE id=%s AND deleted=0",
            [review_id]
        )
        if not review:
            return jsonify({'success': False, 'msg': '评价不存在'})
        
        db.execute("UPDATE business_reviews SET deleted=1 WHERE id=%s", [review_id])
        
        return jsonify({'success': True, 'msg': '评价已删除'})
        return jsonify({'success': False, 'msg': '删除失败'})

# ============ V28.0 批量操作接口 ============

@app.route('/api/staff/batch/ship', methods=['POST'])
@require_staff
@rate_limiter.rate_limit(limit=5, window_seconds=60)
def staff_batch_ship_orders(user):
    """V28.0: 批量订单发货"""
    from business_common.batch_operation_service import BatchOperationService
    data = request.get_json() or {}
    order_ids = data.get('order_ids', [])
    logistics_company = (data.get('logistics_company') or '').strip()

    if not order_ids:
        return jsonify({'success': False, 'msg': '请选择要发货的订单'})
    if len(order_ids) > 50:
        return jsonify({'success': False, 'msg': '每次最多处理50个订单'})

    result = BatchOperationService.batch_ship_orders(
        operator_id=user.get('user_id'),
        operator_name=user.get('user_name', ''),
        order_ids=order_ids,
        logistics_company=logistics_company,
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/staff/batch/applications', methods=['POST'])
@require_staff
@rate_limiter.rate_limit(limit=5, window_seconds=60)
def staff_batch_process_applications(user):
    """V28.0: 批量处理申请单"""
    from business_common.batch_operation_service import BatchOperationService
    data = request.get_json() or {}
    app_ids = data.get('app_ids', [])
    action = data.get('action', '')

    if not app_ids:
        return jsonify({'success': False, 'msg': '请选择要处理的申请单'})
    if len(app_ids) > 50:
        return jsonify({'success': False, 'msg': '每次最多处理50个申请单'})

    result = BatchOperationService.batch_process_applications(
        operator_id=user.get('user_id'),
        operator_name=user.get('user_name', ''),
        app_ids=app_ids,
        action=action,
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/staff/batch/logs', methods=['GET'])
@require_staff
def staff_batch_operation_logs(user):
    """V28.0: 获取批量操作日志"""
    from business_common.batch_operation_service import BatchOperationService
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 50)

    result = BatchOperationService.get_batch_operation_logs(
        operator_id=user.get('user_id'),
        page=page,
        page_size=page_size,
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    )
    return jsonify({'success': True, 'data': result})

# ============ V28.0 打印服务接口 ============

@app.route('/api/staff/print/logistics-companies', methods=['GET'])
@require_staff
def get_logistics_companies(user):
    """V28.0: 获取物流公司列表"""
    from business_common.print_service import PrintService
    companies = PrintService.get_logistics_companies()
    return jsonify({'success': True, 'data': companies})

@app.route('/api/staff/print/express/<int:order_id>', methods=['GET'])
@require_staff
def generate_express_print(user, order_id):
    """V28.0: 生成快递单打印数据"""
    from business_common.print_service import PrintService
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    where = "id=%s AND deleted=0"
    params = [order_id]
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    order = db.get_one(f"SELECT * FROM business_orders WHERE {where}", params)
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})

    express_data = PrintService.generate_express_template(order)
    return jsonify({'success': True, 'data': express_data})

@app.route('/api/staff/print/picking/<int:order_id>', methods=['GET'])
@require_staff
def generate_picking_print(user, order_id):
    """V28.0: 生成配货单打印数据"""
    from business_common.print_service import PrintService
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    where = "id=%s AND deleted=0"
    params = [order_id]
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    order = db.get_one(f"SELECT * FROM business_orders WHERE {where}", params)
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})

    picking_data = PrintService.generate_picking_template(order)
    return jsonify({'success': True, 'data': picking_data})

@app.route('/api/staff/print/log', methods=['POST'])
@require_staff
def record_print_log(user):
    """V28.0: 记录打印日志"""
    from business_common.print_service import PrintService
    data = request.get_json() or {}
    order_id = data.get('order_id')
    order_no = data.get('order_no', '')
    print_type = data.get('print_type', 'express')
    print_content = data.get('print_content', {})

    if not order_id:
        return jsonify({'success': False, 'msg': '订单ID不能为空'})

    print_id = PrintService.log_print(
        order_id=order_id,
        order_no=order_no,
        print_type=print_type,
        print_content=print_content,
        operator_id=user.get('user_id'),
        operator_name=user.get('user_name', ''),
        ip_address=request.remote_addr
    )
    return jsonify({'success': True, 'msg': '打印记录已保存', 'data': {'print_id': print_id}})

@app.route('/api/staff/print/history/<int:order_id>', methods=['GET'])
@require_staff
def get_print_history(user, order_id):
    """V28.0: 获取订单打印历史"""
    from business_common.print_service import PrintService
    limit = min(max(1, int(request.args.get('limit', 10))), 50)
    history = PrintService.get_print_history(order_id, limit)
    return jsonify({'success': True, 'data': history})

# ============ V29.0 申请审批系统 (员工端/管家端) ============

@app.route('/api/staff/applications/v2/pending', methods=['GET'])
@require_staff
def get_pending_applications_v2(user):
    """V29.0: 获取待审批申请列表"""
    from business_common.application_service import ApplicationService
    
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    result = ApplicationService.get_pending_applications(
        approver_id=user.get('user_id'),
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id'),
        page=page,
        page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

@app.route('/api/staff/applications/v2/all', methods=['GET'])
@require_staff
def get_all_applications_v2(user):
    """V29.0: 获取所有申请列表（带筛选）"""
    from business_common.application_service import ApplicationService
    
    type_code = request.args.get('type_code')
    status = request.args.get('status')
    keyword = request.args.get('keyword', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    where = "1=1"
    params = []
    
    if user.get('ec_id'):
        where += " AND ec_id=%s"
        params.append(user.get('ec_id'))
    if user.get('project_id'):
        where += " AND project_id=%s"
        params.append(user.get('project_id'))
    if type_code:
        where += " AND app_type=%s"
        params.append(type_code)
    if status:
        where += " AND status=%s"
        params.append(status)
    if keyword:
        where += " AND (title LIKE %s OR user_name LIKE %s OR app_no LIKE %s)"
        like_key = f"%{keyword}%"
        params.extend([like_key, like_key, like_key])
    
    total = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {where} AND deleted=0", params)
    offset = (page - 1) * page_size
    
    items = db.get_all(
        f"""SELECT id, app_no, app_type, title, user_name, user_phone, status,
                  current_step, total_steps, form_data, created_at, updated_at
           FROM business_applications
           WHERE {where} AND deleted=0
           ORDER BY 
             CASE status 
               WHEN 'pending' THEN 1 
               WHEN 'processing' THEN 2 
               ELSE 3 
             END,
             created_at DESC
           LIMIT %s OFFSET %s""",
        params + [page_size, offset]
    )
    
    # 获取类型名称
    type_names = {}
    types = ApplicationService.get_application_types()
    for t in types:
        type_names[t['type_code']] = {'name': t['type_name'], 'icon': t['icon']}
    
    for item in items or []:
        type_info = type_names.get(item.get('app_type'), {})
        item['type_name'] = type_info.get('name', item.get('app_type'))
        item['type_icon'] = type_info.get('icon', '')
        if item.get('form_data'):
            try:
                item['form_data'] = json.loads(item['form_data'])
            except:
                item['form_data'] = {}
    
    return jsonify({'success': True, 'data': {
        'items': items or [],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/staff/applications/v2/<int:app_id>', methods=['GET'])
@require_staff
def get_application_detail_staff_v2(user, app_id):
    """V29.0: 员工获取申请详情"""
    from business_common.application_service import ApplicationService
    
    app = ApplicationService.get_application_detail(
        app_id=app_id,
        is_staff=True
    )
    
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    
    # 验证数据权限
    if app.get('ec_id') and app.get('ec_id') != user.get('ec_id'):
        return jsonify({'success': False, 'msg': '无权查看该申请'})
    
    return jsonify({'success': True, 'data': app})

@app.route('/api/staff/applications/v2/<int:app_id>/approve', methods=['POST'])
@require_staff
@rate_limiter.rate_limit(limit=30, window_seconds=60)
def approve_application_v2(user, app_id):
    """V29.0: 审批申请"""
    from business_common.application_service import ApplicationService
    
    data = request.get_json() or {}
    action = data.get('action')  # approve, reject, transfer
    remark = data.get('remark', '').strip()
    transfer_to = data.get('transfer_to')
    
    if action not in ['approve', 'reject', 'transfer']:
        return jsonify({'success': False, 'msg': '无效的操作类型'})
    
    if action == 'transfer' and not transfer_to:
        return jsonify({'success': False, 'msg': '请选择转交人'})
    
    result = ApplicationService.approve_application(
        app_id=app_id,
        approver_id=user.get('user_id'),
        approver_name=user.get('user_name', ''),
        action=action,
        remark=remark,
        transfer_to=transfer_to
    )
    return jsonify(result)

@app.route('/api/staff/applications/v2/stats', methods=['GET'])
@require_staff
def get_application_stats_v2(user):
    """V29.0: 获取申请统计"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    where = "deleted=0"
    params = []
    if ec_id:
        where += " AND ec_id=%s"
        params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"
        params.append(project_id)
    
    # 待审批数量
    pending_count = db.get_total(
        f"SELECT COUNT(*) FROM business_applications WHERE {where} AND status IN ('pending', 'processing')",
        params.copy()
    )
    
    # 今日提交数量
    today_count = db.get_total(
        f"SELECT COUNT(*) FROM business_applications WHERE {where} AND DATE(created_at)=CURDATE()",
        params.copy()
    )
    
    # 各状态统计
    status_stats = db.get_all(
        f"""SELECT status, COUNT(*) as count 
            FROM business_applications 
            WHERE {where}
            GROUP BY status""",
        params.copy()
    ) or []
    
    # 各类型统计
    type_stats = db.get_all(
        f"""SELECT app_type, COUNT(*) as count 
            FROM business_applications 
            WHERE {where} AND DATE(created_at)=CURDATE()
            GROUP BY app_type""",
        params.copy()
    ) or []
    
    return jsonify({'success': True, 'data': {
        'pending_count': pending_count,
        'today_count': today_count,
        'status_stats': status_stats,
        'type_stats': type_stats
    }})

@app.route('/api/staff/applications/v2/types', methods=['GET'])
@require_staff
def get_application_types_staff_v2(user):
    """V29.0: 员工获取申请类型列表"""
    from business_common.application_service import ApplicationService
    
    types = ApplicationService.get_application_types()
    return jsonify({'success': True, 'data': {'items': types}})

@app.route('/api/staff/applications/v2/remind-expired', methods=['GET'])
@require_staff
def get_expired_applications_remind(user):
    """V29.0: 获取即将到期的申请（用于提醒）"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    where = "status IN ('approved', 'processing') AND expire_time IS NOT NULL AND expire_time > NOW()"
    params = []
    
    if ec_id:
        where += " AND ec_id=%s"
        params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"
        params.append(project_id)
    
    # 24小时内到期的
    items = db.get_all(
        f"""SELECT id, app_no, app_type, title, user_name, user_phone, 
                  expire_time, form_data
           FROM business_applications
           WHERE {where} AND expire_time <= DATE_ADD(NOW(), INTERVAL 24 HOUR)
           ORDER BY expire_time ASC
           LIMIT 50""",
        params
    ) or []
    
    # 获取类型名称
    type_map = {}
    types = db.get_all("SELECT type_code, type_name FROM business_application_types WHERE is_active=1")
    for t in types or []:
        type_map[t['type_code']] = t['type_name']
    
    for item in items:
        item['type_name'] = type_map.get(item.get('app_type'), item.get('app_type'))
        if item.get('form_data'):
            try:
                item['form_data'] = json.loads(item['form_data'])
            except:
                item['form_data'] = {}
    
    return jsonify({'success': True, 'data': {'items': items, 'total': len(items)}})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22312, debug=False)

# ============ V23.0 积分商城管理（员工端发货） ============

@app.route('/api/staff/points-exchanges', methods=['GET'])
@require_staff
def staff_get_points_exchanges(user):
    """员工端获取积分兑换列表"""
    from business_common.points_mall import PointsMallService
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 50)
    status = request.args.get('status')

    where = "e.deleted=0"
    params = []
    if ec_id:
        where += " AND e.ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND e.project_id=%s"; params.append(project_id)
    if status:
        where += " AND e.status=%s"; params.append(status)

    total = db.get_total(f"SELECT COUNT(*) FROM business_points_exchanges e WHERE {where}", params)
    offset = (page - 1) * page_size
    items = db.get_all(
        f"""SELECT e.id, e.exchange_no, e.user_id, e.user_name, e.goods_name, e.goods_image,
                  e.points_price, e.quantity, e.total_points, e.status,
                  e.address_snapshot, e.phone, e.tracking_no, e.logistics_company,
                  e.created_at, e.shipped_at
           FROM business_points_exchanges e
           WHERE {where} ORDER BY e.created_at DESC LIMIT %s OFFSET %s""",
        params + [page_size, offset]
    )

    # 统计待发货数量
    pending_count = db.get_total(
        f"SELECT COUNT(*) FROM business_points_exchanges e WHERE {where} AND e.status='paid'",
        [p for p in params]
    )

    return jsonify({'success': True, 'data': {
        'items': items or [],
        'total': total,
        'pending_count': pending_count,
        'page': page,
        'page_size': page_size
    }})

@app.route('/api/staff/points-exchanges/<exchange_id>/ship', methods=['POST'])
@require_staff
@rate_limiter.rate_limit(limit=20, window_seconds=60)
def staff_ship_points_exchange(user, exchange_id):
    """员工端积分兑换商品发货"""
    from business_common.points_mall import PointsMallService
    data = request.get_json() or {}
    tracking_no = (data.get('tracking_no') or '').strip()
    logistics_company = (data.get('logistics_company') or '').strip()

    if not tracking_no:
        return jsonify({'success': False, 'msg': '请填写物流单号'})

    result = PointsMallService.ship_exchange(
        exchange_id=exchange_id,
        tracking_no=tracking_no,
        logistics_company=logistics_company,
        admin_user=user
    )
    return jsonify(result)

# ============ 员工数据同步 ============

@app.route('/api/staff/employees/sync', methods=['POST'])
@require_staff
def sync_employees(user):
    """
    同步企业员工数据
    
    从第三方API获取企业所有员工信息并同步到本地表
    限制：一小时内只同步一次
    
    请求参数（从用户信息获取）:
    - ec_id: 企业ID
    - project_id: 项目ID
    - access_token: 访问令牌
    """
    if not employee_sync:
        return jsonify({'success': False, 'msg': '员工同步服务未初始化'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    if not ec_id:
        return jsonify({'success': False, 'msg': '缺少企业ID'})
    
    # 获取access_token
    access_token = request.args.get('access_token') or request.headers.get('Token')
    if not access_token:
        return jsonify({'success': False, 'msg': '缺少访问令牌'})
    
    # 执行同步
    result = employee_sync.sync_employees(access_token, ec_id, project_id)
    return jsonify(result)

@app.route('/api/staff/employees/sync-async', methods=['POST'])
@require_staff
def sync_employees_async(user):
    """
    异步同步企业员工数据
    
    立即返回，后台执行同步
    """
    if not employee_sync:
        return jsonify({'success': False, 'msg': '员工同步服务未初始化'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    if not ec_id:
        return jsonify({'success': False, 'msg': '缺少企业ID'})
    
    # 获取access_token
    access_token = request.args.get('access_token') or request.headers.get('Token')
    if not access_token:
        return jsonify({'success': False, 'msg': '缺少访问令牌'})
    
    # 异步执行同步
    employee_sync.sync_employees_async(access_token, ec_id, project_id)
    return jsonify({'success': True, 'msg': '同步任务已启动'})

@app.route('/api/staff/employees', methods=['GET'])
@require_staff
def get_employees(user):
    """
    获取员工列表
    
    查询参数:
    - keyword: 搜索关键词（姓名）
    - page: 页码
    - page_size: 每页数量
    """
    ec_id = user.get('ec_id')
    
    keyword = request.args.get('keyword', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(50, max(1, int(request.args.get('page_size', 20))))
    offset = (page - 1) * page_size
    
    where = "FECID = %s AND FStatus = 1 AND FIsDelete = 0"
    params = [ec_id]
    
    if keyword:
        where += " AND FName LIKE %s"
        params.append(f"%{keyword}%")
    
    # 查询总数
    total = db.get_total(f"SELECT COUNT(*) FROM t_pc_employee WHERE {where}", params.copy())
    
    # 查询列表
    employees = db.get_all(
        f"""
        SELECT FID, FName, FPhone, FEmail, FJobTitle, FUserUrl, FCreateTime, FUpdateTime
        FROM t_pc_employee 
        WHERE {where}
        ORDER BY FUpdateTime DESC
        LIMIT %s OFFSET %s
        """,
        params + [page_size, offset]
    ) or []
    
    return jsonify({
        'success': True,
        'data': {
            'items': employees,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    })

# 提供 business-common 静态文件支持
# 使用硬编码路径确保正确性
COMMON_STATIC_DIR = '/www/wwwroot/wojiayun/business-common'

@app.route('/business-common/<path:filename>')
def serve_common_static(filename):
    """提供上级目录 business-common 的静态文件"""
    return send_from_directory(COMMON_STATIC_DIR, filename)
