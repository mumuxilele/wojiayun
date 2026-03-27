"""
公共配置模块
"""

# 数据库配置
DB_CONFIG = {
    'host': '47.98.238.209',
    'port': 3306,
    'user': 'root',
    'password': 'Wojiacloud$2023',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

# 用户服务配置
USER_SERVICE_URL = 'http://127.0.0.1:22307/getUserInfo'
USER_SERVICE_URL_CLOUD = 'https://wj.wojiacloud.com/getUserInfo'  # 用户端云端
STAFF_SERVICE_URL_CLOUD = 'https://gj.wojiacloud.com/getUserInfo'  # 员工端云端

# 服务端口配置
PORTS = {
    'user': 22311,
    'staff': 22312,
    'admin': 22313
}

# 申请单类型
APP_TYPES = {
    'repair': '报修',
    'booking': '预约',
    'complaint': '投诉',
    'consult': '咨询',
    'other': '其他'
}

# 申请单状态
APP_STATUS = {
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'rejected': '已拒绝'
}

# 订单状态
ORDER_STATUS = {
    'pending': '待支付',
    'paid': '已支付',
    'processing': '处理中',
    'completed': '已完成',
    'cancelled': '已取消'
}
