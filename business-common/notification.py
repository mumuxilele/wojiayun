"""
消息通知服务模块 V6.0
支持: 站内通知、业务事件通知（申请状态变更、订单状态变更、预约状态变更等）
V20.0: 新增通知发送失败重试机制（最多3次，指数退避）
"""
import json
import logging
import time
from . import db

logger = logging.getLogger(__name__)

# 通知类型常量
NOTIFY_TYPES = {
    'system': '系统通知',
    'order': '订单通知',
    'application': '申请通知',
    'booking': '预约通知',
    'promotion': '促销通知',
    'points': '积分通知',
    'coupon': '优惠券通知',
}

# 重试配置
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.5  # 首次重试等待0.5秒


def send_notification(user_id, title, content, notify_type='system', 
                     ref_id=None, ref_type=None, ec_id=None, project_id=None):
    """
    发送站内通知（带重试机制）
    
    Args:
        user_id: 接收用户ID
        title: 通知标题
        content: 通知内容
        notify_type: 通知类型 (system/order/application/booking/promotion/points/coupon)
        ref_id: 关联业务ID
        ref_type: 关联业务类型
        ec_id: 企业ID
        project_id: 项目ID
    
    Returns:
        bool: 是否发送成功
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            db.execute(
                """INSERT INTO business_notifications 
                   (user_id, title, content, notify_type, ref_id, ref_type, ec_id, project_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                [user_id, title, content, notify_type, ref_id, ref_type, ec_id, project_id]
            )
            logger.info(f"通知发送成功: user={user_id}, type={notify_type}, title={title}")
            return True
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait_time = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(f"通知发送失败(第{attempt}次), {wait_time}s后重试: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"通知发送最终失败(已重试{MAX_RETRIES}次): {e}")
    return False


def send_batch_notification(user_ids, title, content, notify_type='system',
                           ref_id=None, ref_type=None, ec_id=None, project_id=None):
    """
    批量发送通知
    
    Args:
        user_ids: 用户ID列表
        title: 通知标题
        content: 通知内容
        notify_type: 通知类型
        ref_id: 关联业务ID
        ref_type: 关联业务类型
        ec_id: 企业ID
        project_id: 项目ID
    """
    if not user_ids:
        return 0
    
    try:
        sql = """INSERT INTO business_notifications 
                (user_id, title, content, notify_type, ref_id, ref_type, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        params_list = [
            [uid, title, content, notify_type, ref_id, ref_type, ec_id, project_id]
            for uid in user_ids
        ]
        count = db.execute_many(sql, params_list)
        logger.info(f"批量通知发送成功: {count}条, type={notify_type}, title={title}")
        return count
    except Exception as e:
        logger.error(f"批量通知发送失败: {e}")
        return 0


def get_user_notifications(user_id, page=1, page_size=20, is_read=None, notify_type=None):
    """
    获取用户通知列表
    
    Args:
        user_id: 用户ID
        page: 页码
        page_size: 每页数量
        is_read: 是否已读 (None=全部, True=已读, False=未读)
        notify_type: 通知类型筛选
    """
    where = "user_id=%s AND deleted=0"
    params = [user_id]
    
    if is_read is not None:
        where += " AND is_read=%s"
        params.append(1 if is_read else 0)
    if notify_type:
        where += " AND notify_type=%s"
        params.append(notify_type)
    
    total = db.get_total("SELECT COUNT(*) FROM business_notifications WHERE " + where, params)
    
    # 未读数量
    unread_count = db.get_total(
        "SELECT COUNT(*) FROM business_notifications WHERE user_id=%s AND is_read=0 AND deleted=0",
        [user_id]
    )
    
    offset = (page - 1) * page_size
    items = db.get_all(
        """SELECT id, title, content, notify_type, ref_id, ref_type, is_read, 
                  read_at, created_at 
           FROM business_notifications WHERE """ + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    
    return {
        'items': items or [],
        'total': total,
        'unread_count': unread_count,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }


def mark_as_read(notification_id, user_id):
    """标记通知为已读"""
    try:
        db.execute(
            "UPDATE business_notifications SET is_read=1, read_at=NOW() WHERE id=%s AND user_id=%s",
            [notification_id, user_id]
        )
        return True
    except Exception as e:
        logger.error(f"标记已读失败: {e}")
        return False


def mark_all_as_read(user_id):
    """标记所有通知为已读"""
    try:
        db.execute(
            "UPDATE business_notifications SET is_read=1, read_at=NOW() WHERE user_id=%s AND is_read=0",
            [user_id]
        )
        return True
    except Exception as e:
        logger.error(f"批量标记已读失败: {e}")
        return False


def delete_notification(notification_id, user_id):
    """删除(软删除)通知"""
    try:
        db.execute(
            "UPDATE business_notifications SET deleted=1 WHERE id=%s AND user_id=%s",
            [notification_id, user_id]
        )
        return True
    except Exception as e:
        logger.error(f"删除通知失败: {e}")
        return False


# ============ 业务事件通知快捷方法 ============

def notify_application_status(user_id, app_no, new_status, old_status=''):
    """申请状态变更通知"""
    status_map = {
        'pending': '待处理', 'processing': '处理中', 
        'completed': '已完成', 'rejected': '已拒绝', 'cancelled': '已取消'
    }
    title = f"申请状态更新"
    content = f"您的申请 {app_no} 状态已从「{status_map.get(old_status, old_status)}」变更为「{status_map.get(new_status, new_status)}」"
    send_notification(user_id, title, content, notify_type='application', ref_id=app_no, ref_type='application')


def notify_order_status(user_id, order_no, new_status):
    """订单状态变更通知"""
    status_map = {
        'pending': '待支付', 'paid': '已支付', 'processing': '处理中',
        'completed': '已完成', 'cancelled': '已取消'
    }
    title = f"订单状态更新"
    content = f"您的订单 {order_no} 状态已更新为「{status_map.get(new_status, new_status)}」"
    send_notification(user_id, title, content, notify_type='order', ref_id=order_no, ref_type='order')


def notify_booking_status(user_id, booking_info, new_status):
    """预约状态变更通知"""
    status_map = {
        'pending': '待确认', 'confirmed': '已确认', 
        'completed': '已完成', 'cancelled': '已取消'
    }
    venue_name = booking_info.get('venue_name', '场地')
    title = f"预约状态更新"
    content = f"您预约的「{venue_name}」状态已更新为「{status_map.get(new_status, new_status)}」"
    ref_id = booking_info.get('verify_code', str(booking_info.get('id', '')))
    send_notification(user_id, title, content, notify_type='booking', ref_id=ref_id, ref_type='booking')


def notify_points_change(user_id, points, balance_after, description):
    """积分变动通知"""
    if points > 0:
        title = f"积分到账 +{points}"
    else:
        title = f"积分扣减 {points}"
    content = f"{description}，当前积分余额：{balance_after}"
    send_notification(user_id, title, content, notify_type='points')
