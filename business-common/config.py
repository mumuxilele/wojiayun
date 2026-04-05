"""
公共配置模块
优先读取环境变量，未设置时使用默认值（生产环境请务必通过环境变量传入敏感信息）

环境变量示例：
  export DB_HOST=47.98.238.209
  export DB_PASSWORD=your_password
  export DB_NAME=visit_system
"""
import os

# ============ 数据库配置 ============
DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', '47.98.238.209'),
    'port':     int(os.environ.get('DB_PORT', '3306')),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD') or os.environ.get('MYSQL_PWD', ''),
    'database': os.environ.get('DB_NAME', 'visit_system'),
    'charset':  'utf8mb4',
    'connect_timeout': 10,
    'autocommit': False,
}

# ============ 用户服务配置 ============
USER_SERVICE_URL        = os.environ.get('USER_SERVICE_URL', 'http://127.0.0.1:22307/getUserInfo')
USER_SERVICE_URL_CLOUD  = os.environ.get('USER_SERVICE_URL_CLOUD', 'https://wj.wojiacloud.com/getUserInfo')
STAFF_SERVICE_URL_CLOUD = os.environ.get('STAFF_SERVICE_URL_CLOUD', 'https://gj.wojiacloud.com/getUserInfo')

# ============ 服务端口 ============
PORTS = {
    'user':  int(os.environ.get('PORT_USER', '22311')),
    'staff': int(os.environ.get('PORT_STAFF', '22312')),
    'admin': int(os.environ.get('PORT_ADMIN', '22313')),
}

# ============ 申请单类型 ============
APP_TYPES = {
    'repair':    '报修',
    'booking':   '预约',
    'complaint': '投诉',
    'consult':   '咨询',
    'other':     '其他'
}

# ============ 申请单状态 ============
APP_STATUS = {
    'pending':    '待处理',
    'processing': '处理中',
    'completed':  '已完成',
    'rejected':   '已拒绝',
    'cancelled':  '已取消',
}

# ============ 订单状态 ============
ORDER_STATUS = {
    'pending':    '待支付',
    'paid':       '已支付',
    'processing': '处理中',
    'completed':  '已完成',
    'cancelled':  '已取消',
}

# ============ 场地预约状态 ============
BOOKING_STATUS = {
    'pending':   '待确认',
    'confirmed': '已确认',
    'completed': '已完成',
    'cancelled': '已取消',
}

# ============ 支付状态 ============
PAY_STATUS = {
    'unpaid': '未支付',
    'paid':   '已支付',
    'refund': '已退款',
}
