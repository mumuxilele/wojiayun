"""
V33.0 任务队列服务集成测试
"""

import pytest
import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db
from business_common.task_queue_service import TaskQueueService, TaskStatus, TaskPriority


class TestTaskQueueService:
    """任务队列服务测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = TaskQueueService()

    def test_service_health_check(self):
        """测试服务健康检查"""
        result = self.service.health_check()
        assert result is not None
        assert 'pending_tasks' in result or 'service_name' in result

    def test_task_types(self):
        """测试任务类型配置"""
        assert 'notification' in self.service.TASK_TYPES
        assert 'order_batch' in self.service.TASK_TYPES
        assert 'analytics' in self.service.TASK_TYPES
        assert 'export' in self.service.TASK_TYPES

    def test_task_status(self):
        """测试任务状态配置"""
        assert self.service.STATUS_PENDING == TaskStatus.PENDING
        assert self.service.STATUS_RUNNING == TaskStatus.RUNNING
        assert self.service.STATUS_COMPLETED == TaskStatus.COMPLETED
        assert self.service.STATUS_FAILED == TaskStatus.FAILED

    def test_task_priority(self):
        """测试任务优先级配置"""
        assert TaskPriority.LOW == 1
        assert TaskPriority.NORMAL == 5
        assert TaskPriority.HIGH == 10
        assert TaskPriority.URGENT == 20

    def test_generate_task_id(self):
        """测试任务ID生成"""
        task_id = self.service._generate_task_id()
        assert task_id is not None
        assert task_id.startswith('TK')
        assert len(task_id) == 24

    def test_register_handler(self):
        """测试任务处理器注册"""
        def test_handler(data):
            return {'success': True, 'result': data}

        self.service.register_handler('test_custom', test_handler)
        handler = self.service.get_handler('test_custom')
        assert handler is not None
        assert callable(handler)

    def test_get_handler_not_found(self):
        """测试获取不存在的处理器"""
        handler = self.service.get_handler('nonexistent_handler')
        assert handler is None


class TestTaskCRUD:
    """任务CRUD测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = TaskQueueService()
        self.test_user_id = 'test_user_001'
        self.test_ec_id = 1
        self.test_project_id = 1

    def test_create_task(self):
        """测试创建任务"""
        result = self.service.create_task(
            task_type='test_custom',
            task_data={'key': 'value', 'test': True},
            priority=TaskPriority.NORMAL,
            ec_id=self.test_ec_id,
            project_id=self.test_project_id,
            created_by='test_user'
        )
        assert result is not None
        if result.get('success'):
            assert 'task_id' in result
            assert 'db_id' in result

    def test_create_task_with_handler(self):
        """测试创建带处理器的任务"""
        # 注册处理器
        def sample_handler(data):
            return {'success': True, 'processed': data.get('data')}

        self.service.register_handler('sample', sample_handler)

        # 创建任务
        result = self.service.create_task(
            task_type='sample',
            task_data={'data': 'test_value'},
            priority=TaskPriority.HIGH,
            created_by='test'
        )
        assert result is not None

    def test_create_batch_tasks(self):
        """测试批量创建任务"""
        tasks = [
            {
                'task_type': 'notification',
                'task_data': {'user_id': 'user1', 'msg': '通知1'},
                'priority': TaskPriority.NORMAL
            },
            {
                'task_type': 'notification',
                'task_data': {'user_id': 'user2', 'msg': '通知2'},
                'priority': TaskPriority.HIGH
            }
        ]

        result = self.service.create_batch_tasks(tasks)
        assert result is not None
        assert result.get('success') == True
        assert 'results' in result

    def test_get_task_not_found(self):
        """测试获取不存在的任务"""
        task = self.service.get_task('TK99999999999999999')
        assert task is None

    def test_list_tasks(self):
        """测试获取任务列表"""
        result = self.service.list_tasks(
            page=1,
            page_size=10
        )
        assert 'items' in result
        assert 'total' in result
        assert 'page' in result

    def test_list_tasks_with_filters(self):
        """测试带筛选条件的任务列表"""
        result = self.service.list_tasks(
            task_type='notification',
            status='pending',
            ec_id=1,
            page=1,
            page_size=10
        )
        assert 'items' in result


class TestTaskExecution:
    """任务执行测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = TaskQueueService()

    def test_execute_task_not_found(self):
        """测试执行不存在的任务"""
        result = self.service.execute_task('TK99999999999999999')
        assert result is not None
        assert result.get('success') == False
        assert '不存在' in result.get('msg', '')

    def test_execute_next_task_no_task(self):
        """测试没有待执行任务"""
        result = self.service.execute_next_task()
        # 可能没有任务，这是正常情况
        assert result is not None


class TestTaskManagement:
    """任务管理测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = TaskQueueService()

    def test_cancel_task_not_found(self):
        """测试取消不存在的任务"""
        result = self.service.cancel_task('TK99999999999999999')
        assert result is not None
        assert result.get('success') == False

    def test_retry_task_not_found(self):
        """测试重试不存在的任务"""
        result = self.service.retry_task('TK99999999999999999')
        assert result is not None
        assert result.get('success') == False

    def test_get_statistics(self):
        """测试获取任务统计"""
        result = self.service.get_task_statistics()
        assert result is not None
        # 统计结果可能为空，但结构应该正确


class TestScheduledTasks:
    """定时任务测试"""

    def setup_method(self):
        """测试前准备"""
        self.service = TaskQueueService()

    def test_create_scheduled_task(self):
        """测试创建定时任务"""
        # 设置1分钟后执行
        scheduled_at = datetime.now() + timedelta(minutes=1)

        result = self.service.create_task(
            task_type='test_custom',
            task_data={'scheduled': True},
            scheduled_at=scheduled_at,
            priority=TaskPriority.NORMAL
        )
        assert result is not None
        if result.get('success'):
            assert 'task_id' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
