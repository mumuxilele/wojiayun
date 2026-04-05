"""
积分过期服务 V16.0
功能：
  1. 积分过期检查与执行
  2. 过期前提醒通知（30天/7天/1天）
  3. 积分过期记录追踪

使用方式:
    from business_common.points_scheduler import PointsExpireService
    # 检查并执行过期
    PointsExpireService.process_expired_points()
    # 发送过期提醒
    PointsExpireService.send_expiring_notifications()
"""
import logging
from datetime import datetime, timedelta
from . import db

logger = logging.getLogger(__name__)


class PointsExpireService:
    """积分过期服务"""

    # 积分有效期（月）
    POINTS_VALIDITY_MONTHS = 12

    @staticmethod
    def record_points_earned(user_id, points, description='', ec_id=None, project_id=None):
        """
        记录用户获得的积分（用于追踪过期）

        Args:
            user_id: 用户ID
            points: 获得的积分数量
            description: 积分描述
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            bool: 是否记录成功
        """
        try:
            if points <= 0:
                return False

            earned_at = datetime.now()
            expires_at = earned_at + timedelta(days=PointsExpireService.POINTS_VALIDITY_MONTHS * 30)

            db.execute("""
                INSERT INTO business_points_expiring
                (user_id, points_earned, earned_at, expires_at, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [user_id, points, earned_at, expires_at, ec_id, project_id])

            return True
        except Exception as e:
            logger.warning(f"记录积分获得失败: {e}")
            return False

    @staticmethod
    def process_expired_points():
        """
        处理过期的积分
        - 查找已过期的积分记录
        - 扣除用户积分
        - 记录过期日志
        - 发送通知

        Returns:
            dict: 处理结果统计
        """
        result = {
            'processed': 0,
            'total_expired_points': 0,
            'errors': []
        }

        try:
            now = datetime.now()

            # 查找已过期的活跃积分记录
            expired_records = db.get_all("""
                SELECT pe.*, m.points as current_points, m.user_name
                FROM business_points_expiring pe
                LEFT JOIN business_members m ON pe.user_id = m.user_id
                WHERE pe.status = 'active'
                AND pe.expires_at < %s
                ORDER BY pe.expires_at ASC
                LIMIT 1000
            """, [now])

            if not expired_records:
                logger.info("无过期积分需要处理")
                return result

            for record in expired_records:
                try:
                    user_id = record['user_id']
                    expired_points = record['points_earned']
                    current_points = record.get('current_points', 0) or 0

                    # 实际扣除的积分数量（不能超过当前余额）
                    deduct_points = min(expired_points, current_points)

                    if deduct_points <= 0:
                        # 积分已用完，标记为已过期
                        db.execute("""
                            UPDATE business_points_expiring
                            SET status = 'expired', expired_at = %s
                            WHERE id = %s
                        """, [now, record['id']])
                        continue

                    conn = db.get_db()
                    cursor = conn.cursor()
                    conn.begin()

                    try:
                        # 扣除用户积分
                        cursor.execute("""
                            UPDATE business_members
                            SET points = GREATEST(0, points - %s),
                                total_points = GREATEST(0, total_points - %s)
                            WHERE user_id = %s
                        """, [deduct_points, deduct_points, user_id])

                        # 记录积分日志
                        cursor.execute("""
                            INSERT INTO business_points_log
                            (user_id, log_type, points, balance_after, description, ec_id, project_id)
                            SELECT %s, 'expire', -%s, points, %s, %s, %s
                            FROM business_members WHERE user_id = %s
                        """, [
                            user_id, deduct_points,
                            '积分过期自动扣除（有效期12个月）',
                            record.get('ec_id'), record.get('project_id'),
                            user_id
                        ])

                        # 标记积分记录为已过期
                        cursor.execute("""
                            UPDATE business_points_expiring
                            SET status = 'expired', expired_at = %s
                            WHERE id = %s
                        """, [now, record['id']])

                        conn.commit()

                        result['processed'] += 1
                        result['total_expired_points'] += deduct_points

                        logger.info(f"积分过期处理: user={user_id}, 过期={deduct_points}积分")

                        # 发送通知
                        try:
                            from .notification import send_notification
                            send_notification(
                                user_id=user_id,
                                title='积分过期提醒',
                                content=f'您的 {int(deduct_points)} 积分已过期，为保障您的权益，请及时使用积分。',
                                notify_type='points',
                                ec_id=record.get('ec_id'),
                                project_id=record.get('project_id')
                            )
                        except Exception as e:
                            logger.warning(f"发送过期通知失败: {e}")

                    except Exception as e:
                        conn.rollback()
                        raise e
                    finally:
                        cursor.close()
                        conn.close()

                except Exception as e:
                    error_msg = f"处理用户 {record.get('user_id')} 积分过期失败: {e}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)

        except Exception as e:
            logger.error(f"积分过期处理任务异常: {e}")
            result['errors'].append(str(e))

        logger.info(f"积分过期处理完成: 处理={result['processed']}条, 总过期={result['total_expired_points']}积分")
        return result

    @staticmethod
    def send_expiring_notifications():
        """
        发送积分即将过期提醒
        - 到期前30天提醒一次
        - 到期前7天提醒一次
        - 到期前1天提醒一次
        """
        result = {
            'notified_30d': 0,
            'notified_7d': 0,
            'notified_1d': 0,
            'errors': []
        }

        try:
            now = datetime.now()

            # 30天内即将过期
            in_30_days = now + timedelta(days=30)
            records_30d = db.get_all("""
                SELECT pe.*, m.user_name, m.points
                FROM business_points_expiring pe
                LEFT JOIN business_members m ON pe.user_id = m.user_id
                WHERE pe.status = 'active'
                AND pe.expires_at BETWEEN %s AND %s
                AND pe.notified_30days = 0
                LIMIT 100
            """, [now, in_30_days])

            # 7天内即将过期
            in_7_days = now + timedelta(days=7)
            records_7d = db.get_all("""
                SELECT pe.*, m.user_name, m.points
                FROM business_points_expiring pe
                LEFT JOIN business_members m ON pe.user_id = m.user_id
                WHERE pe.status = 'active'
                AND pe.expires_at BETWEEN %s AND %s
                AND pe.notified_7days = 0
                LIMIT 100
            """, [now, in_7_days])

            # 1天内即将过期
            in_1_day = now + timedelta(days=1)
            records_1d = db.get_all("""
                SELECT pe.*, m.user_name, m.points
                FROM business_points_expiring pe
                LEFT JOIN business_members m ON pe.user_id = m.user_id
                WHERE pe.status = 'active'
                AND pe.expires_at BETWEEN %s AND %s
                AND pe.notified_1day = 0
                LIMIT 100
            """, [now, in_1_day])

            from .notification import send_notification

            # 处理30天提醒
            for record in records_30d:
                try:
                    send_notification(
                        user_id=record['user_id'],
                        title='积分即将过期提醒',
                        content=f'您有 {int(record["points_earned"])} 积分将于30天后过期，请及时使用！',
                        notify_type='points',
                        ec_id=record.get('ec_id'),
                        project_id=record.get('project_id')
                    )
                    db.execute("""
                        UPDATE business_points_expiring
                        SET notified_30days = 1, notified_at = %s
                        WHERE id = %s
                    """, [now, record['id']])
                    result['notified_30d'] += 1
                except Exception as e:
                    logger.warning(f"发送30天提醒失败: {e}")

            # 处理7天提醒
            for record in records_7d:
                try:
                    send_notification(
                        user_id=record['user_id'],
                        title='积分即将过期提醒',
                        content=f'您有 {int(record["points_earned"])} 积分将于7天后过期，请尽快使用！',
                        notify_type='points',
                        ec_id=record.get('ec_id'),
                        project_id=record.get('project_id')
                    )
                    db.execute("""
                        UPDATE business_points_expiring
                        SET notified_7days = 1, notified_at = %s
                        WHERE id = %s
                    """, [now, record['id']])
                    result['notified_7d'] += 1
                except Exception as e:
                    logger.warning(f"发送7天提醒失败: {e}")

            # 处理1天提醒
            for record in records_1d:
                try:
                    send_notification(
                        user_id=record['user_id'],
                        title='积分即将过期提醒',
                        content=f'您有 {int(record["points_earned"])} 积分将于明天过期，请立即使用！',
                        notify_type='points',
                        ec_id=record.get('ec_id'),
                        project_id=record.get('project_id')
                    )
                    db.execute("""
                        UPDATE business_points_expiring
                        SET notified_1day = 1, notified_at = %s
                        WHERE id = %s
                    """, [now, record['id']])
                    result['notified_1d'] += 1
                except Exception as e:
                    logger.warning(f"发送1天提醒失败: {e}")

        except Exception as e:
            logger.error(f"积分过期提醒任务异常: {e}")
            result['errors'].append(str(e))

        logger.info(f"积分过期提醒完成: 30天={result['notified_30d']}, 7天={result['notified_7d']}, 1天={result['notified_1d']}")
        return result

    @staticmethod
    def get_user_expiring_points(user_id):
        """
        获取用户即将过期的积分

        Args:
            user_id: 用户ID

        Returns:
            list: 即将过期的积分记录
        """
        try:
            now = datetime.now()
            in_30_days = now + timedelta(days=30)

            records = db.get_all("""
                SELECT points_earned, expires_at,
                       DATEDIFF(expires_at, %s) as days_remaining
                FROM business_points_expiring
                WHERE user_id = %s
                AND status = 'active'
                AND expires_at BETWEEN %s AND %s
                ORDER BY expires_at ASC
            """, [now, user_id, now, in_30_days])

            return records or []
        except Exception as e:
            logger.warning(f"查询即将过期积分失败: {e}")
            return []

    @staticmethod
    def get_points_summary(user_id):
        """
        获取用户积分汇总

        Args:
            user_id: 用户ID

        Returns:
            dict: 积分汇总信息
        """
        try:
            # 当前积分
            member = db.get_one("""
                SELECT points, total_points FROM business_members WHERE user_id = %s
            """, [user_id])

            # 即将过期（30天内）
            expiring = db.get_one("""
                SELECT COALESCE(SUM(points_earned), 0) as total
                FROM business_points_expiring
                WHERE user_id = %s
                AND status = 'active'
                AND expires_at BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 30 DAY)
            """, [user_id])

            # 已过期总计
            expired_total = db.get_one("""
                SELECT COALESCE(SUM(points_earned), 0) as total
                FROM business_points_expiring
                WHERE user_id = %s AND status = 'expired'
            """, [user_id])

            return {
                'current_points': member.get('points', 0) if member else 0,
                'total_points': member.get('total_points', 0) if member else 0,
                'expiring_30d': float(expiring.get('total', 0) or 0) if expiring else 0,
                'expired_total': float(expired_total.get('total', 0) or 0) if expired_total else 0
            }
        except Exception as e:
            logger.warning(f"获取积分汇总失败: {e}")
            return {
                'current_points': 0,
                'total_points': 0,
                'expiring_30d': 0,
                'expired_total': 0
            }


# 定时任务入口（供调度器调用）
def run_points_expire_task():
    """积分过期定时任务入口"""
    logger.info("开始执行积分过期检查任务...")
    result = PointsExpireService.process_expired_points()
    logger.info(f"积分过期任务完成: {result}")
    return result


def run_points_notify_task():
    """积分过期提醒定时任务入口"""
    logger.info("开始执行积分过期提醒任务...")
    result = PointsExpireService.send_expiring_notifications()
    logger.info(f"积分提醒任务完成: {result}")
    return result
