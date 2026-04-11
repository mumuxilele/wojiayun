"""
公共配置模块
敏感信息必须通过环境变量传入，禁止硬编码：

必填环境变量：
  DB_HOST      - 数据库地址
  DB_PASSWORD  - 数据库密码（生产环境必须设置）

可选环境变量（带默认值，适合开发环境）：
  DB_PORT=3306
  DB_USER=root
  DB_NAME=visit_system
"""
import os

def _require_env(key, default=None, required=True):
    """获取环境变量，敏感信息不允许有默认值"""
    value = os.environ.get(key)
    if not value and required and default is None:
        raise EnvironmentError(f"缺少必填环境变量: {key}，请在启动前设置")
    return value if value else default

# ============ 数据库配置 ============
DB_CONFIG = {
    'host':     _require_env('DB_HOST', required=True),  # 必填，禁止硬编码
    'port':     int(_require_env('DB_PORT', '3306', required=False)),
    'user':     _require_env('DB_USER', 'root', required=False),
    'password': _require_env('DB_PASSWORD', required=True),  # 必填，禁止硬编码
    'database': _require_env('DB_NAME', 'visit_system', required=False),
    'charset':  'utf8mb4',
    'connect_timeout': 10,
    'autocommit': False,
}

# ============ 用户服务配置 ============
USER_SERVICE_URL        = os.environ.get('USER_SERVICE_URL', 'http://127.0.0.1:22307/getUserInfo')
USER_SERVICE_URL_CLOUD  = os.environ.get('USER_SERVICE_URL_CLOUD', 'https://wj.wojiacloud.com/h5/users/api/getUserInfo')
STAFF_SERVICE_URL_CLOUD = os.environ.get('STAFF_SERVICE_URL_CLOUD', 'https://gj.wojiacloud.com/users/getUserInfo')

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
