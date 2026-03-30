"""
客户认证服务
端口: 22320
接口: GET /account/customer
"""

from flask import Flask, request, jsonify, send_from_directory
import hmac
import hashlib
import time
import logging
import pymysql
from urllib.parse import quote
import os
import json

app = Flask(__name__, static_folder='.', static_url_path='')

# 配置
CUSTOMER_ACCOUNT_SECRET_KEY = os.environ.get('CUSTOMER_ACCOUNT_SECRET_KEY', 'wojiacloud_secret_key_2026')
PORT = 22320

# 数据库配置
DB_CONFIG = {
    'host': '47.98.238.209',
    'user': 'root',
    'password': 'Wojiacloud$2023',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auth-service')


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def init_db():
    """初始化数据库表"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                provider VARCHAR(32) DEFAULT 'customer',
                customer_id VARCHAR(128) NOT NULL,
                name VARCHAR(128),
                extra_info TEXT,
                token VARCHAR(256),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_provider_customer (provider, customer_id),
                INDEX idx_customer_id (customer_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        conn.commit()
        logger.info("Database table initialized")
    finally:
        conn.close()


def generate_token(customer_id, name):
    """生成用户token"""
    msg = f'{customer_id}{name}{time.time()}'
    return hashlib.sha256(msg.encode()).hexdigest()


def verify_signature(customer_id, name, extra_info, timestamp, code):
    """
    验证签名
    签名算法: SHA256(HMAC(SECRET_KEY, customer_id + name + extra_info + timestamp))
    """
    # 时间戳验证（60秒内有效）
    current_ts = int(time.time())
    ts_diff = abs(int(timestamp) - current_ts)
    
    if ts_diff > 60:
        logger.error(f'Timestamp diff too much: {ts_diff} seconds')
        return False, f'timestamp expired (diff: {ts_diff}s, max: 60s)'
    
    # 构建签名字符串
    msg = f'{customer_id}{name}{extra_info}{timestamp}'
    
    # 计算签名
    expected_sign = hmac.new(
        CUSTOMER_ACCOUNT_SECRET_KEY.encode('utf-8'),
        msg.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    if expected_sign != code:
        logger.error(f'Sign mismatch: expected={expected_sign}, got={code}, msg={msg}')
        return False, 'invalid signature'
    
    return True, 'ok'


def find_or_create_account(customer_id, name, extra_info):
    """查找或创建账户"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查找现有账户
        cursor.execute(
            'SELECT * FROM auth_accounts WHERE provider = %s AND customer_id = %s',
            ('customer', customer_id)
        )
        account = cursor.fetchone()
        
        if account:
            # 更新账户信息
            cursor.execute(
                '''UPDATE auth_accounts 
                   SET name = %s, extra_info = %s, updated_at = NOW()
                   WHERE id = %s''',
                (name or f'customer_{customer_id}', extra_info, account['id'])
            )
            conn.commit()
            account['name'] = name or f'customer_{customer_id}'
            account['extra_info'] = extra_info
            logger.info(f"Account updated: {customer_id}")
            return account
        else:
            # 创建新账户
            token = generate_token(customer_id, name)
            cursor.execute(
                '''INSERT INTO auth_accounts (provider, customer_id, name, extra_info, token)
                   VALUES (%s, %s, %s, %s, %s)''',
                ('customer', customer_id, name or f'customer_{customer_id}', extra_info, token)
            )
            conn.commit()
            account_id = cursor.lastrowid
            logger.info(f"Account created: {customer_id}")
            return {
                'id': account_id,
                'provider': 'customer',
                'customer_id': customer_id,
                'name': name or f'customer_{customer_id}',
                'extra_info': extra_info,
                'token': token
            }
    finally:
        conn.close()


@app.route('/account/customer', methods=['GET'])
def customer_auth():
    """
    客户认证接口
    
    参数:
    - CustomerId: 用户ID (必需)
    - Name: 用户名 (可选)
    - Timestamp: 时间戳 (必需)
    - ExtraInfo: 用户信息 (可选)
    - Code: 签名 (必需)
    
    签名算法: SHA256(HMAC(SECRET_KEY, CustomerId + Name + ExtraInfo + Timestamp))
    """
    # 获取参数
    customer_id = request.args.get('CustomerId', '')
    name = request.args.get('Name', '')
    timestamp = request.args.get('Timestamp', '')
    extra_info = request.args.get('ExtraInfo', '')
    code = request.args.get('Code', '')
    
    logger.info(f"Auth request: customer_id={customer_id}, name={name}, timestamp={timestamp}")
    
    # 参数验证
    if not customer_id:
        return jsonify({
            'success': False,
            'error': 'CustomerId is required'
        }), 400
    
    if not timestamp:
        return jsonify({
            'success': False,
            'error': 'Timestamp is required'
        }), 400
    
    if not code:
        return jsonify({
            'success': False,
            'error': 'Code is required'
        }), 400
    
    try:
        timestamp_int = int(timestamp)
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid timestamp'
        }), 400
    
    # 验证签名
    valid, msg = verify_signature(customer_id, name, extra_info, timestamp_int, code)
    if not valid:
        return jsonify({
            'success': False,
            'error': msg
        }), 401
    
    # 查找或创建账户
    try:
        account = find_or_create_account(customer_id, name, extra_info)
        return jsonify({
            'success': True,
            'data': {
                'id': account['id'],
                'customer_id': account['customer_id'],
                'name': account['name'],
                'extra_info': account['extra_info'],
                'token': account.get('token', ''),
                'provider': account['provider']
            }
        })
    except Exception as e:
        logger.error(f"Database error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'service': 'auth-service',
        'port': PORT
    })


@app.route('/', methods=['GET'])
def index():
    """首页 - 测试页面"""
    return send_from_directory('.', 'index.html')


@app.route('/api/generate-url', methods=['POST'])
def generate_url():
    """
    生成认证URL（供测试使用）
    
    请求体:
    {
        "customer_id": "用户ID",
        "name": "用户名",
        "extra_info": "额外信息"
    }
    """
    data = request.get_json() or {}
    
    customer_id = data.get('customer_id', '')
    name = data.get('name', '')
    extra_info = data.get('extra_info', '')
    
    if not customer_id:
        return jsonify({
            'success': False,
            'error': 'customer_id is required'
        }), 400
    
    # 生成时间戳和签名
    timestamp = int(time.time())
    msg = f'{customer_id}{name}{extra_info}{timestamp}'
    code = hmac.new(
        CUSTOMER_ACCOUNT_SECRET_KEY.encode('utf-8'),
        msg.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # 构建URL
    base_url = request.host_url.rstrip('/')
    url = f"{base_url}/account/customer?CustomerId={quote(customer_id)}&Name={quote(name)}&Timestamp={timestamp}&ExtraInfo={quote(extra_info)}&Code={code}"
    
    return jsonify({
        'success': True,
        'data': {
            'url': url,
            'customer_id': customer_id,
            'name': name,
            'timestamp': timestamp,
            'code': code
        }
    })


if __name__ == '__main__':
    init_db()
    logger.info(f"Auth service starting on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
