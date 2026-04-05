#!/usr/bin/env python3
"""
V19.0: 申请单超时监控服务
- 检测挂起超过24小时的申请单
- 自动发送站内通知和员工端提醒
"""
import logging
from datetime import datetime, timedelta
from business_common import db, notification
from business_common.websocket_service import push_notification
from business_common.cache_service import cache_get, cache_set

logger = logging.getLogger(__name__)

# 超时阈值（小时）
TIMEOUT_HOURS = 24
# 提醒冷却时间（小时）- 避免重复提醒
REMINDER_COOLDOWN_HOURS = 4


def check_overdue_applications():
    """
    检查超时的申请单并发送提醒
    返回: (超时数量, 发送提醒数量)
    """
    try:
        # 查询挂起超过24小时的申请单
        # status: pending=待处理, processing=处理中
        overdue_apps = db.get_all(
            """SELECT a.id, a.app_no, a.app_type, a.title, a.user_id, a.user_name, 
                      a.status, a.created_at, a.ec_id, a.project_id,
                      TIMESTAMPDIFF(HOUR, a.created_at, NOW()) as hours_pending
               FROM business_applications a
               WHERE a.deleted=0 
                 AND a.status IN ('pending', 'processing')
                 AND TIMESTAMPDIFF(HOUR, a.created_at, NOW()) >= %s
               ORDER BY a.created_at ASC""",
            [TIMEOUT_HOURS]
        )
        
        if not overdue_apps:
            return 0, 0
        
        overdue_count = len(overdue_apps)
        reminder_sent = 0
        
        for app in overdue_apps:
            app_id = app['id']
            hours = app.get('hours_pending', TIMEOUT_HOURS)
            
            # 检查是否已经发送过提醒（冷却期内不重复发送）
            cache_key = f"app_reminder_{app_id}"
            last_reminder = cache_get(cache_key)
            
            if last_reminder:
                # 冷却期内跳过
                continue
            
            # 发送站内通知给员工
            status_text = '待处理' if app['status'] == 'pending' else '处理中'
            title = f"⚠️ 申请单超时提醒"
            content = (f"申请单 {app['app_no']} 已挂起 {hours} 小时\n"
                      f"类型：{app['app_type']}\n"
                      f"标题：{app['title']}\n"
                      f"用户：{app['user_name']}\n"
                      f"当前状态：{status_text}")
            
            notification.send_notification(
                user_id='staff',
                title=title,
                content=content,
                notify_type='application_overdue',
                ec_id=app.get('ec_id'),
                project_id=app.get('project_id')
            )
            
            # WebSocket推送给员工端
            push_notification(
                channel='staff',
                data={
                    'type': 'application_overdue',
                    'app_id': app_id,
                    'app_no': app['app_no'],
                    'app_type': app['app_type'],
                    'title': app['title'],
                    'user_name': app['user_name'],
                    'status': app['status'],
                    'hours_pending': hours,
                    'created_at': app['created_at'].isoformat() if isinstance(app['created_at'], datetime) else str(app['created_at'])
                }
            )
            
            # 设置提醒缓存（冷却期）
            cache_set(cache_key, {'sent_at': datetime.now().isoformat()}, REMINDER_COOLDOWN_HOURS * 3600)
            reminder_sent += 1
            
            logger.info(f"已发送申请单超时提醒: app_id={app_id}, hours={hours}")
        
        return overdue_count, reminder_sent
        
    except Exception as e:
        logger.error(f"检查超时申请单失败: {e}")
        return 0, 0


def get_overdue_statistics(ec_id=None, project_id=None):
    """
    获取超时申请单统计（用于员工端展示）
    """
    try:
        where = "a.deleted=0 AND a.status IN ('pending', 'processing') AND TIMESTAMPDIFF(HOUR, a.created_at, NOW()) >= %s"
        params = [TIMEOUT_HOURS]
        
        if ec_id:
            where += " AND a.ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND a.project_id=%s"
            params.append(project_id)
        
        # 按超时时长分组统计
        stats = db.get_all(
            f"""SELECT 
                CASE 
                    WHEN TIMESTAMPDIFF(HOUR, a.created_at, NOW()) < 48 THEN '24-48小时'
                    WHEN TIMESTAMPDIFF(HOUR, a.created_at, NOW()) < 72 THEN '48-72小时'
                    ELSE '超过72小时'
                END as overdue_range,
                COUNT(*) as count
            FROM business_applications a
            WHERE {where}
            GROUP BY overdue_range""",
            params
        )
        
        # 总超时数量
        total = db.get_total(
            f"SELECT COUNT(*) FROM business_applications a WHERE {where}",
            params
        )
        
        # 最紧急的5条
        urgent = db.get_all(
            f"""SELECT a.id, a.app_no, a.app_type, a.title, a.user_name, 
                       a.status, a.created_at,
                       TIMESTAMPDIFF(HOUR, a.created_at, NOW()) as hours_pending
                FROM business_applications a
                WHERE {where}
                ORDER BY a.created_at ASC
                LIMIT 5""",
            params
        )
        
        return {
            'total_overdue': total,
            'distribution': stats or [],
            'urgent_list': urgent or []
        }
        
    except Exception as e:
        logger.error(f"获取超时统计失败: {e}")
        return {'total_overdue': 0, 'distribution': [], 'urgent_list': []}


def get_application_timeline(app_id):
    """
    获取申请单处理时间线（用于详情页展示）
    """
    try:
        app = db.get_one(
            """SELECT id, app_no, status, created_at, updated_at, completed_at,
                      TIMESTAMPDIFF(HOUR, created_at, NOW()) as hours_pending,
                      TIMESTAMPDIFF(HOUR, created_at, updated_at) as hours_to_first_update,
                      TIMESTAMPDIFF(HOUR, created_at, completed_at) as hours_to_complete
               FROM business_applications
               WHERE id=%s AND deleted=0""",
            [app_id]
        )
        
        if not app:
            return None
        
        timeline = []
        created_at = app.get('created_at')
        
        if created_at:
            timeline.append({
                'time': created_at.isoformat() if isinstance(created_at, datetime) else str(created_at),
                'event': '申请提交',
                'description': '用户提交申请'
            })
        
        hours = app.get('hours_pending', 0)
        if app['status'] in ('pending', 'processing') and hours >= TIMEOUT_HOURS:
            timeline.append({
                'time': (datetime.now() - timedelta(hours=hours - TIMEOUT_HOURS)).isoformat(),
                'event': '⚠️ 超时警告',
                'description': f'申请已挂起 {hours} 小时，超过 {TIMEOUT_HOURS} 小时处理时限'
            })
        
        if app.get('completed_at'):
            timeline.append({
                'time': app['completed_at'].isoformat() if isinstance(app['completed_at'], datetime) else str(app['completed_at']),
                'event': '处理完成',
                'description': f'耗时 {app.get("hours_to_complete", "未知")} 小时'
            })
        
        return {
            'application': app,
            'timeline': timeline,
            'is_overdue': hours >= TIMEOUT_HOURS if app['status'] in ('pending', 'processing') else False
        }
        
    except Exception as e:
        logger.error(f"获取申请单时间线失败: {e}")
        return None


# 定时任务入口（可被外部调度器调用）
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    count, sent = check_overdue_applications()
    print(f"检查完成: {count} 条超时申请, 发送 {sent} 条提醒")
