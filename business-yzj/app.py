#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YZJ Channel Message API
端口: 19740 (内部), Nginx反代至19729对外
路由: /channels/yzj/msg
支持: GET / POST
"""

from flask import Flask, request, jsonify
import pymysql
import json
import os
from datetime import datetime

app = Flask(__name__)

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'Wojiacloud$2023',
    'database': 'visit_system',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def success_response(data=None, message='操作成功'):
    """统一成功返回"""
    return jsonify({
        'code': 200,
        'message': message,
        'data': data or {},
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


def error_response(message='操作失败', code=500):
    """统一失败返回"""
    return jsonify({
        'code': code,
        'message': message,
        'data': {},
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }), code if code >= 400 else 200


@app.route('/channels/yzj/msg', methods=['GET', 'POST'])
def yzj_msg():
    """
    YZJ频道消息接口
    GET: 查询消息列表
    POST: 发送/创建消息
    """
    if request.method == 'GET':
        return _get_messages()
    else:
        return _create_message()


def _get_messages():
    """
    GET /channels/yzj/msg
    查询消息列表，支持分页和筛选
    
    Query参数:
    - page: 页码，默认1
    - page_size: 每页条数，默认20
    - msg_type: 消息类型筛选（可选）
    - sender: 发送者筛选（可选）
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    msg_type = request.args.get('msg_type', '')
    sender = request.args.get('sender', '')
    
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    
    offset = (page - 1) * page_size
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 构建查询条件
        conditions = ["1=1"]
        params = []
        
        if msg_type:
            conditions.append("msg_type = %s")
            params.append(msg_type)
        if sender:
            conditions.append("sender = %s")
            params.append(sender)
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM yzj_messages WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 查询列表
        list_sql = f"""
            SELECT id, msg_type, sender, content, extra_data, 
                   create_time, update_time
            FROM yzj_messages 
            WHERE {where_clause}
            ORDER BY create_time DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(list_sql, params + [page_size, offset])
        items = cursor.fetchall()
        
        # 序列化
        for item in items:
            if item.get('extra_data'):
                try:
                    item['extra_data'] = json.loads(item['extra_data'])
                except:
                    pass
            if item.get('create_time'):
                item['create_time'] = item['create_time'].strftime('%Y-%m-%d %H:%M:%S')
            if item.get('update_time'):
                item['update_time'] = item['update_time'].strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.close()
        db.close()
        
        return success_response({
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size
        })
        
    except Exception as e:
        return error_response(f'查询消息失败: {str(e)}')


def _create_message():
    """
    POST /channels/yzj/msg
    创建消息
    
    Body参数 (JSON):
    - msg_type: 消息类型（必填）, 如 text/image/file/system
    - sender: 发送者（必填）
    - content: 消息内容（必填）
    - extra_data: 附加数据（可选，JSON对象）
    """
    data = request.get_json(silent=True) or {}
    
    msg_type = data.get('msg_type', '').strip()
    sender = data.get('sender', '').strip()
    content = data.get('content', '').strip()
    extra_data = data.get('extra_data')
    
    # 参数校验
    if not msg_type:
        return error_response('msg_type 不能为空', 400)
    if not sender:
        return error_response('sender 不能为空', 400)
    if not content:
        return error_response('content 不能为空', 400)
    
    # extra_data 序列化
    if extra_data and not isinstance(extra_data, str):
        extra_data = json.dumps(extra_data, ensure_ascii=False)
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        insert_sql = """
            INSERT INTO yzj_messages (msg_type, sender, content, extra_data)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_sql, [msg_type, sender, content, extra_data])
        db.commit()
        
        msg_id = cursor.lastrowid
        
        cursor.close()
        db.close()
        
        return success_response({
            'id': msg_id,
            'msg_type': msg_type,
            'sender': sender,
            'content': content
        }, '消息发送成功')
        
    except Exception as e:
        return error_response(f'发送消息失败: {str(e)}')


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return success_response({'module': 'yzj-channel-msg', 'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=19740, debug=False)
