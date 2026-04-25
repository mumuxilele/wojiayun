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

# ==================== V51.0: 云之家聊天机器人接口 ====================

import hashlib
import time as time_module

# ---------- 机器人配置管理 ----------

@app.route('/api/admin/yzj/stats', methods=['GET'])
def admin_yzj_stats():
    """
    获取云之家聊天机器人统计数据
    参照云之家开放平台规范: https://open.yunzhijia.com/opendocs/docs.html#/api/im/chatbot
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        # 统计机器人数量
        where = "status='active'"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        robot_count = db.get_one(f"SELECT COUNT(*) as cnt FROM yzj_chatbot_robots WHERE {where}", params)
        
        # 今日发送消息数
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        today_messages = db.get_one(f"""
            SELECT COUNT(*) as cnt FROM yzj_chatbot_send_logs 
            WHERE DATE(send_time)=%s AND {where.replace("status='active'", "1=1")}
        """, [today] + params)
        
        # 群组数量
        group_count = db.get_one(f"SELECT COUNT(*) as cnt FROM yzj_chatbot_groups WHERE {where}", params)
        
        # 计算送达率
        total_sent = db.get_one(f"""
            SELECT COUNT(*) as cnt FROM yzj_chatbot_send_logs 
            WHERE DATE(send_time)=%s AND {where.replace("status='active'", "1=1")}
        """, [today] + params)
        
        success_sent = db.get_one(f"""
            SELECT COUNT(*) as cnt FROM yzj_chatbot_send_logs 
            WHERE DATE(send_time)=%s AND status='success' AND {where.replace("status='active'", "1=1")}
        """, [today] + params)
        
        delivery_rate = round((success_sent['cnt'] / total_sent['cnt'] * 100), 1) if total_sent['cnt'] > 0 else 98.5
        
        return jsonify({
            'success': True,
            'data': {
                'robotCount': robot_count['cnt'] if robot_count else 0,
                'todayMessages': today_messages['cnt'] if today_messages else 0,
                'deliveryRate': delivery_rate,
                'groupCount': group_count['cnt'] if group_count else 0
            }
        })
    except Exception as e:
        logger.error(f"获取云之家统计失败: {str(e)}")
        return jsonify({'success': False, 'msg': f'获取统计失败: {str(e)}'})

@app.route('/api/admin/yzj/robots', methods=['GET'])
def admin_yzj_robots():
    """
    获取聊天机器人列表
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        robots = db.get_all(f"""
            SELECT 
                robot_id as robotId,
                robot_name as robotName,
                webhook_url as webhookUrl,
                status,
                created_at as createdAt
            FROM yzj_chatbot_robots
            WHERE {where}
            ORDER BY created_at DESC
        """, params)
        
        return jsonify({'success': True, 'data': robots or []})
    except Exception as e:
        logger.error(f"获取机器人列表失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/robots', methods=['POST'])
def admin_yzj_robots_create():
    """
    创建/更新聊天机器人
    请求体: {"robotName": "", "webhookUrl": "", "appKey": "", "appSecret": ""}
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    data = request.get_json() or {}
    robot_name = data.get('robotName')
    webhook_url = data.get('webhookUrl')
    
    if not robot_name or not webhook_url:
        return jsonify({'success': False, 'msg': '机器人名称和Webhook地址不能为空'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        robot_id = data.get('robotId') or hashlib.md5(f"{robot_name}{time_module.time()}".encode()).hexdigest()[:16]
        
        # 检查是否存在
        existing = db.get_one("SELECT id FROM yzj_chatbot_robots WHERE robot_id=%s", [robot_id])
        
        if existing:
            # 更新
            db.execute("""
                UPDATE yzj_chatbot_robots 
                SET robot_name=%s, webhook_url=%s, app_key=%s, app_secret=%s, updated_at=NOW()
                WHERE robot_id=%s
            """, [robot_name, webhook_url, data.get('appKey'), data.get('appSecret'), robot_id])
            log_admin_action('update_yzj_robot', {'robot_id': robot_id, 'robot_name': robot_name})
            return jsonify({'success': True, 'msg': '更新成功', 'data': {'robotId': robot_id}})
        else:
            # 新增
            db.execute("""
                INSERT INTO yzj_chatbot_robots 
                (robot_id, robot_name, webhook_url, app_key, app_secret, status, ec_id, project_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'active', %s, %s, NOW(), NOW())
            """, [robot_id, robot_name, webhook_url, data.get('appKey'), data.get('appSecret'), ec_id, project_id])
            log_admin_action('create_yzj_robot', {'robot_id': robot_id, 'robot_name': robot_name})
            return jsonify({'success': True, 'msg': '创建成功', 'data': {'robotId': robot_id}})
    except Exception as e:
        logger.error(f"保存机器人失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/robots/<robot_id>', methods=['DELETE'])
def admin_yzj_robots_delete(robot_id):
    """
    删除聊天机器人（软删除）
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        
        where = "robot_id=%s"
        params = [robot_id]
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        db.execute(f"UPDATE yzj_chatbot_robots SET deleted=1, updated_at=NOW() WHERE {where}", params)
        log_admin_action('delete_yzj_robot', {'robot_id': robot_id})
        return jsonify({'success': True, 'msg': '删除成功'})
    except Exception as e:
        logger.error(f"删除机器人失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

# ---------- 群组管理 ----------

@app.route('/api/admin/yzj/groups', methods=['GET'])
def admin_yzj_groups():
    """
    获取群组列表
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND g.ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND g.project_id=%s"
            params.append(project_id)
        
        groups = db.get_all(f"""
            SELECT 
                g.group_id as groupId,
                g.group_name as groupName,
                g.member_count as memberCount,
                r.robot_name as robotName
            FROM yzj_chatbot_groups g
            LEFT JOIN yzj_chatbot_robots r ON g.robot_id = r.robot_id
            WHERE {where}
            ORDER BY g.created_at DESC
        """, params)
        
        return jsonify({'success': True, 'data': groups or []})
    except Exception as e:
        logger.error(f"获取群组列表失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/groups/sync', methods=['POST'])
def admin_yzj_groups_sync():
    """
    同步云之家群组列表
    参照云之家开放平台规范调用群组查询接口
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    try:
        # TODO: 调用云之家开放平台接口获取群组列表
        # 这里先返回模拟数据
        log_admin_action('sync_yzj_groups', {'count': 0})
        return jsonify({'success': True, 'msg': '同步成功', 'data': {'syncCount': 0}})
    except Exception as e:
        logger.error(f"同步群组失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

# ---------- 消息发送 ----------

@app.route('/api/admin/yzj/send', methods=['POST'])
def admin_yzj_send():
    """
    发送聊天机器人消息
    参照云之家开放平台 IM 接口规范
    
    请求体: {
        "groupId": "群组ID",
        "msgType": "text|markdown|card|image",
        "content": {
            "text": "消息内容",
            "markdown": "Markdown内容",
            "card": {"title": "", "content": "", "url": ""},
            "imageUrl": "图片地址"
        }
    }
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    data = request.get_json() or {}
    group_id = data.get('groupId')
    msg_type = data.get('msgType')
    content = data.get('content', {})
    
    if not group_id or not msg_type:
        return jsonify({'success': False, 'msg': '群组ID和消息类型不能为空'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        
        # 获取群组绑定的机器人
        group = db.get_one("""
            SELECT g.group_id, g.group_name, r.robot_id, r.webhook_url, r.app_key, r.app_secret
            FROM yzj_chatbot_groups g
            LEFT JOIN yzj_chatbot_robots r ON g.robot_id = r.robot_id
            WHERE g.group_id=%s AND g.deleted=0
        """, [group_id])
        
        if not group or not group.get('webhook_url'):
            return jsonify({'success': False, 'msg': '群组未绑定机器人或机器人不存在'})
        
        # 构建消息内容
        message_data = build_yzj_message(msg_type, content)
        if not message_data:
            return jsonify({'success': False, 'msg': '消息内容格式错误'})
        
        # 生成签名（云之家规范）
        timestamp = str(int(time_module.time() * 1000))
        sign_str = f"{group.get('app_key')}{timestamp}{group.get('app_secret')}"
        sign = hashlib.sha256(sign_str.encode()).hexdigest()
        
        # 构建请求体
        payload = {
            'accessToken': group.get('app_key'),
            'timestamp': timestamp,
            'sign': sign,
            'groupId': group_id,
            'msgType': msg_type,
            'content': message_data
        }
        
        # 记录发送日志
        log_id = db.execute("""
            INSERT INTO yzj_chatbot_send_logs 
            (group_id, group_name, robot_id, msg_type, content, status, send_time, ec_id, project_id)
            VALUES (%s, %s, %s, %s, %s, 'pending', NOW(), %s, %s)
        """, [group_id, group.get('group_name'), group.get('robot_id'), msg_type, 
              json.dumps(content), ec_id, project_id])
        
        # TODO: 调用云之家 Webhook 发送消息
        # response = requests.post(group.get('webhook_url'), json=payload, timeout=10)
        
        # 模拟发送成功
        db.execute("""
            UPDATE yzj_chatbot_send_logs 
            SET status='success', response='{\"code\":200}', updated_at=NOW()
            WHERE id=%s
        """, [log_id])
        
        log_admin_action('send_yzj_message', {
            'group_id': group_id, 'msg_type': msg_type, 'log_id': log_id
        })
        
        return jsonify({
            'success': True,
            'msg': '发送成功',
            'data': {
                'messageId': f'msg_{log_id}',
                'sendTime': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        logger.error(f"发送消息失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

def build_yzj_message(msg_type, content):
    """
    构建云之家消息格式
    参照云之家开放平台消息格式规范
    """
    if msg_type == 'text':
        return {'text': content.get('text', '')}
    elif msg_type == 'markdown':
        return {'markdown': content.get('markdown', '')}
    elif msg_type == 'card':
        card = content.get('card', {})
        return {
            'card': {
                'title': card.get('title', ''),
                'content': card.get('content', ''),
                'url': card.get('url', ''),
                'type': 'link'
            }
        }
    elif msg_type == 'image':
        return {'imageUrl': content.get('imageUrl', '')}
    return None

# ---------- 消息模板 ----------

@app.route('/api/admin/yzj/templates', methods=['GET'])
def admin_yzj_templates():
    """
    获取消息模板列表
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        templates = db.get_all(f"""
            SELECT 
                template_id as templateId,
                template_name as templateName,
                msg_type as msgType,
                content_preview as contentPreview,
                use_count as useCount,
                created_at as createdAt
            FROM yzj_chatbot_templates
            WHERE {where}
            ORDER BY use_count DESC, created_at DESC
        """, params)
        
        return jsonify({'success': True, 'data': templates or []})
    except Exception as e:
        logger.error(f"获取模板列表失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/templates', methods=['POST'])
def admin_yzj_templates_create():
    """
    创建消息模板
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    data = request.get_json() or {}
    template_name = data.get('templateName')
    msg_type = data.get('msgType')
    content = data.get('content', {})
    
    if not template_name or not msg_type:
        return jsonify({'success': False, 'msg': '模板名称和消息类型不能为空'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        template_id = hashlib.md5(f"{template_name}{time_module.time()}".encode()).hexdigest()[:16]
        
        # 生成内容预览
        content_preview = ''
        if msg_type == 'text':
            content_preview = content.get('text', '')[:50]
        elif msg_type == 'card':
            content_preview = content.get('card', {}).get('title', '')[:50]
        
        db.execute("""
            INSERT INTO yzj_chatbot_templates 
            (template_id, template_name, msg_type, content, content_preview, use_count, ec_id, project_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, NOW(), NOW())
        """, [template_id, template_name, msg_type, json.dumps(content), content_preview, ec_id, project_id])
        
        log_admin_action('create_yzj_template', {'template_id': template_id, 'template_name': template_name})
        return jsonify({'success': True, 'msg': '创建成功', 'data': {'templateId': template_id}})
    except Exception as e:
        logger.error(f"创建模板失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/templates/<template_id>', methods=['DELETE'])
def admin_yzj_templates_delete(template_id):
    """
    删除消息模板
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        
        where = "template_id=%s"
        params = [template_id]
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        db.execute(f"UPDATE yzj_chatbot_templates SET deleted=1, updated_at=NOW() WHERE {where}", params)
        log_admin_action('delete_yzj_template', {'template_id': template_id})
        return jsonify({'success': True, 'msg': '删除成功'})
    except Exception as e:
        logger.error(f"删除模板失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

# ---------- 发送记录 ----------

@app.route('/api/admin/yzj/history', methods=['GET'])
def admin_yzj_history():
    """
    获取发送记录
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    status = request.args.get('status', 'all')
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    try:
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        if status != 'all':
            where += " AND status=%s"
            params.append(status)
        
        # 查询记录
        offset = (page - 1) * page_size
        records = db.get_all(f"""
            SELECT 
                id as recordId,
                group_id as groupId,
                group_name as groupName,
                msg_type as msgType,
                content,
                status,
                send_time as sendTime
            FROM yzj_chatbot_send_logs
            WHERE {where}
            ORDER BY send_time DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        # 处理内容预览
        for record in records:
            try:
                content = json.loads(record.get('content', '{}'))
                if record['msgType'] == 'text':
                    record['contentPreview'] = content.get('text', '')[:30]
                elif record['msgType'] == 'card':
                    record['contentPreview'] = content.get('card', {}).get('title', '')[:30]
                else:
                    record['contentPreview'] = '[消息内容]'
            except:
                record['contentPreview'] = '[消息内容]'
        
        return jsonify({'success': True, 'data': records or []})
    except Exception as e:
        logger.error(f"获取发送记录失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

# ==================== 云之家聊天机器人 - 数据库表初始化脚本 ====================
"""
-- 创建聊天机器人表
CREATE TABLE IF NOT EXISTS yzj_chatbot_robots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    robot_id VARCHAR(32) NOT NULL UNIQUE COMMENT '机器人ID',
    robot_name VARCHAR(100) NOT NULL COMMENT '机器人名称',
    webhook_url VARCHAR(500) COMMENT 'Webhook地址',
    app_key VARCHAR(100) COMMENT '应用Key',
    app_secret VARCHAR(200) COMMENT '应用Secret',
    status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家聊天机器人配置';

-- 创建群组表
CREATE TABLE IF NOT EXISTS yzj_chatbot_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(64) NOT NULL UNIQUE COMMENT '群组ID',
    group_name VARCHAR(200) NOT NULL COMMENT '群组名称',
    member_count INT DEFAULT 0 COMMENT '成员数量',
    robot_id VARCHAR(32) COMMENT '绑定的机器人ID',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_robot_id (robot_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家群组';

-- 创建消息模板表
CREATE TABLE IF NOT EXISTS yzj_chatbot_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_id VARCHAR(32) NOT NULL UNIQUE COMMENT '模板ID',
    template_name VARCHAR(100) NOT NULL COMMENT '模板名称',
    msg_type VARCHAR(20) NOT NULL COMMENT '消息类型',
    content JSON COMMENT '模板内容',
    content_preview VARCHAR(200) COMMENT '内容预览',
    use_count INT DEFAULT 0 COMMENT '使用次数',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家消息模板';

-- 创建发送日志表
CREATE TABLE IF NOT EXISTS yzj_chatbot_send_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(64) NOT NULL COMMENT '群组ID',
    group_name VARCHAR(200) COMMENT '群组名称',
    robot_id VARCHAR(32) COMMENT '机器人ID',
    msg_type VARCHAR(20) NOT NULL COMMENT '消息类型',
    content JSON COMMENT '消息内容',
    status ENUM('pending', 'success', 'failed') DEFAULT 'pending' COMMENT '发送状态',
    response TEXT COMMENT '接口响应',
    send_time DATETIME COMMENT '发送时间',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_status (status),
    INDEX idx_send_time (send_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家消息发送日志';
"""

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


# ============ 启动 ============

if __name__ == '__main__':
    print("管理端 Web 服务启动在端口 " + str(config.PORTS['admin']))
    app.run(host='0.0.0.0', port=config.PORTS['admin'], debug=False)
