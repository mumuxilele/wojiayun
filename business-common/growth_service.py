#!/usr/bin/env python3
"""
成长值服务模块 V28.0
功能:
  - 成长值计算与记录
  - 会员等级自动升级
  - 成长值规则管理
"""
import json
import logging
from datetime import datetime, date
from . import db

logger = logging.getLogger(__name__)


class GrowthService:
    """成长值服务"""

    # 默认等级阈值
    DEFAULT_LEVEL_THRESHOLDS = [
        {'level': 1, 'threshold': 0, 'name': '普通会员'},
        {'level': 2, 'threshold': 100, 'name': '青铜会员'},
        {'level': 3, 'threshold': 500, 'name': '白银会员'},
        {'level': 4, 'threshold': 1000, 'name': '黄金会员'},
        {'level': 5, 'threshold': 2000, 'name': '铂金会员'},
        {'level': 6, 'threshold': 5000, 'name': '钻石会员'},
        {'level': 7, 'threshold': 10000, 'name': '皇冠会员'},
        {'level': 8, 'threshold': 20000, 'name': '至尊会员'},
        {'level': 9, 'threshold': 50000, 'name': '荣耀会员'},
        {'level': 10, 'threshold': 100000, 'name': '传奇会员'},
    ]

    @staticmethod
    def get_level_by_growth(growth):
        """根据成长值计算等级"""
        thresholds = GrowthService.DEFAULT_LEVEL_THRESHOLDS
        level = 1
        for t in thresholds:
            if growth >= t['threshold']:
                level = t['level']
        return level

    @staticmethod
    def get_level_name(level):
        """获取等级名称"""
        for t in GrowthService.DEFAULT_LEVEL_THRESHOLDS:
            if t['level'] == level:
                return t['name']
        return '普通会员'

    @staticmethod
    def add_growth(user_id, user_name, growth_type, value, ref_id='', ref_type='',
                   description='', ec_id=None, project_id=None):
        """
        增加用户成长值

        Args:
            user_id: 用户ID
            user_name: 用户名
            growth_type: 成长类型 (order/checkin/review/referral/activity)
            value: 成长值
            ref_id: 关联ID
            ref_type: 关联类型
            description: 说明
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 结果信息
        """
        if value <= 0:
            return {'success': False, 'msg': '成长值必须大于0'}

        # 检查规则限制
        rule = db.get_one(
            "SELECT * FROM business_growth_rules WHERE growth_type=%s AND is_active=1",
            [growth_type]
        )

        if rule:
            daily_limit = rule.get('daily_limit', 0)
            total_limit = rule.get('total_limit', 0)

            # 检查每日上限
            if daily_limit > 0:
                today = date.today()
                today_count = db.get_total(
                    """SELECT COUNT(*) FROM business_member_growth
                       WHERE user_id=%s AND growth_type=%s AND DATE(created_at)=%s""",
                    [user_id, growth_type, today]
                )
                if today_count >= daily_limit:
                    return {'success': False, 'msg': f'今日{growth_type}成长值已达上限'}

            # 检查累计上限
            if total_limit > 0:
                total_count = db.get_total(
                    """SELECT COUNT(*) FROM business_member_growth
                       WHERE user_id=%s AND growth_type=%s""",
                    [user_id, growth_type]
                )
                if total_count >= total_limit:
                    return {'success': False, 'msg': f'该类型成长值已达累计上限'}

        # 获取用户当前信息
        member = db.get_one(
            "SELECT growth_value, member_grade FROM business_members WHERE user_id=%s",
            [user_id]
        )

        if not member:
            return {'success': False, 'msg': '用户不存在'}

        current_growth = int(member.get('growth_value') or 0)
        level_before = int(member.get('member_grade') or 1)

        # 计算新的成长值和等级
        new_growth = current_growth + value
        level_after = GrowthService.get_level_by_growth(new_growth)

        try:
            conn = db.get_db()
            cursor = conn.cursor()
            conn.begin()

            # 更新会员成长值和等级
            cursor.execute(
                """UPDATE business_members
                   SET growth_value=%s, member_grade=%s, updated_at=NOW()
                   WHERE user_id=%s""",
                [new_growth, level_after, user_id]
            )

            # 记录成长值日志
            cursor.execute(
                """INSERT INTO business_member_growth
                   (user_id, user_name, growth_type, growth_value, total_growth,
                    level_before, level_after, description, ref_id, ref_type, ec_id, project_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [user_id, user_name, growth_type, value, new_growth,
                 level_before, level_after, description, ref_id, ref_type, ec_id, project_id]
            )

            conn.commit()

            result = {
                'success': True,
                'msg': '成长值增加成功',
                'data': {
                    'growth_added': value,
                    'total_growth': new_growth,
                    'level_before': level_before,
                    'level_after': level_after,
                    'level_up': level_after > level_before,
                    'level_name': GrowthService.get_level_name(level_after)
                }
            }

            # 如果等级提升，发送通知
            if level_after > level_before:
                try:
                    from business_common.notification import send_notification
                    send_notification(
                        user_id=user_id,
                        title='等级提升',
                        content=f"恭喜！您的会员等级从{GrowthService.get_level_name(level_before)}提升至{GrowthService.get_level_name(level_after)}！",
                        notify_type='member',
                        ref_type='level_upgrade'
                    )
                except:
                    pass

            return result

        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            logger.error(f"增加成长值失败: {e}")
            return {'success': False, 'msg': '操作失败'}

        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

    @staticmethod
    def get_growth_logs(user_id, page=1, page_size=20):
        """获取成长值记录"""
        total = db.get_total(
            "SELECT COUNT(*) FROM business_member_growth WHERE user_id=%s",
            [user_id]
        )
        offset = (page - 1) * page_size
        logs = db.get_all(
            """SELECT id, growth_type, growth_value, total_growth, level_before, level_after,
                      description, ref_id, ref_type, created_at
               FROM business_member_growth
               WHERE user_id=%s
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            [user_id, page_size, offset]
        )

        return {
            'items': logs or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }

    @staticmethod
    def get_growth_rules(ec_id=None, project_id=None):
        """获取成长值规则"""
        where = "is_active=1"
        params = []

        if ec_id:
            where += " AND (ec_id IS NULL OR ec_id=%s)"
            params.append(ec_id)
        if project_id:
            where += " AND (project_id IS NULL OR project_id=%s)"
            params.append(project_id)

        rules = db.get_all(
            f"""SELECT id, rule_code, rule_name, growth_type, growth_value,
                      daily_limit, total_limit, description
               FROM business_growth_rules WHERE {where}
               ORDER BY sort_order ASC""",
            params
        )
        return rules or []

    @staticmethod
    def get_member_growth_info(user_id):
        """获取会员成长值详情"""
        member = db.get_one(
            "SELECT user_id, user_name, growth_value, member_grade FROM business_members WHERE user_id=%s",
            [user_id]
        )

        if not member:
            return None

        growth = int(member.get('growth_value') or 0)
        current_level = int(member.get('member_grade') or 1)

        # 获取下一等级阈值
        thresholds = GrowthService.DEFAULT_LEVEL_THRESHOLDS
        next_threshold = None
        for t in thresholds:
            if t['level'] == current_level + 1:
                next_threshold = t
                break

        # 计算距离下一等级还需要多少成长值
        progress = 0
        if next_threshold:
            current_threshold = 0
            for t in thresholds:
                if t['level'] == current_level:
                    current_threshold = t['threshold']
                    break
            progress = min(100, int((growth - current_threshold) / (next_threshold['threshold'] - current_threshold) * 100))

        return {
            'user_id': member.get('user_id'),
            'user_name': member.get('user_name'),
            'growth_value': growth,
            'current_level': current_level,
            'level_name': GrowthService.get_level_name(current_level),
            'next_level': next_threshold['level'] if next_threshold else None,
            'next_level_name': next_threshold['name'] if next_threshold else None,
            'next_threshold': next_threshold['threshold'] if next_threshold else None,
            'progress_to_next': progress,
            'next_growth_needed': max(0, (next_threshold['threshold'] if next_threshold else 0) - growth)
        }
