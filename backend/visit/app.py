#!/usr/bin/env python3
"""
走访台账系统 - 后端API
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import datetime
import json

app = Flask(__name__)
CORS(app)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Root@202400',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def init_table():
    """初始化走访表"""
    db = get_db()
    cursor = db.cursor()
    
    # 创建走访记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visit_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            region VARCHAR(100) COMMENT '区域地址',
            company_name VARCHAR(200) COMMENT '企业名称',
            visitor VARCHAR(50) COMMENT '走访人',
            visitor_name VARCHAR(50) COMMENT '走访人姓名',
            category VARCHAR(20) COMMENT '沟通事项分类:租赁/服务/物业/其他',
            content TEXT COMMENT '沟通事项',
            visit_time DATETIME COMMENT '走访时间',
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted TINYINT DEFAULT 0,
            INDEX idx_region (region),
            INDEX idx_visitor (visitor),
            INDEX idx_visit_time (visit_time),
            INDEX idx_company_name (company_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    
    db.commit()
    cursor.close()
    db.close()

# ==================== API接口 ====================

@app.route('/')
def index():
    return jsonify({'msg': '走访台账系统API', 'version': '1.0'})

# 获取Token（简单验证）
def verify_token():
    token = request.headers.get('Token') or request.args.get('token')
    if not token:
        return None
    return token

# 获取列表
@app.route('/api/visit/list', methods=['GET'])
def get_visit_list():
    token = verify_token()
    if not token:
        return jsonify({'code': 401, 'msg': 'Token不能为空', 'success': False}), 401
    
    # 查询参数
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 10))
    region = request.args.get('region', '')
    visitor = request.args.get('visitor', '')
    visitor_name = request.args.get('visitorName', '')
    category = request.args.get('category', '')
    company_name = request.args.get('companyName', '')
    
    # 日期筛选
    start_date = request.args.get('startDate', '')
    end_date = request.args.get('endDate', '')
    
    # 构建查询
    where = 'WHERE deleted = 0'
    params = []
    
    if region:
        where += ' AND region LIKE %s'
        params.append(f'%{region}%')
    if visitor:
        where += ' AND visitor = %s'
        params.append(visitor)
    if visitor_name:
        where += ' AND visitor_name LIKE %s'
        params.append(f'%{visitor_name}%')
    if category:
        where += ' AND category = %s'
        params.append(category)
    if company_name:
        where += ' AND company_name LIKE %s'
        params.append(f'%{company_name}%')
    if start_date:
        where += ' AND visit_time >= %s'
        params.append(start_date)
    if end_date:
        where += ' AND visit_time <= %s'
        params.append(end_date + ' 23:59:59')
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    # 获取总数
    cursor.execute(f'SELECT COUNT(*) as total FROM visit_records {where}', params)
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * page_size
    cursor.execute(f'''
        SELECT * FROM visit_records 
        {where} 
        ORDER BY visit_time DESC, id DESC
        LIMIT %s OFFSET %s
    ''', params + [page_size, offset])
    
    rows = cursor.fetchall()
    
    # 转换时间格式
    for row in rows:
        if row.get('visit_time'):
            row['visit_time'] = row['visit_time'].strftime('%Y-%m-%d %H:%M:%S')
        if row.get('create_time'):
            row['create_time'] = row['create_time'].strftime('%Y-%m-%d %H:%M:%S')
        if row.get('update_time'):
            row['update_time'] = row['update_time'].strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.close()
    db.close()
    
    return jsonify({
        'code': 200,
        'msg': 'success',
        'success': True,
        'data': {
            'list': rows,
            'total': total,
            'page': page,
            'pageSize': page_size
        }
    })

# 新增记录
@app.route('/api/visit/add', methods=['POST'])
def add_visit():
    token = verify_token()
    if not token:
        return jsonify({'code': 401, 'msg': 'Token不能为空', 'success': False}), 401
    
    data = request.get_json()
    
    # 必填校验
    required_fields = ['region', 'company_name', 'visitor', 'visitor_name', 'category', 'content', 'visit_time']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'code': 400, 'msg': f'{field}不能为空', 'success': False}), 400
    
    # 分类校验
    valid_categories = ['租赁', '服务', '物业', '其他']
    if data['category'] not in valid_categories:
        return jsonify({'code': 400, 'msg': f'分类必须是{valid_categories}之一', 'success': False}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        INSERT INTO visit_records 
        (region, company_name, visitor, visitor_name, category, content, visit_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (
        data['region'],
        data['company_name'],
        data['visitor'],
        data['visitor_name'],
        data['category'],
        data['content'],
        data['visit_time']
    ))
    
    db.commit()
    new_id = cursor.lastrowid
    cursor.close()
    db.close()
    
    return jsonify({
        'code': 200,
        'msg': '新增成功',
        'success': True,
        'data': {'id': new_id}
    })

# 修改记录
@app.route('/api/visit/update', methods=['POST'])
def update_visit():
    token = verify_token()
    if not token:
        return jsonify({'code': 401, 'msg': 'Token不能为空', 'success': False}), 401
    
    data = request.get_json()
    
    if not data.get('id'):
        return jsonify({'code': 400, 'msg': 'ID不能为空', 'success': False}), 400
    
    # 检查记录是否存在
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id FROM visit_records WHERE id = %s AND deleted = 0', (data['id'],))
    if not cursor.fetchone():
        cursor.close()
        db.close()
        return jsonify({'code': 404, 'msg': '记录不存在', 'success': False}), 404
    
    # 更新
    update_fields = []
    params = []
    
    for field in ['region', 'company_name', 'visitor', 'visitor_name', 'category', 'content', 'visit_time']:
        if field in data:
            update_fields.append(f'{field} = %s')
            params.append(data[field])
    
    if update_fields:
        params.append(data['id'])
        cursor.execute(f'''
            UPDATE visit_records 
            SET {', '.join(update_fields)}, update_time = NOW()
            WHERE id = %s
        ''', params)
        db.commit()
    
    cursor.close()
    db.close()
    
    return jsonify({
        'code': 200,
        'msg': '修改成功',
        'success': True
    })

# 删除记录
@app.route('/api/visit/delete', methods=['POST'])
def delete_visit():
    token = verify_token()
    if not token:
        return jsonify({'code': 401, 'msg': 'Token不能为空', 'success': False}), 401
    
    data = request.get_json()
    visit_id = data.get('id')
    
    if not visit_id:
        return jsonify({'code': 400, 'msg': 'ID不能为空', 'success': False}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    # 软删除
    cursor.execute('UPDATE visit_records SET deleted = 1 WHERE id = %s', (visit_id,))
    db.commit()
    
    cursor.close()
    db.close()
    
    return jsonify({
        'code': 200,
        'msg': '删除成功',
        'success': True
    })

# 统计汇总
@app.route('/api/visit/stats', methods=['GET'])
def get_stats():
    token = verify_token()
    if not token:
        return jsonify({'code': 401, 'msg': 'Token不能为空', 'success': False}), 401
    
    # 筛选参数
    start_date = request.args.get('startDate', '')
    end_date = request.args.get('endDate', '')
    group_by = request.args.get('groupBy', 'month')  # month/quarter/year/region/visitor
    
    where = 'WHERE deleted = 0'
    params = []
    
    if start_date:
        where += ' AND visit_time >= %s'
        params.append(start_date)
    if end_date:
        where += ' AND visit_time <= %s'
        params.append(end_date + ' 23:59:59')
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    # 按不同维度统计
    if group_by == 'month':
        cursor.execute(f'''
            SELECT DATE_FORMAT(visit_time, '%%Y-%%m') as period, COUNT(*) as count
            FROM visit_records {where}
            GROUP BY DATE_FORMAT(visit_time, '%%Y-%%m')
            ORDER BY period DESC
        ''', params)
    elif group_by == 'quarter':
        cursor.execute(f'''
            SELECT CONCAT(DATE_FORMAT(visit_time, '%%Y'), 'Q', QUARTER(visit_time)) as period, COUNT(*) as count
            FROM visit_records {where}
            GROUP BY QUARTER(visit_time), DATE_FORMAT(visit_time, '%%Y')
            ORDER BY period DESC
        ''', params)
    elif group_by == 'year':
        cursor.execute(f'''
            SELECT DATE_FORMAT(visit_time, '%%Y') as period, COUNT(*) as count
            FROM visit_records {where}
            GROUP BY DATE_FORMAT(visit_time, '%%Y')
            ORDER BY period DESC
        ''', params)
    elif group_by == 'region':
        cursor.execute(f'''
            SELECT region as name, COUNT(*) as count
            FROM visit_records {where}
            GROUP BY region
            ORDER BY count DESC
        ''', params)
    elif group_by == 'visitor':
        cursor.execute(f'''
            SELECT visitor_name as name, COUNT(*) as count
            FROM visit_records {where}
            GROUP BY visitor_name
            ORDER BY count DESC
        ''', params)
    elif group_by == 'category':
        cursor.execute(f'''
            SELECT category as name, COUNT(*) as count
            FROM visit_records {where}
            GROUP BY category
            ORDER BY count DESC
        ''', params)
    
    stats = cursor.fetchall()
    
    # 总数
    cursor.execute(f'SELECT COUNT(*) as total FROM visit_records {where}', params)
    total = cursor.fetchone()['total']
    
    cursor.close()
    db.close()
    
    return jsonify({
        'code': 200,
        'msg': 'success',
        'success': True,
        'data': {
            'stats': stats,
            'total': total
        }
    })

# 获取详情
@app.route('/api/visit/detail', methods=['GET'])
def get_detail():
    token = verify_token()
    if not token:
        return jsonify({'code': 401, 'msg': 'Token不能为空', 'success': False}), 401
    
    visit_id = request.args.get('id')
    
    if not visit_id:
        return jsonify({'code': 400, 'msg': 'ID不能为空', 'success': False}), 400
    
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute('SELECT * FROM visit_records WHERE id = %s AND deleted = 0', (visit_id,))
    row = cursor.fetchone()
    
    cursor.close()
    db.close()
    
    if not row:
        return jsonify({'code': 404, 'msg': '记录不存在', 'success': False}), 404
    
    # 转换时间格式
    if row.get('visit_time'):
        row['visit_time'] = row['visit_time'].strftime('%Y-%m-%d %H:%M:%S')
    if row.get('create_time'):
        row['create_time'] = row['create_time'].strftime('%Y-%m-%d %H:%M:%S')
    if row.get('update_time'):
        row['update_time'] = row['update_time'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'code': 200,
        'msg': 'success',
        'success': True,
        'data': row
    })

# ==================== 启动 ====================
if __name__ == '__main__':
    init_table()
    print("启动服务: http://0.0.0.0:22306")
    app.run(host='0.0.0.0', port=22306, debug=True)
