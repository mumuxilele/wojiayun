#!/usr/bin/env python3
"""
V44.0 数据库迁移脚本
主要变更:
1. 新增大厦门禁卡申请类型
2. 新增监控调取审计日志表
3. 新增系统联动记录表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db


def migrate():
    """执行迁移"""
    print("开始 V44.0 数据库迁移...")

    # 1. 新增大厦门禁卡申请类型
    add_access_card_application_type()

    # 2. 创建监控调取审计日志表
    create_monitor_query_logs_table()

    # 3. 创建系统联动记录表
    create_system_linkage_logs_table()

    print("V44.0 数据库迁移完成!")


def add_access_card_application_type():
    """新增大厦门禁卡申请类型"""
    print("新增大厦门禁卡申请类型...")

    # 检查是否已存在
    check = db.get_one(
        "SELECT id FROM business_application_types WHERE type_code='access_card'"
    )

    if check:
        print("  大厦门禁卡申请类型已存在，跳过")
        return

    # 表单配置
    form_schema = {
        'fields': [
            {'name': 'applicant_name', 'label': '申请人姓名', 'type': 'text', 'required': True, 'placeholder': '请输入申请人姓名'},
            {'name': 'applicant_phone', 'label': '申请人电话', 'type': 'text', 'required': True, 'placeholder': '请输入联系电话'},
            {'name': 'department', 'label': '所属部门', 'type': 'text', 'required': True, 'placeholder': '请输入所属部门'},
            {'name': 'position', 'label': '职位', 'type': 'text', 'required': False, 'placeholder': '请输入职位'},
            {'name': 'card_type', 'label': '门禁卡类型', 'type': 'select', 'required': True,
             'options': [
                 {'value': 'employee', 'label': '员工卡'},
                 {'value': 'visitor', 'label': '访客卡'},
                 {'value': 'temporary', 'label': '临时卡'},
             ]},
            {'name': 'area_ids', 'label': '权限范围', 'type': 'multi_select', 'required': True,
             'options': [
                 {'value': 'main_entrance', 'label': '大厦主入口'},
                 {'value': 'office_floor', 'label': '办公楼层'},
                 {'value': 'parking', 'label': '停车场'},
                 {'value': 'gym', 'label': '健身房'},
                 {'value': 'cafeteria', 'label': '餐厅'},
             ]},
            {'name': 'valid_from', 'label': '生效日期', 'type': 'date', 'required': True},
            {'name': 'valid_to', 'label': '失效日期', 'type': 'date', 'required': True},
            {'name': 'reason', 'label': '申请原因', 'type': 'textarea', 'required': True, 'placeholder': '请说明申请原因'},
            {'name': 'remark', 'label': '备注', 'type': 'textarea', 'required': False, 'placeholder': '其他需要说明的事项'},
        ]
    }

    # 审批流程配置
    approve_flow = {
        'steps': 1,
        'nodes': [
            {'step': 1, 'name': '物业审批', 'role': 'property_manager', 'timeout_hours': 24}
        ],
        'auto_action': {
            'type': 'grant_access',
            'description': '审批通过后自动下发门禁权限'
        }
    }

    db.execute(
        """INSERT INTO business_application_types
           (type_code, type_name, category, icon, description, form_schema, approve_flow,
            require_attachment, max_attachment, need_remind, remind_before_hours, sort_order, is_active)
           VALUES ('access_card', '大厦门禁卡申请', 'property', 'id-card',
                   '申请大厦门禁卡，审批通过后系统自动下发门禁权限',
                   %s, %s, 0, 0, 0, 0, 9, 1)""",
        [json.dumps(form_schema, ensure_ascii=False), json.dumps(approve_flow, ensure_ascii=False)]
    )

    print("  大厦门禁卡申请类型创建成功")


def create_monitor_query_logs_table():
    """创建监控调取审计日志表"""
    print("创建 business_monitor_query_logs 表...")

    # 检查表是否存在
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_monitor_query_logs'
    """)

    if check and check['cnt'] > 0:
        print("  business_monitor_query_logs 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_monitor_query_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            query_type VARCHAR(50) DEFAULT 'monitor_query' COMMENT '查询类型',
            app_no VARCHAR(50) COMMENT '关联申请单号',
            camera_ids JSON COMMENT '摄像头ID列表',
            time_range JSON COMMENT '时间范围',
            reason TEXT COMMENT '调取原因',
            operator_id INT COMMENT '操作人ID',
            operator_name VARCHAR(50) COMMENT '操作人姓名',
            operator_phone VARCHAR(20) COMMENT '操作人电话',
            query_time DATETIME COMMENT '调取时间',
            result_status VARCHAR(20) DEFAULT 'success' COMMENT '调取结果',
            result_msg TEXT COMMENT '结果说明',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_app_no (app_no),
            INDEX idx_operator (operator_id),
            INDEX idx_query_time (query_time),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='监控录像调取审计日志表'
    """)

    print("  business_monitor_query_logs 表创建成功")


def create_system_linkage_logs_table():
    """创建系统联动记录表"""
    print("创建 business_system_linkage_logs 表...")

    # 检查表是否存在
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_system_linkage_logs'
    """)

    if check and check['cnt'] > 0:
        print("  business_system_linkage_logs 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_system_linkage_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            linkage_type VARCHAR(50) NOT NULL COMMENT '联动类型: access_control/lift_control/hvac_control',
            app_no VARCHAR(50) COMMENT '关联申请单号',
            action VARCHAR(50) NOT NULL COMMENT '操作类型: grant/revoke/reserve/cancel',
            target_id VARCHAR(100) COMMENT '目标ID（权限ID/预约ID等）',
            request_data JSON COMMENT '请求数据',
            response_data JSON COMMENT '响应数据',
            status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/success/failed',
            error_msg TEXT COMMENT '错误信息',
            user_id INT COMMENT '用户ID',
            user_name VARCHAR(50) COMMENT '用户姓名',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            executed_at DATETIME COMMENT '执行时间',
            INDEX idx_linkage_type (linkage_type),
            INDEX idx_app_no (app_no),
            INDEX idx_status (status),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统联动记录表'
    """)

    print("  business_system_linkage_logs 表创建成功")


def rollback():
    """回滚迁移"""
    print("开始回滚 V44.0 数据库迁移...")

    try:
        # 删除大厦门禁卡申请类型
        db.execute("DELETE FROM business_application_types WHERE type_code='access_card'")
        print("  大厦门禁卡申请类型已删除")

        # 删除表
        db.execute("DROP TABLE IF EXISTS business_system_linkage_logs")
        print("  business_system_linkage_logs 表已删除")

        db.execute("DROP TABLE IF EXISTS business_monitor_query_logs")
        print("  business_monitor_query_logs 表已删除")

        print("V44.0 回滚完成!")
    except Exception as e:
        print(f"回滚失败: {e}")


if __name__ == '__main__':
    import json
    if '--rollback' in sys.argv:
        rollback()
    else:
        migrate()