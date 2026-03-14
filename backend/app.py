"""
企业走访台账系统 - 后端服务
需要安装: pip install flask flask-cors pymysql
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import datetime
import json

app = Flask(__name__)
CORS(app)

# 数据库配置 - 请修改为你的数据库信息
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

# Token缓存（实际应该存Redis或数据库）
TOKEN_CACHE = {}

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def init_database():
    """初始化数据库表"""
    conn = pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    
    # 创建数据库
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    cursor.execute(f"USE {DB_CONFIG['database']}")
    
    # 创建走访记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visit_records (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            company_name VARCHAR(255) NOT NULL COMMENT '企业名称',
            region VARCHAR(255) COMMENT '区域地址',
            staff_id VARCHAR(64) COMMENT '企服人员ID',
            staff_name VARCHAR(64) NOT NULL COMMENT '企服人员姓名',
            visit_date DATE NOT NULL COMMENT '走访日期',
            category VARCHAR(32) COMMENT '沟通事项分类',
            content TEXT COMMENT '沟通详情',
            
            create_by VARCHAR(64) COMMENT '新增人',
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '新增时间',
            update_by VARCHAR(64) COMMENT '修改人',
            update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
            delete_by VARCHAR(64) COMMENT '删除人',
            delete_time DATETIME COMMENT '删除时间',
            deleted TINYINT DEFAULT 0 COMMENT '删除状态 0正常 1已删除',
            
            INDEX idx_staff_id (staff_id),
            INDEX idx_visit_date (visit_date),
            INDEX idx_deleted (deleted)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='走访记录表'
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    print("数据库初始化完成!")

# ============ Token验证 ============
def verify_token(token):
    """验证token是否有效"""
    if not token:
        return False, "Token不能为空"
    
    # TODO: 这里应该调用我家云接口验证token
    # 暂时直接返回成功
    return True, token

# ============ 中间件 ============
def token_required(f):
    """Token验证装饰器"""
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            # 尝试从query参数获取
            token = request.args.get('access_token')
        
        is_valid, result = verify_token(token)
        if not is_valid:
            return jsonify({'success': False, 'msg': result, 'code': 401})
        
        request.token = token
        request.user_id = result
        return f(*args, **kwargs)
    
    decorated.__name__ = f.__name__
    return decorated

# ============ 员工搜索接口（代理） ============
@app.route('/api/employees/search')
@token_required
def search_employees():
    """搜索员工列表"""
    name = request.args.get('name', '')
    current = int(request.args.get('current', 1))
    row_count = int(request.args.get('rowCount', 20))
    project_id = request.args.get('projectID', '')
    
    import urllib.request
    import urllib.parse
    
    # 调用我家云接口
    base_url = 'https://gj.wojiacloud.com/h5/api/employees/getEmployeeListByName'
    params = {
        'access_token': request.token,
        'time': int(datetime.datetime.now().timestamp() * 1000),
        'projectID': project_id,
        'name': urllib.parse.quote(name),
        'rowCount': row_count,
        'current': current
    }
    
    url = base_url + '?' + urllib.parse.urlencode(params)
    
    try:
        ctx = __import__('ssl').create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = __import__('ssl').CERT_NONE
        
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e), 'data': []})

# ============ 走访记录CRUD ============

@app.route('/api/visits', methods=['GET'])
@token_required
def get_visits():
    """获取走访记录列表"""
    page = int(request.args.get('current', 1))
    page_size = int(request.args.get('rowCount', 10))
    month = request.args.get('month', '')
    staff_id = request.args.get('staffId', '')
    category = request.args.get('category', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # 构建查询条件
    where = "WHERE deleted = 0"
    params = []
    
    if month:
        where += " AND DATE_FORMAT(visit_date, '%%Y-%%m') = %s"
        params.append(month)
    
    if staff_id:
        where += " AND staff_id = %s"
        params.append(staff_id)
    
    if category:
        where += " AND category = %s"
        params.append(category)
    
    # 查询总数
    cursor.execute(f"SELECT COUNT(*) as total FROM visit_records {where}", params)
    total = cursor.fetchone()['total']
    
    # 分页查询
    offset = (page - 1) * page_size
    cursor.execute(
        f"{where} ORDER BY visit_date DESC, id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # 转换日期格式
    for row in rows:
        if row.get('visit_date'):
            row['visit_date'] = str(row['visit_date'])
        if row.get('create_time'):
            row['create_time'] = row['create_time'].strftime('%Y-%m-%d %H:%M:%S')
        if row.get('update_time'):
            row['update_time'] = row['update_time'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'success': True,
        'data': {
            'rows': rows,
            'total': total,
            'current': page,
            'rowCount': page_size
        }
    })

@app.route('/api/visits', methods=['POST'])
@token_required
def create_visit():
    """新增走访记录"""
    data = request.json
    
    required_fields = ['companyName', 'staffId', 'staffName', 'visitDate']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'msg': f'{field}不能为空'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    user_name = data.get('userName', '系统用户')
    
    sql = '''
        INSERT INTO visit_records 
        (company_name, region, staff_id, staff_name, visit_date, category, content, create_by, create_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    
    cursor.execute(sql, (
        data.get('companyName'),
        data.get('region', ''),
        data.get('staffId'),
        data.get('staffName'),
        data.get('visitDate'),
        data.get('category', ''),
        data.get('content', ''),
        user_name,
        now
    ))
    
    record_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'msg': '保存成功',
        'data': {'id': record_id}
    })

@app.route('/api/visits/<int:record_id>', methods=['PUT'])
@token_required
def update_visit(record_id):
    """修改走访记录"""
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    user_name = data.get('userName', '系统用户')
    
    sql = '''
        UPDATE visit_records SET
            company_name = %s,
            region = %s,
            staff_id = %s,
            staff_name = %s,
            visit_date = %s,
            category = %s,
            content = %s,
            update_by = %s,
            update_time = %s
        WHERE id = %s AND deleted = 0
    '''
    
    cursor.execute(sql, (
        data.get('companyName'),
        data.get('region', ''),
        data.get('staffId'),
        data.get('staffName'),
        data.get('visitDate'),
        data.get('category', ''),
        data.get('content', ''),
        user_name,
        now,
        record_id
    ))
    
    conn.commit()
    affected = cursor.affected_rows()
    cursor.close()
    conn.close()
    
    if affected == 0:
        return jsonify({'success': False, 'msg': '记录不存在或已删除'})
    
    return jsonify({'success': True, 'msg': '修改成功'})

@app.route('/api/visits/<int:record_id>', methods=['DELETE'])
@token_required
def delete_visit(record_id):
    """删除走访记录（软删除）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    user_name = request.args.get('userName', '系统用户')
    
    sql = '''
        UPDATE visit_records SET
            deleted = 1,
            delete_by = %s,
            delete_time = %s
        WHERE id = %s AND deleted = 0
    '''
    
    cursor.execute(sql, (user_name, now, record_id))
    
    conn.commit()
    affected = cursor.affected_rows()
    cursor.close()
    conn.close()
    
    if affected == 0:
        return jsonify({'success': False, 'msg': '记录不存在或已删除'})
    
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 统计接口 ============
@app.route('/api/visits/stats')
@token_required
def get_stats():
    """获取统计数据"""
    stats_type = request.args.get('type', 'month')  # month/quarter/year
    region = request.args.get('region', '')
    staff_id = request.args.get('staffId', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # 构建条件
    where = "WHERE deleted = 0"
    params = []
    
    if region:
        where += " AND region = %s"
        params.append(region)
    
    if staff_id:
        where += " AND staff_id = %s"
        params.append(staff_id)
    
    # 按时间维度统计
    if stats_type == 'month':
        date_format = "DATE_FORMAT(visit_date, '%%Y-%%m')"
    elif stats_type == 'quarter':
        date_format = "CONCAT(YEAR(visit_date), '-Q', QUARTER(visit_date))"
    else:
        date_format = "YEAR(visit_date)"
    
    sql = f'''
        SELECT 
            {date_format} as period,
            COUNT(*) as count,
            COUNT(DISTINCT company_name) as company_count
        FROM visit_records
        {where}
        GROUP BY {date_format}
        ORDER BY period DESC
    '''
    
    cursor.execute(sql, params)
    stats = cursor.fetchall()
    
    # 汇总统计
    cursor.execute(f"SELECT COUNT(*) as total FROM visit_records {where}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(f"SELECT COUNT(DISTINCT company_name) as companies FROM visit_records {where}", params)
    companies = cursor.fetchone()['companies']
    
    cursor.execute(f"SELECT COUNT(DISTINCT staff_id) as staff FROM visit_records {where}", params)
    staff = cursor.fetchone()['staff']
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'data': {
            'stats': stats,
            'summary': {
                'total': total,
                'companies': companies,
                'staff': staff
            }
        }
    })

# ============ 健康检查 ============
@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# ============ 启动 ============
if __name__ == '__main__':
    # 初始化数据库（首次运行）
    # init_database()
    
    print("启动服务: http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
