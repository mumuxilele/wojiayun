"""
V38.0 成长任务服务
提供用户成长任务的管理和奖励发放

功能：
1. 成长任务配置管理
2. 用户任务进度追踪
3. 任务完成奖励发放（积分+成长值）
4. 周期任务自动重置
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)

# 任务周期类型
PERIOD_WEEKLY = 'weekly'
PERIOD_MONTHLY = 'monthly'
PERIOD_ONCE = 'once'  # 一次性任务


class GrowthTaskService(BaseService):
    """成长任务服务"""
    
    SERVICE_NAME = 'GrowthTaskService'
    
    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_growth_tasks WHERE status=1")
            base['active_task_count'] = result.get('cnt', 0) if result else 0
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base
    
    # ============ 任务配置管理 ============
    
    def get_all_tasks(self, ec_id: int, project_id: int) -> List[Dict]:
        """获取所有成长任务配置"""
        tasks = db.get_all("""
            SELECT id, task_code, task_name, task_type, description, 
                   target_count, growth_reward, points_reward, icon, status
            FROM business_growth_tasks 
            WHERE ec_id=%s AND project_id=%s AND status=1
            ORDER BY target_count ASC
        """, [ec_id, project_id])
        return tasks or []
    
    def get_task_by_code(self, task_code: str, ec_id: int, project_id: int) -> Optional[Dict]:
        """根据任务代码获取任务"""
        return db.get_one("""
            SELECT * FROM business_growth_tasks 
            WHERE task_code=%s AND ec_id=%s AND project_id=%s
        """, [task_code, ec_id, project_id])
    
    # ============ 用户任务进度 ============
    
    def get_user_tasks(self, user_id: int, ec_id: int, project_id: int) -> List[Dict]:
        """
        获取用户当前周期的所有任务及进度
        
        Returns:
            List: 包含任务信息+用户进度+状态
        """
        today = date.today()
        period_start, period_end = self._get_period_dates(today)
        
        # 获取所有任务
        tasks = self.get_all_tasks(ec_id, project_id)
        
        # 获取用户在当前周期的进度
        progress_list = db.get_all("""
            SELECT task_id, current_count, status, completed_at
            FROM business_user_growth_progress
            WHERE user_id=%s AND period_start=%s
        """, [user_id, period_start])
        
        progress_map = {p['task_id']: p for p in progress_list}
        
        result = []
        for task in tasks:
            task_id = task['id']
            progress = progress_map.get(task_id, {})
            
            current_count = progress.get('current_count', 0)
            status = progress.get('status', 0)
            target_count = task['target_count']
            
            # 计算进度百分比
            progress_percent = min(100, int(current_count / target_count * 100)) if target_count > 0 else 0
            
            result.append({
                'task_id': task_id,
                'task_code': task['task_code'],
                'task_name': task['task_name'],
                'task_type': task['task_type'],
                'description': task['description'],
                'icon': task['icon'],
                'target_count': target_count,
                'current_count': current_count,
                'progress_percent': progress_percent,
                'growth_reward': task['growth_reward'],
                'points_reward': task['points_reward'],
                'status': status,  # 0进行中 1已完成
                'is_completed': status == 1 or current_count >= target_count,
            })
        
        return result
    
    def get_user_task_summary(self, user_id: int, ec_id: int, project_id: int) -> Dict:
        """获取用户任务汇总"""
        tasks = self.get_user_tasks(user_id, ec_id, project_id)
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t['is_completed'])
        
        # 获取本周期的日期范围
        today = date.today()
        period_start, period_end = self._get_period_dates(today)
        
        return {
            'total_tasks': total,
            'completed_tasks': completed,
            'remaining_tasks': total - completed,
            'completion_rate': int(completed / total * 100) if total > 0 else 0,
            'period_start': str(period_start),
            'period_end': str(period_end),
            'tasks': tasks,
        }
    
    def _get_period_dates(self, today: date) -> tuple:
        """获取当前周期日期范围"""
        # 默认周期为每周
        # 计算本周一和下周一
        weekday = today.weekday()  # 0=周一
        period_start = today - timedelta(days=weekday)
        period_end = period_start + timedelta(days=6)
        return period_start, period_end
    
    # ============ 任务进度更新 ============
    
    def increment_task_progress(self, user_id: int, task_type: str, 
                                ec_id: int, project_id: int,
                                delta: int = 1) -> Dict:
        """
        增加用户任务进度
        
        Args:
            user_id: 用户ID
            task_type: 任务类型 (order/checkin/review/share/invite)
            ec_id: 企业ID
            project_id: 项目ID
            delta: 增量，默认1
        
        Returns:
            {"success": True, "completed_tasks": [...], "rewards": {...}}
        """
        today = date.today()
        period_start, period_end = self._get_period_dates(today)
        
        # 查询所有匹配类型的任务
        tasks = db.get_all("""
            SELECT id, task_code, task_name, task_type, target_count, 
                   growth_reward, points_reward
            FROM business_growth_tasks
            WHERE ec_id=%s AND project_id=%s AND status=1 AND task_type=%s
        """, [ec_id, project_id, task_type])
        
        if not tasks:
            return {'success': True, 'completed_tasks': [], 'rewards': {}}
        
        completed_tasks = []
        total_growth_reward = 0
        total_points_reward = 0
        
        for task in tasks:
            task_id = task['id']
            
            # 检查当前进度
            progress = db.get_one("""
                SELECT id, current_count, status
                FROM business_user_growth_progress
                WHERE user_id=%s AND task_id=%s AND period_start=%s
            """, [user_id, task_id, period_start])
            
            if not progress:
                # 新建进度记录
                if delta > 0:
                    db.execute("""
                        INSERT INTO business_user_growth_progress
                        (user_id, task_id, current_count, status, period_start, period_end)
                        VALUES (%s, %s, %s, 0, %s, %s)
                    """, [user_id, task_id, delta, period_start, period_end])
                    
                    new_count = delta
                    old_status = 0
                else:
                    continue
            else:
                if progress['status'] == 1:
                    continue  # 已完成的任务不再更新
                
                old_count = progress.get('current_count', 0)
                old_status = progress.get('status', 0)
                new_count = old_count + delta
                
                if new_count > 0:
                    db.execute("""
                        UPDATE business_user_growth_progress
                        SET current_count=%s, updated_at=NOW()
                        WHERE id=%s
                    """, [new_count, progress['id']])
            
            # 检查是否完成
            target = task['target_count']
            if new_count >= target and old_status == 0:
                # 任务完成！发放奖励
                db.execute("""
                    UPDATE business_user_growth_progress
                    SET status=1, completed_at=NOW(), current_count=%s
                    WHERE user_id=%s AND task_id=%s AND period_start=%s
                """, [target, user_id, task_id, period_start])
                
                completed_tasks.append({
                    'task_code': task['task_code'],
                    'task_name': task['task_name'],
                    'growth_reward': task['growth_reward'],
                    'points_reward': task['points_reward'],
                })
                
                total_growth_reward += task['growth_reward']
                total_points_reward += task['points_reward']
                
                logger.info(f"[GrowthTaskService] 用户 {user_id} 完成任务 {task['task_code']}，"
                           f"发放成长值 {task['growth_reward']}，积分 {task['points_reward']}")
        
        rewards_granted = True
        if completed_tasks:
            rewards_granted = self.grant_rewards(user_id, completed_tasks, ec_id, project_id)
        
        return {
            'success': True,
            'completed_tasks': completed_tasks,
            'total_growth_reward': total_growth_reward,
            'total_points_reward': total_points_reward,
            'rewards_granted': rewards_granted,
        }

    
    # ============ 奖励发放 ============
    
    def grant_rewards(self, user_id: int, completed_tasks: List[Dict],
                     ec_id: int, project_id: int) -> bool:
        """发放任务完成奖励"""
        if not completed_tasks:
            return True
        
        total_points = sum(t['points_reward'] for t in completed_tasks)
        total_growth = sum(t['growth_reward'] for t in completed_tasks)
        
        try:
            # 发放积分
            if total_points > 0:
                self._add_points_log(
                    user_id=user_id,
                    points=total_points,
                    change_type='task_reward',
                    change_reason=f"完成{len(completed_tasks)}个成长任务奖励",
                    ec_id=ec_id,
                    project_id=project_id
                )
                
                # 更新会员积分
                db.execute("""
                    UPDATE business_members
                    SET points = points + %s,
                        total_points = total_points + %s,
                        updated_at = NOW()
                    WHERE user_id=%s
                """, [total_points, total_points, user_id])
            
            # 更新成长值
            if total_growth > 0:
                db.execute("""
                    UPDATE business_members
                    SET growth_value = growth_value + %s,
                        updated_at = NOW()
                    WHERE user_id=%s
                """, [total_growth, user_id])
                
                # 检查是否需要升级会员等级
                self._check_level_upgrade(user_id, ec_id, project_id)
            
            return True
            
        except Exception as e:
            logger.error(f"[GrowthTaskService] 发放奖励失败: {e}")
            return False
    
    def _add_points_log(self, user_id: int, points: int, change_type: str,
                        change_reason: str, ec_id: int, project_id: int):
        """记录积分变动日志"""
        now = datetime.now()
        db.execute("""
            INSERT INTO business_points_log 
            (user_id, change_type, change_reason, points_change, balance_after, ec_id, project_id, created_at)
            VALUES (%s, %s, %s, %s, 
                    (SELECT points FROM business_members WHERE user_id=%s),
                    %s, %s, %s)
        """, [user_id, change_type, change_reason, points, user_id, ec_id, project_id, now])
    
    def _check_level_upgrade(self, user_id: int, ec_id: int, project_id: int):
        """检查并执行会员等级升级"""
        member = db.get_one("""
            SELECT m.*, l.level_code as current_level_code
            FROM business_members m
            LEFT JOIN business_member_levels l ON m.member_grade = l.level_name
            WHERE m.user_id=%s
        """, [user_id])
        
        if not member:
            return
        
        current_growth = member.get('growth_value', 0)
        current_level = member.get('member_grade', '普通会员')
        
        # 查询下一等级
        next_level = db.get_one("""
            SELECT level_code, level_name, min_growth
            FROM business_member_levels
            WHERE ec_id=%s AND project_id=%s AND min_growth > %s
            ORDER BY min_growth ASC LIMIT 1
        """, [ec_id, project_id, current_growth])
        
        if next_level and current_growth >= next_level['min_growth']:
            # 执行升级
            db.execute("""
                UPDATE business_members
                SET member_level=%s, member_grade=%s, updated_at=NOW()
                WHERE user_id=%s
            """, [next_level['level_code'], next_level['level_name'], user_id])
            
            logger.info(f"[GrowthTaskService] 用户 {user_id} 升级为 {next_level['level_name']}")
    
    # ============ 订单完成触发 ============
    
    def on_order_completed(self, user_id: int, order_id: int, 
                          order_amount: float, ec_id: int, project_id: int):
        """
        订单完成时调用，更新成长任务进度
        
        这是一个便捷方法，会同时处理：
        1. 订单计数任务
        2. 消费金额任务
        """
        # 增加订单计数
        return self.increment_task_progress(user_id, 'order', ec_id, project_id, 1)
        
        # 对于消费金额任务，直接检查并更新
        # 注意：这里简化处理，实际可能需要累计消费金额
    
    # ============ 签到触发 ============
    
    def on_checkin(self, user_id: int, ec_id: int, project_id: int):
        """用户签到时调用"""
        return self.increment_task_progress(user_id, 'checkin', ec_id, project_id, 1)
    
    # ============ 评价触发 ============
    
    def on_review(self, user_id: int, ec_id: int, project_id: int):
        """用户评价时调用"""
        return self.increment_task_progress(user_id, 'review', ec_id, project_id, 1)
    
    # ============ 分享触发 ============
    
    def on_share(self, user_id: int, ec_id: int, project_id: int):
        """用户分享时调用"""
        return self.increment_task_progress(user_id, 'share', ec_id, project_id, 1)



# 全局实例
growth_task_service = GrowthTaskService()
