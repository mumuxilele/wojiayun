"""
Checkin Service - 签到业务逻辑层
V48.0: MVC架构改造
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CheckinService:
    """签到服务类"""
    
    def __init__(self):
        from business_common import db
        self.db = db
    
    def get_checkin_status(self, user_id: str, ec_id: str, project_id: str = None) -> Dict[str, Any]:
        """
        获取签到状态
        
        Returns:
            {
                'checked_in_today': bool,
                'continuous_days': int,
                'total_days': int,
                'today_points': int,
                'rank': int
            }
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 今日是否签到
        checked_today = self.db.get_one("""
            SELECT id, checkin_time FROM business_checkins 
            WHERE user_id=%s AND DATE(checkin_time)=%s AND deleted=0
        """, [user_id, today])
        
        # 连续签到天数
        continuous_days = self._get_continuous_days(user_id)
        
        # 总签到天数
        total_days = self.db.get_total(
            "SELECT COUNT(*) FROM business_checkins WHERE user_id=%s AND deleted=0",
            [user_id]
        )
        
        # 今日签到积分
        today_points = 0
        if checked_today:
            points_config = self._get_checkin_points(ec_id, project_id)
            today_points = points_config.get('daily', 5)
        
        # 今日排名
        rank = self._get_checkin_rank(user_id, today)
        
        return {
            'checked_in_today': checked_today is not None,
            'checkin_time': checked_today['checkin_time'] if checked_today else None,
            'continuous_days': continuous_days,
            'total_days': total_days,
            'today_points': today_points,
            'rank': rank
        }
    
    def do_checkin(self, user_id: str, ec_id: str, project_id: str = None) -> Dict[str, Any]:
        """
        执行签到
        
        Returns:
            {'success': True, 'msg': '签到成功', 'points': int, 'continuous_days': int}
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 检查今日是否已签到
        existing = self.db.get_one("""
            SELECT id FROM business_checkins 
            WHERE user_id=%s AND DATE(checkin_time)=%s AND deleted=0
        """, [user_id, today])
        
        if existing:
            return {'success': False, 'msg': '今日已签到'}
        
        # 获取签到积分配置
        points_config = self._get_checkin_points(ec_id, project_id)
        
        # 计算连续签到天数
        continuous_days = self._get_continuous_days(user_id) + 1
        
        # 计算本次签到积分（连续签到加成）
        base_points = points_config.get('daily', 5)
        bonus_points = 0
        
        # 连续7天额外奖励
        if continuous_days >= 7:
            bonus_points = points_config.get('week_bonus', 10)
        # 连续30天额外奖励
        elif continuous_days >= 30:
            bonus_points = points_config.get('month_bonus', 50)
        
        total_points = base_points + bonus_points
        
        try:
            # 插入签到记录
            self.db.execute("""
                INSERT INTO business_checkins (user_id, ec_id, project_id, checkin_time, points, continuous_days, created_at)
                VALUES (%s, %s, %s, NOW(), %s, %s, NOW())
            """, [user_id, ec_id, project_id, total_points, continuous_days])
            
            # 更新用户积分
            self.db.execute("""
                UPDATE business_members 
                SET points=points+%s, total_points=total_points+%s, updated_at=NOW()
                WHERE user_id=%s
            """, [total_points, total_points, user_id])
            
            return {
                'success': True,
                'msg': f'签到成功，获得{total_points}积分',
                'points': total_points,
                'continuous_days': continuous_days,
                'bonus_points': bonus_points
            }
            
        except Exception as e:
            logger.error(f"签到失败: {e}")
            return {'success': False, 'msg': f'签到失败: {str(e)}'}
    
    def get_checkin_rank(self, user_id: str, date: str = None) -> int:
        """获取签到排名"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        rank = self.db.get_one("""
            SELECT COUNT(*) + 1 as rank
            FROM business_checkins
            WHERE DATE(checkin_time)=%s AND deleted=0
            AND (checkin_time > (SELECT checkin_time FROM business_checkins WHERE user_id=%s AND DATE(checkin_time)=%s AND deleted=0))
        """, [date, user_id, date])
        
        return rank['rank'] if rank else 0
    
    def _get_continuous_days(self, user_id: str) -> int:
        """计算连续签到天数"""
        today = datetime.now().date()
        days = 0
        
        for i in range(365):  # 最多检查一年
            check_date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            has_checkin = self.db.get_one("""
                SELECT id FROM business_checkins 
                WHERE user_id=%s AND DATE(checkin_time)=%s AND deleted=0
            """, [user_id, check_date])
            
            if has_checkin:
                days += 1
            elif i > 0:  # 今天不检查
                break
        
        return days
    
    def _get_checkin_points(self, ec_id: str, project_id: str) -> Dict[str, int]:
        """获取签到积分配置"""
        config = self.db.get_one("""
            SELECT checkin_daily_points, checkin_week_bonus, checkin_month_bonus
            FROM business_checkin_configs
            WHERE (ec_id=%s OR ec_id='global') AND status=1
            ORDER BY CASE WHEN ec_id='global' THEN 1 ELSE 0 END
            LIMIT 1
        """, [ec_id])
        
        if config:
            return {
                'daily': config.get('checkin_daily_points', 5),
                'week_bonus': config.get('checkin_week_bonus', 10),
                'month_bonus': config.get('checkin_month_bonus', 50)
            }
        
        return {'daily': 5, 'week_bonus': 10, 'month_bonus': 50}
    
    def get_checkin_rewards_config(self, ec_id: str, project_id: str = None) -> Dict[str, Any]:
        """获取签到奖励配置"""
        config = self._get_checkin_points(ec_id, project_id)
        
        return {
            'daily_points': config.get('daily', 5),
            'week_bonus': config.get('week_bonus', 10),
            'week_threshold': 7,
            'month_bonus': config.get('month_bonus', 50),
            'month_threshold': 30
        }


# 单例
_checkin_service = None

def get_checkin_service() -> CheckinService:
    global _checkin_service
    if _checkin_service is None:
        _checkin_service = CheckinService()
    return _checkin_service
