#!/usr/bin/env python3
"""Staff H5 Service - Fixed Version"""
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
from business_common import config, db, auth, utils

# 图片上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

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
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    scope = "deleted=0"
    p = []
    if ec_id:
        scope += " AND ec_id=%s"; p.append(ec_id)
    if project_id:
        scope += " AND project_id=%s"; p.append(project_id)

    pending = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {scope} AND status='pending'", p.copy())
    processing = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {scope} AND status='processing'", p.copy())
    completed_today = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {scope} AND status='completed' AND DATE(completed_at)=CURDATE()", p.copy())
    total_orders = db.get_total(f"SELECT COUNT(*) FROM business_orders WHERE {scope}", p.copy())
    return jsonify({'success': True, 'data': {'pending': pending, 'processing': processing, 'completed_today': completed_today, 'total_orders': total_orders, 'total_apps': pending+processing}})

@app.route('/api/staff/statistics', methods=['GET'])
@require_staff
def get_staff_statistics(user):
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    scope = "deleted=0"
    p = []
    if ec_id:
        scope += " AND ec_id=%s"; p.append(ec_id)
    if project_id:
        scope += " AND project_id=%s"; p.append(project_id)

    today_apps = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {scope} AND DATE(created_at)=CURDATE()", p.copy())
    pending_apps = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {scope} AND status='pending'", p.copy())
    processing_apps = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {scope} AND status='processing'", p.copy())

    today_orders = 0
    today_income = 0
    try:
        today_orders = db.get_total(f"SELECT COUNT(*) FROM business_orders WHERE {scope} AND DATE(created_at)=CURDATE()", p.copy())
        income_row = db.get_one(f"SELECT COALESCE(SUM(actual_amount),0) as income FROM business_orders WHERE {scope} AND order_status IN ('paid','completed') AND DATE(created_at)=CURDATE()", p.copy())
        if income_row:
            today_income = float(income_row.get('income') or 0)
    except Exception as e:
        logging.error('Error getting today orders/income: %s', e)

    app_stats = []
    try:
        app_stats = db.get_all(f"SELECT status, COUNT(*) as cnt FROM business_applications WHERE {scope} GROUP BY status ORDER BY cnt DESC", p.copy())
    except Exception as e:
        logging.error('Error getting app_stats: %s', e)

    order_stats = []
    try:
        order_stats = db.get_all(f"SELECT order_status as status, COUNT(*) as cnt FROM business_orders WHERE {scope} GROUP BY order_status ORDER BY cnt DESC", p.copy())
    except Exception as e:
        logging.error('Error getting order_stats: %s', e)

    return jsonify({
        'success': True,
        'data': {
            'today': {'applications': today_apps, 'orders': today_orders, 'income': round(today_income, 2)},
            'pending_applications': pending_apps,
            'processing_applications': processing_apps,
            'today_orders': today_orders,
            'today_income': round(today_income, 2),
            'application_stats': app_stats,
            'order_stats': order_stats
        }
    })

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
    sql = "SELECT * FROM business_applications WHERE id=%s AND deleted=0"
    app = db.get_one(sql, [app_id])
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
def process_application(user, app_id):
    data = request.get_json() or {}
    action = data.get('action')
    result = data.get('result', '')
    images = data.get('images', [])  # 处理时上传的图片
    
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
    sql = "SELECT * FROM business_orders WHERE id=%s AND deleted=0"
    order = db.get_one(sql, [order_id])
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    return jsonify({'success': True, 'data': order})

@app.route('/api/staff/orders/<order_id>/status', methods=['POST'])
@require_staff
def update_order_status(user, order_id):
    data = request.get_json() or {}
    status = data.get('status')
    
    if not status:
        return jsonify({'success': False, 'msg': '请提供状态'})
    
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
    except Exception as e:
        logging.error('Upload error: %s', e)
        return jsonify({'success': False, 'msg': '上传失败，请重试'})

@app.route('/uploads/<filename>')
def serve_upload(filename):
    """访问上传的图片"""
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'staff-h5', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=22312, debug=False)
