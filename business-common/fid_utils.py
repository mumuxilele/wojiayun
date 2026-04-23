"""
FID生成工具模块 V47.0
功能：生成32位MD5随机字符串作为主键
"""
import hashlib
import uuid
import random
import time


def generate_fid():
    """
    生成32位MD5随机字符串作为主键
    
    算法：MD5(UUID + 随机数 + 时间戳)
    结果：32位小写十六进制字符串
    
    Returns:
        str: 32位FID字符串
    """
    # 组合多个随机因子确保唯一性
    uuid_str = str(uuid.uuid4())
    random_str = str(random.randint(1000000000, 9999999999))
    timestamp_str = str(time.time())
    
    # 拼接并计算MD5
    raw_string = f"{uuid_str}{random_str}{timestamp_str}"
    fid = hashlib.md5(raw_string.encode('utf-8')).hexdigest()
    
    return fid


def generate_fid_with_prefix(prefix):
    """
    生成带前缀的FID
    
    Args:
        prefix: 前缀字符串（如 'ORD', 'APP'）
        
    Returns:
        str: 前缀 + 32位FID
    """
    return f"{prefix}{generate_fid()}"


def batch_generate_fid(count=1):
    """
    批量生成FID
    
    Args:
        count: 生成数量
        
    Returns:
        list: FID字符串列表
    """
    return [generate_fid() for _ in range(count)]


# 预定义的业务前缀
FID_PREFIX = {
    'order': 'ORD',           # 订单
    'application': 'APP',     # 申请
    'booking': 'BOK',         # 预约
    'refund': 'RFD',          # 退款
    'review': 'RVW',          # 评价
    'member': 'MBR',          # 会员
    'product': 'PRD',         # 商品
    'cart': 'CRT',            # 购物车
    'coupon': 'CPN',          # 优惠券
    'invoice': 'INV',         # 发票
    'aftersale': 'AFS',       # 售后
    'visit': 'VST',           # 走访
    'chat': 'CHT',            # 聊天
    'user': 'USR',            # 用户
}


def generate_business_fid(business_type):
    """
    根据业务类型生成带前缀的FID
    
    Args:
        business_type: 业务类型（如 'order', 'application'）
        
    Returns:
        str: 带业务前缀的FID
    """
    prefix = FID_PREFIX.get(business_type, 'FID')
    return generate_fid_with_prefix(prefix)


if __name__ == '__main__':
    # 测试
    print("普通FID:", generate_fid())
    print("带前缀FID:", generate_fid_with_prefix('TEST'))
    print("订单FID:", generate_business_fid('order'))
    print("批量生成:", batch_generate_fid(3))
