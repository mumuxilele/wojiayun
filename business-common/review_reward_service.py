"""
V38.0 评价积分奖励服务
提供评价完成后的积分和成长值奖励

功能：
1. 评价积分奖励规则
2. 奖励发放记录
3. 奖励撤销（差评申诉后）
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any
from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)


class ReviewRewardService(BaseService):
    """评价积分奖励服务"""
    
    SERVICE_NAME = 'ReviewRewardService'
    
    # 评价积分奖励规则
    REWARD_RULES = {
        5: {'points': 20, 'growth': 10, 'label': '5星好评'},
        4: {'points': 10, 'growth': 5, 'label': '4星好评'},
        3: {'points': 5, 'growth': 2, 'label': '3星中评'},
        2: {'points': 0, 'growth': 0, 'label': '2星差评'},
        1: {'points': 0, 'growth': 0, 'label': '1星差评'},
    }
    
    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_review_rewards WHERE status=1")
            base['total_rewards'] = result.get('cnt', 0) if result else 0
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base
    
    def get_reward_by_rating(self, rating: int) -> Dict:
        """根据评分获取奖励规则"""
        rating = max(1, min(5, rating))  # 确保在1-5范围内
        return self.REWARD_RULES.get(rating, {'points': 0, 'growth': 0, 'label': '未知'})
    
    def grant_reward(self, user_id: int, review_id: int, order_id: int,
                    rating: int, ec_id: int, project_id: int) -> Dict:
        """
        发放评价积分奖励
        
        Args:
            user_id: 用户ID
            review_id: 评价ID
            order_id: 关联订单ID
            rating: 评分 1-5
            ec_id: 企业ID
            project_id: 项目ID
        
        Returns:
            {"success": True, "points": 20, "growth": 10, "message": "..."}
        """
        # 检查是否已经发放过奖励
        existing = db.get_one("""
            SELECT id FROM business_review_rewards 
            WHERE review_id=%s AND status=1
        """, [review_id])
        
        if existing:
            return {
                'success': False,
                'msg': '该评价已发放过奖励',
                'points': 0,
                'growth': 0,
            }
        
        # 获取奖励规则
        reward = self.get_reward_by_rating(rating)
        points = reward['points']
        growth = reward['growth']
        label = reward['label']
        
        if points == 0 and growth == 0:
            return {
                'success': True,
                'msg': f'该评价({label})不发放积分奖励',
                'points': 0,
                'growth': 0,
                'rating': rating,
                'reward_label': label,
            }
        
        try:
            # 记录奖励
            db.execute("""
                INSERT INTO business_review_rewards
                (user_id, review_id, order_id, rating, points_reward, growth_reward, status, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s)
            """, [user_id, review_id, order_id, rating, points, growth, ec_id, project_id])
            
            # 发放积分
            if points > 0:
                self._add_points(user_id, points, ec_id, project_id)
            
            # 发放成长值
            if growth > 0:
                self._add_growth(user_id, growth)
            
            logger.info(f"[ReviewRewardService] 用户 {user_id} 评价获得奖励："
                       f"积分 {points}，成长值 {growth}（{label}）")
            
            return {
                'success': True,
                'msg': f'评价成功，获得{label}奖励',
                'points': points,
                'growth': growth,
                'rating': rating,
                'reward_label': label,
            }
            
        except Exception as e:
            logger.error(f"[ReviewRewardService] 发放评价奖励失败: {e}")
            return {
                'success': False,
                'msg': '奖励发放失败',
                'points': 0,
                'growth': 0,
            }
    
    def revoke_reward(self, review_id: int) -> Dict:
        """
        撤销评价奖励（差评申诉后）
        """
        try:
            reward = db.get_one("""
                SELECT * FROM business_review_rewards 
                WHERE review_id=%s AND status=1
            """, [review_id])
            
            if not reward:
                return {'success': False, 'msg': '奖励记录不存在或已撤销'}
            
            # 撤销奖励
            db.execute("""
                UPDATE business_review_rewards 
                SET status=0, updated_at=NOW()
                WHERE review_id=%s
            """, [review_id])
            
            # 扣回积分
            if reward['points_reward'] > 0:
                db.execute("""
                    UPDATE business_members
                    SET points = GREATEST(0, points - %s),
                        total_points = GREATEST(0, total_points - %s),
                        updated_at = NOW()
                    WHERE user_id=%s
                """, [reward['points_reward'], reward['points_reward'], reward['user_id']])
                
                # 记录积分变动
                self._add_points_log(
                    user_id=reward['user_id'],
                    points=-reward['points_reward'],
                    change_type='reward_revoke',
                    change_reason=f'评价奖励撤销（{reward["rating"]}星）',
                    ec_id=reward['ec_id'],
                    project_id=reward['project_id']
                )
            
            # 扣回成长值
            if reward['growth_reward'] > 0:
                db.execute("""
                    UPDATE business_members
                    SET growth_value = GREATEST(0, growth_value - %s),
                        updated_at = NOW()
                    WHERE user_id=%s
                """, [reward['growth_reward'], reward['user_id']])
            
            logger.info(f"[ReviewRewardService] 撤销评价 {review_id} 的奖励")
            
            return {
                'success': True,
                'msg': '奖励已撤销',
                'revoked_points': reward['points_reward'],
                'revoked_growth': reward['growth_reward'],
            }
            
        except Exception as e:
            logger.error(f"[ReviewRewardService] 撤销奖励失败: {e}")
            return {'success': False, 'msg': str(e)}
    
    def get_user_reward_stats(self, user_id: int) -> Dict:
        """获取用户评价奖励统计"""
        stats = db.get_one("""
            SELECT 
                COUNT(*) as total_reviews,
                SUM(CASE WHEN status=1 THEN 1 ELSE 0 END) as rewarded_reviews,
                SUM(CASE WHEN status=1 THEN points_reward ELSE 0 END) as total_points,
                SUM(CASE WHEN status=1 THEN growth_reward ELSE 0 END) as total_growth,
                AVG(CASE WHEN status=1 THEN rating ELSE NULL END) as avg_rating
            FROM business_review_rewards
            WHERE user_id=%s
        """, [user_id])
        
        return {
            'total_reviews': stats.get('total_reviews', 0) or 0,
            'rewarded_reviews': stats.get('rewarded_reviews', 0) or 0,
            'total_points_earned': stats.get('total_points', 0) or 0,
            'total_growth_earned': stats.get('total_growth', 0) or 0,
            'avg_rating': round(stats.get('avg_rating', 0) or 0, 1),
        }
    
    def get_reward_rules_display(self) -> list:
        """获取奖励规则展示"""
        return [
            {
                'rating': rating,
                'label': rules['label'],
                'points': rules['points'],
                'growth': rules['growth'],
            }
            for rating, rules in sorted(self.REWARD_RULES.items())
        ]
    
    def _add_points(self, user_id: int, points: int, ec_id: int, project_id: int):
        """增加用户积分"""
        db.execute("""
            UPDATE business_members
            SET points = points + %s,
                total_points = total_points + %s,
                updated_at = NOW()
            WHERE user_id=%s
        """, [points, points, user_id])
        
        # 记录积分日志
        self._add_points_log(
            user_id=user_id,
            points=points,
            change_type='review_reward',
            change_reason='商品评价奖励',
            ec_id=ec_id,
            project_id=project_id
        )
    
    def _add_growth(self, user_id: int, growth: int):
        """增加用户成长值"""
        db.execute("""
            UPDATE business_members
            SET growth_value = growth_value + %s,
                updated_at = NOW()
            WHERE user_id=%s
        """, [growth, user_id])
    
    def _add_points_log(self, user_id: int, points: int, change_type: str,
                       change_reason: str, ec_id: int, project_id: int):
        """记录积分变动日志"""
        now = datetime.now()
        try:
            db.execute("""
                INSERT INTO business_points_log 
                (user_id, change_type, change_reason, points_change, ec_id, project_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [user_id, change_type, change_reason, points, ec_id, project_id, now])
        except Exception as e:
            logger.warning(f"[ReviewRewardService] 记录积分日志失败: {e}")


# 全局实例
review_reward_service = ReviewRewardService()
