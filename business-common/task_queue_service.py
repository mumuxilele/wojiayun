"""
异步任务队列服务 V33.0
功能:
  - 任务入队与调度
  - 任务执行与状态管理
  - 任务重试机制
  - 定时任务调度

依赖:
  - Redis (可选，用于分布式任务队列)
  - APScheduler (定时任务调度)
"""

import os
import sys
import json
import logging
import uuid
import time
import threading
import multiprocessing
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = 'pending'           # 等待执行
    RUNNING = 'running'          # 执行中
    COMPLETED = 'completed'      # 已完成
    FAILED = 'failed'            # 执行失败
    CANCELLED = 'cancelled'      # 已取消
    RETRYING = 'retrying'        # 重试中


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    URGENT = 20


class TaskQueueService(BaseService):
    """异步任务队列服务"""

    SERVICE_NAME = 'TaskQueueService'

    # 任务类型
    TASK_TYPES = {
        'notification': '批量发送通知',
        'order_batch': '批量处理订单',
        'analytics': '数据统计分析',
        'points_settle': '积分结算',
        'inventory_sync': '库存同步',
        'export': '数据导出',
        'cleanup': '数据清理',
        'invoice_generate': '发票生成',
        'backup': '数据备份',
        'custom': '自定义任务'
    }

    # 任务状态
    STATUS_PENDING = TaskStatus.PENDING
    STATUS_RUNNING = TaskStatus.RUNNING
    STATUS_COMPLETED = TaskStatus.COMPLETED
    STATUS_FAILED = TaskStatus.FAILED
    STATUS_CANCELLED = TaskStatus.CANCELLED
    STATUS_RETRYING = TaskStatus.RETRYING

    # 配置
    MAX_RETRIES = 3
    RETRY_DELAY = 60  # 重试延迟（秒）
    TASK_TIMEOUT = 3600  # 任务超时（秒）
    MAX_CONCURRENT_TASKS = 10  # 最大并发任务数

    # 任务处理器注册表
    _handlers = {}

    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            # 检查任务队列状态
            pending_count = db.get_total(
                "SELECT COUNT(*) FROM business_tasks WHERE status='pending' AND deleted=0"
            )
            running_count = db.get_total(
                "SELECT COUNT(*) FROM business_tasks WHERE status='running' AND deleted=0"
            )
            
            base['pending_tasks'] = pending_count
            base['running_tasks'] = running_count
            base['queue_healthy'] = True
        except Exception as e:
            base['error'] = str(e)
            base['queue_healthy'] = False
        return base

    # ============ 任务注册 ============

    @classmethod
    def register_handler(cls, task_type: str, handler: Callable):
        """
        注册任务处理器

        Args:
            task_type: 任务类型
            handler: 处理函数
        """
        cls._handlers[task_type] = handler
        logger.info(f"注册任务处理器: {task_type}")

    @classmethod
    def get_handler(cls, task_type: str) -> Optional[Callable]:
        """获取任务处理器"""
        return cls._handlers.get(task_type)

    # ============ 任务创建 ============

    def create_task(self, task_type: str, task_data: Dict,
                   priority: int = TaskPriority.NORMAL,
                   scheduled_at: datetime = None,
                   callback_url: str = None,
                   max_retries: int = None,
                   ec_id: int = None,
                   project_id: int = None,
                   created_by: str = None) -> Dict[str, Any]:
        """
        创建异步任务

        Args:
            task_type: 任务类型
            task_data: 任务数据
            priority: 优先级
            scheduled_at: 定时执行时间（可选）
            callback_url: 回调URL（可选）
            max_retries: 最大重试次数
            ec_id: 企业ID
            project_id: 项目ID
            created_by: 创建人

        Returns:
            Dict: 创建结果
        """
        try:
            # 生成任务ID
            task_id = self._generate_task_id()

            # 序列任务数据
            data_json = json.dumps(task_data, ensure_ascii=False, default=str)

            # 确定状态
            status = self.STATUS_PENDING
            if scheduled_at and scheduled_at > datetime.now():
                status = 'scheduled'

            # 执行插入
            sql = """
                INSERT INTO business_tasks
                (task_id, task_type, task_data, priority, status, scheduled_at,
                 callback_url, max_retries, retry_count, ec_id, project_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            db_id = db.execute(sql, (
                task_id, task_type, data_json, priority, status,
                scheduled_at, callback_url,
                max_retries or self.MAX_RETRIES, 0,
                ec_id, project_id, created_by
            ))

            logger.info(f"创建任务成功: task_id={task_id}, type={task_type}")

            return {
                'success': True,
                'msg': '任务创建成功',
                'task_id': task_id,
                'db_id': db_id
            }

        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return {'success': False, 'msg': f'创建失败: {str(e)}'}

    def create_batch_tasks(self, tasks: List[Dict]) -> Dict[str, Any]:
        """
        批量创建任务

        Args:
            tasks: 任务列表

        Returns:
            Dict: 创建结果
        """
        try:
            results = []
            for task_info in tasks:
                result = self.create_task(
                    task_type=task_info.get('task_type'),
                    task_data=task_info.get('task_data', {}),
                    priority=task_info.get('priority', TaskPriority.NORMAL),
                    ec_id=task_info.get('ec_id'),
                    project_id=task_info.get('project_id'),
                    created_by=task_info.get('created_by')
                )
                results.append(result)

            success_count = sum(1 for r in results if r['success'])
            
            return {
                'success': True,
                'msg': f'批量创建完成: {success_count}/{len(tasks)}',
                'results': results
            }

        except Exception as e:
            logger.error(f"批量创建任务失败: {e}")
            return {'success': False, 'msg': f'批量创建失败: {str(e)}'}

    # ============ 任务执行 ============

    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """
        执行指定任务

        Args:
            task_id: 任务ID

        Returns:
            Dict: 执行结果
        """
        try:
            # 获取任务
            task = self.get_task(task_id)
            if not task:
                return {'success': False, 'msg': '任务不存在'}

            # 检查任务状态
            if task['status'] not in [self.STATUS_PENDING, 'scheduled']:
                return {'success': False, 'msg': f"任务状态不允许执行: {task['status']}"}

            # 获取处理器
            handler = self.get_handler(task['task_type'])
            if not handler:
                return {'success': False, 'msg': f"未注册的任务处理器: {task['task_type']}"}

            # 更新状态为运行中
            self._update_task_status(task_id, self.STATUS_RUNNING)

            # 解析任务数据
            task_data = json.loads(task['task_data'])

            # 执行任务
            start_time = datetime.now()
            try:
                result = handler(task_data)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                # 判断执行结果
                if result.get('success', True):
                    self._complete_task(task_id, result, duration)
                    return {
                        'success': True,
                        'msg': '任务执行成功',
                        'result': result,
                        'duration': duration
                    }
                else:
                    self._fail_task(task_id, result.get('msg', '任务执行失败'), result)
                    return {
                        'success': False,
                        'msg': result.get('msg', '任务执行失败'),
                        'result': result
                    }

            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                self._fail_task(task_id, str(e), None)
                return {'success': False, 'msg': f'任务执行异常: {str(e)}'}

        except Exception as e:
            logger.error(f"执行任务失败: {e}")
            return {'success': False, 'msg': f'执行失败: {str(e)}'}

    def execute_next_task(self, worker_id: str = None) -> Dict[str, Any]:
        """
        执行下一个待处理任务

        Args:
            worker_id: 工作进程ID

        Returns:
            Dict: 执行结果
        """
        try:
            # 查询待执行任务
            sql = """
                SELECT * FROM business_tasks
                WHERE status IN ('pending', 'scheduled') AND deleted=0
                AND (scheduled_at IS NULL OR scheduled_at <= NOW())
                ORDER BY priority DESC, created_at ASC
                LIMIT 1 FOR UPDATE SKIP LOCKED
            """
            
            task = db.get_one(sql)
            if not task:
                return {'success': False, 'msg': '没有待执行任务', 'code': 'NO_TASK'}

            # 更新任务状态
            db.execute("""
                UPDATE business_tasks
                SET status=%s, worker_id=%s, started_at=NOW(), updated_at=NOW()
                WHERE id=%s
            """, [self.STATUS_RUNNING, worker_id, task['id']])

            # 执行任务
            return self.execute_task(task['task_id'])

        except Exception as e:
            logger.error(f"执行下一个任务失败: {e}")
            return {'success': False, 'msg': f'执行失败: {str(e)}'}

    # ============ 任务管理 ============

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            Dict: 任务详情
        """
        try:
            return db.get_one(
                "SELECT * FROM business_tasks WHERE task_id=%s AND deleted=0",
                [task_id]
            )
        except Exception as e:
            logger.error(f"获取任务详情失败: {e}")
            return None

    def list_tasks(self, task_type: str = None, status: str = None,
                  ec_id: int = None, project_id: int = None,
                  created_by: str = None, page: int = 1, page_size: int = 20) -> Dict:
        """
        获取任务列表

        Args:
            task_type: 任务类型
            status: 任务状态
            ec_id: 企业ID
            project_id: 项目ID
            created_by: 创建人
            page: 页码
            page_size: 每页数量

        Returns:
            Dict: 分页结果
        """
        try:
            where_clauses = ["deleted=0"]
            params = []

            if task_type:
                where_clauses.append("task_type=%s")
                params.append(task_type)

            if status:
                where_clauses.append("status=%s")
                params.append(status)

            if ec_id:
                where_clauses.append("ec_id=%s")
                params.append(ec_id)

            if project_id:
                where_clauses.append("project_id=%s")
                params.append(project_id)

            if created_by:
                where_clauses.append("created_by=%s")
                params.append(created_by)

            where_sql = " AND ".join(where_clauses)

            # 统计总数
            total = db.get_total(f"SELECT COUNT(*) FROM business_tasks WHERE {where_sql}", params)

            # 分页查询
            offset = (page - 1) * page_size
            sql = f"""
                SELECT * FROM business_tasks
                WHERE {where_sql}
                ORDER BY priority DESC, created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])

            items = db.get_all(sql, params) or []

            return {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size if total else 0
            }

        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            Dict: 取消结果
        """
        try:
            task = self.get_task(task_id)
            if not task:
                return {'success': False, 'msg': '任务不存在'}

            if task['status'] in [self.STATUS_COMPLETED, self.STATUS_CANCELLED]:
                return {'success': False, 'msg': f"任务状态不允许取消: {task['status']}"}

            db.execute("""
                UPDATE business_tasks
                SET status=%s, updated_at=NOW()
                WHERE task_id=%s
            """, [self.STATUS_CANCELLED, task_id])

            logger.info(f"取消任务: {task_id}")

            return {'success': True, 'msg': '任务已取消'}

        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return {'success': False, 'msg': f'取消失败: {str(e)}'}

    def retry_task(self, task_id: str) -> Dict[str, Any]:
        """
        重试任务

        Args:
            task_id: 任务ID

        Returns:
            Dict: 重试结果
        """
        try:
            task = self.get_task(task_id)
            if not task:
                return {'success': False, 'msg': '任务不存在'}

            if task['status'] not in [self.STATUS_FAILED]:
                return {'success': False, 'msg': '只能重试失败的任务'}

            retry_count = task.get('retry_count', 0)
            max_retries = task.get('max_retries', self.MAX_RETRIES)

            if retry_count >= max_retries:
                return {'success': False, 'msg': f"已超过最大重试次数 ({max_retries})"}

            # 更新重试次数
            db.execute("""
                UPDATE business_tasks
                SET status=%s, retry_count=%s, error_message=NULL, updated_at=NOW()
                WHERE task_id=%s
            """, [self.STATUS_PENDING, retry_count + 1, task_id])

            logger.info(f"重试任务: {task_id}, retry_count={retry_count + 1}")

            return {'success': True, 'msg': '任务已加入重试队列'}

        except Exception as e:
            logger.error(f"重试任务失败: {e}")
            return {'success': False, 'msg': f'重试失败: {str(e)}'}

    def get_task_statistics(self, ec_id: int = None, project_id: int = None) -> Dict:
        """
        获取任务统计

        Args:
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            Dict: 统计数据
        """
        try:
            where_clauses = ["deleted=0"]
            params = []

            if ec_id:
                where_clauses.append("ec_id=%s")
                params.append(ec_id)

            if project_id:
                where_clauses.append("project_id=%s")
                params.append(project_id)

            where_sql = " AND ".join(where_clauses)

            # 按状态统计
            status_stats = db.get_all(f"""
                SELECT status, COUNT(*) as count
                FROM business_tasks
                WHERE {where_sql}
                GROUP BY status
            """, params)

            # 按类型统计
            type_stats = db.get_all(f"""
                SELECT task_type, COUNT(*) as count,
                       SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as success_count,
                       SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed_count
                FROM business_tasks
                WHERE {where_sql}
                GROUP BY task_type
            """, params)

            # 计算平均执行时间
            avg_duration = db.get_one(f"""
                SELECT AVG(TIMESTAMPDIFF(SECOND, started_at, completed_at)) as avg_duration
                FROM business_tasks
                WHERE {where_sql} AND status='completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
            """, params)

            return {
                'by_status': {s['status']: s['count'] for s in status_stats},
                'by_type': [{
                    'task_type': s['task_type'],
                    'total': s['count'],
                    'success': s['success_count'],
                    'failed': s['failed_count']
                } for s in type_stats],
                'avg_duration_seconds': avg_duration.get('avg_duration') if avg_duration else 0
            }

        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}

    # ============ 定时任务 ============

    def schedule_task(self, task_type: str, task_data: Dict,
                    cron_expr: str = None, interval_seconds: int = None,
                    **kwargs) -> Dict[str, Any]:
        """
        创建定时任务

        Args:
            task_type: 任务类型
            task_data: 任务数据
            cron_expr: Cron表达式
            interval_seconds: 间隔秒数
            **kwargs: 其他参数

        Returns:
            Dict: 创建结果
        """
        try:
            # 计算下次执行时间
            scheduled_at = None
            if interval_seconds:
                scheduled_at = datetime.now() + timedelta(seconds=interval_seconds)
            elif cron_expr:
                scheduled_at = self._parse_cron(cron_expr)

            return self.create_task(
                task_type=task_type,
                task_data=task_data,
                scheduled_at=scheduled_at,
                **kwargs
            )

        except Exception as e:
            logger.error(f"创建定时任务失败: {e}")
            return {'success': False, 'msg': f'创建失败: {str(e)}'}

    def _parse_cron(self, cron_expr: str) -> datetime:
        """解析Cron表达式（简化版）"""
        # 简化实现：仅支持 daily/hourly/minutely
        parts = cron_expr.split()
        if 'daily' in cron_expr:
            return datetime.now().replace(hour=2, minute=0, second=0) + timedelta(days=1)
        elif 'hourly' in cron_expr:
            return datetime.now() + timedelta(hours=1)
        elif 'minutely' in cron_expr:
            return datetime.now() + timedelta(minutes=1)
        return datetime.now()

    # ============ 内部方法 ============

    def _generate_task_id(self) -> str:
        """生成任务ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique = uuid.uuid4().hex[:8].upper()
        return f"TK{timestamp}{unique}"

    def _update_task_status(self, task_id: str, status: str):
        """更新任务状态"""
        db.execute("""
            UPDATE business_tasks
            SET status=%s, updated_at=NOW()
            WHERE task_id=%s
        """, [status, task_id])

    def _complete_task(self, task_id: str, result: Dict, duration: float):
        """完成任务"""
        result_json = json.dumps(result, ensure_ascii=False, default=str)
        db.execute("""
            UPDATE business_tasks
            SET status=%s, result=%s, duration=%s, completed_at=NOW(), updated_at=NOW()
            WHERE task_id=%s
        """, [self.STATUS_COMPLETED, result_json, duration, task_id])

    def _fail_task(self, task_id: str, error_message: str, result: Dict = None):
        """标记任务失败"""
        task = self.get_task(task_id)
        if not task:
            return

        retry_count = task.get('retry_count', 0)
        max_retries = task.get('max_retries', self.MAX_RETRIES)

        if retry_count < max_retries:
            # 需要重试
            new_status = self.STATUS_PENDING
            retry_count += 1
            logger.info(f"任务失败准备重试: {task_id}, retry={retry_count}")
        else:
            # 超过最大重试次数
            new_status = self.STATUS_FAILED

        result_json = json.dumps(result, ensure_ascii=False, default=str) if result else None
        
        db.execute("""
            UPDATE business_tasks
            SET status=%s, error_message=%s, result=%s, retry_count=%s, updated_at=NOW()
            WHERE task_id=%s
        """, [new_status, error_message, result_json, retry_count, task_id])


# 单例实例
task_queue_service = TaskQueueService()
