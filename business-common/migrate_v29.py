#!/usr/bin/env python3
"""
V29.0 申请审批系统数据库迁移
功能：扩展申请系统，支持8种业务申请类型
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db

MIGRATIONS = [
    # 1. 扩展申请表单字段，支持JSON格式业务数据
    """
    ALTER TABLE business_applications 
    ADD COLUMN IF NOT EXISTS form_data JSON COMMENT '表单业务数据JSON',
    ADD COLUMN IF NOT EXISTS approve_flow JSON COMMENT '审批流程配置JSON',
    ADD COLUMN IF NOT EXISTS current_step INT DEFAULT 0 COMMENT '当前审批步骤',
    ADD COLUMN IF NOT EXISTS total_steps INT DEFAULT 1 COMMENT '总审批步骤数',
    ADD COLUMN IF NOT EXISTS approver_id BIGINT DEFAULT NULL COMMENT '当前审批人ID',
    ADD COLUMN IF NOT EXISTS approver_name VARCHAR(50) DEFAULT '' COMMENT '当前审批人姓名',
    ADD COLUMN IF NOT EXISTS approve_remark TEXT COMMENT '审批备注',
    ADD COLUMN IF NOT EXISTS approve_history JSON COMMENT '审批历史记录JSON',
    ADD COLUMN IF NOT EXISTS expire_time DATETIME DEFAULT NULL COMMENT '到期提醒时间',
    ADD COLUMN IF NOT EXISTS is_favorite TINYINT DEFAULT 0 COMMENT '是否常用申请',
    ADD COLUMN IF NOT EXISTS related_order_no VARCHAR(50) DEFAULT '' COMMENT '关联工单号';
    """,

    # 2. 申请类型配置表
    """
    CREATE TABLE IF NOT EXISTS business_application_types (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        type_code VARCHAR(50) NOT NULL UNIQUE COMMENT '申请类型代码',
        type_name VARCHAR(100) NOT NULL COMMENT '申请类型名称',
        category VARCHAR(50) DEFAULT '' COMMENT '分类',
        icon VARCHAR(50) DEFAULT '' COMMENT '图标',
        description TEXT COMMENT '说明',
        form_schema JSON COMMENT '表单字段配置JSON',
        approve_flow JSON COMMENT '默认审批流程配置',
        require_attachment TINYINT DEFAULT 0 COMMENT '是否需要附件',
        max_attachment INT DEFAULT 5 COMMENT '最大附件数量',
        need_remind TINYINT DEFAULT 0 COMMENT '是否需要到期提醒',
        remind_before_hours INT DEFAULT 24 COMMENT '提前提醒小时数',
        sort_order INT DEFAULT 0 COMMENT '排序',
        is_active TINYINT DEFAULT 1 COMMENT '是否启用',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_active_category (is_active, category),
        INDEX idx_sort_order (sort_order)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='申请类型配置表';
    """,

    # 3. 审批节点配置表
    """
    CREATE TABLE IF NOT EXISTS business_approve_nodes (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        node_code VARCHAR(50) NOT NULL COMMENT '节点代码',
        node_name VARCHAR(100) NOT NULL COMMENT '节点名称',
        app_type VARCHAR(50) NOT NULL COMMENT '申请类型',
        step_order INT DEFAULT 1 COMMENT '步骤顺序',
        approver_type ENUM('user', 'role', 'dept') DEFAULT 'user' COMMENT '审批人类型',
        approver_id BIGINT DEFAULT NULL COMMENT '审批人ID',
        approver_role VARCHAR(50) DEFAULT '' COMMENT '审批角色',
        approver_dept VARCHAR(50) DEFAULT '' COMMENT '审批部门',
        auto_pass TINYINT DEFAULT 0 COMMENT '是否自动通过',
        auto_pass_hours INT DEFAULT 24 COMMENT '自动通过小时数',
        need_sign TINYINT DEFAULT 1 COMMENT '是否需要签字',
        can_transfer TINYINT DEFAULT 1 COMMENT '是否允许转交',
        transfer_to BIGINT DEFAULT NULL COMMENT '转交人ID',
        is_active TINYINT DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_app_type_step (app_type, step_order),
        INDEX idx_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审批节点配置表';
    """,

    # 4. 申请附件表
    """
    CREATE TABLE IF NOT EXISTS business_application_attachments (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        app_id BIGINT NOT NULL COMMENT '申请ID',
        file_name VARCHAR(200) NOT NULL COMMENT '文件名',
        file_url TEXT NOT NULL COMMENT '文件URL',
        file_size INT DEFAULT 0 COMMENT '文件大小(字节)',
        file_type VARCHAR(50) DEFAULT '' COMMENT '文件类型',
        uploaded_by BIGINT DEFAULT NULL COMMENT '上传人ID',
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_app_id (app_id),
        INDEX idx_uploaded_at (uploaded_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='申请附件表';
    """,

    # 5. 提醒记录表
    """
    CREATE TABLE IF NOT EXISTS business_application_reminds (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        app_id BIGINT NOT NULL COMMENT '申请ID',
        remind_type VARCHAR(30) NOT NULL COMMENT '提醒类型: expire-到期, approve-审批',
        remind_time DATETIME NOT NULL COMMENT '提醒时间',
        remind_content TEXT COMMENT '提醒内容',
        is_sent TINYINT DEFAULT 0 COMMENT '是否已发送',
        sent_at DATETIME DEFAULT NULL COMMENT '发送时间',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_app_id (app_id),
        INDEX idx_remind_time (remind_time, is_sent)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='申请提醒记录表';
    """,
]

def init_application_types():
    """初始化申请类型配置"""
    types = [
        {
            'type_code': 'overtime',
            'type_name': '加班申请',
            'category': '物业申请',
            'icon': '🌙',
            'description': '申请加班使用办公区域',
            'form_schema': {
                'fields': [
                    {'name': 'overtime_date', 'label': '加班日期', 'type': 'date', 'required': True},
                    {'name': 'start_time', 'label': '开始时间', 'type': 'time', 'required': True},
                    {'name': 'end_time', 'label': '结束时间', 'type': 'time', 'required': True},
                    {'name': 'area', 'label': '加班区域', 'type': 'select', 'required': True, 
                     'options': ['A座办公区', 'B座办公区', 'C座办公区', '会议室']},
                    {'name': 'people_count', 'label': '加班人数', 'type': 'number', 'required': True, 'min': 1, 'max': 100},
                    {'name': 'reason', 'label': '加班事由', 'type': 'textarea', 'required': True, 'max': 500}
                ]
            },
            'approve_flow': {'steps': 1, 'nodes': [{'step': 1, 'name': '物业审批', 'role': 'property_manager'}]},
            'need_remind': 0,
            'sort_order': 1
        },
        {
            'type_code': 'chair_placement',
            'type_name': '候餐椅临时摆放申请',
            'category': '物业申请',
            'icon': '🪑',
            'description': '申请临时摆放候餐椅',
            'form_schema': {
                'fields': [
                    {'name': 'placement_area', 'label': '摆放区域', 'type': 'select', 'required': True,
                     'options': ['大堂休息区', '走廊通道', '露台区域', '其他']},
                    {'name': 'start_date', 'label': '开始日期', 'type': 'date', 'required': True},
                    {'name': 'end_date', 'label': '结束日期', 'type': 'date', 'required': True},
                    {'name': 'chair_count', 'label': '椅子数量', 'type': 'number', 'required': True, 'min': 1, 'max': 50},
                    {'name': 'contact_name', 'label': '联系人', 'type': 'text', 'required': True},
                    {'name': 'contact_phone', 'label': '联系电话', 'type': 'tel', 'required': True}
                ]
            },
            'approve_flow': {'steps': 1, 'nodes': [{'step': 1, 'name': '物业审批', 'role': 'property_manager'}]},
            'need_remind': 1,
            'remind_before_hours': 24,
            'sort_order': 2
        },
        {
            'type_code': 'key_return',
            'type_name': '备用钥匙回收申请',
            'category': '物业申请',
            'icon': '🔑',
            'description': '申请回收备用钥匙',
            'form_schema': {
                'fields': [
                    {'name': 'key_type', 'label': '钥匙类型', 'type': 'select', 'required': True,
                     'options': ['办公室钥匙', '会议室钥匙', '仓库钥匙', '其他']},
                    {'name': 'key_no', 'label': '钥匙编号', 'type': 'text', 'required': True},
                    {'name': 'return_date', 'label': '归还日期', 'type': 'date', 'required': True},
                    {'name': 'return_reason', 'label': '归还原因', 'type': 'textarea', 'required': True, 'max': 300},
                    {'name': 'remark', 'label': '备注', 'type': 'textarea', 'required': False, 'max': 200}
                ]
            },
            'approve_flow': {'steps': 1, 'nodes': [{'step': 1, 'name': '物业确认', 'role': 'property_manager'}]},
            'need_remind': 0,
            'sort_order': 3
        },
        {
            'type_code': 'tenant_activity',
            'type_name': '租户活动申请',
            'category': '活动申请',
            'icon': '🎉',
            'description': '申请举办租户活动',
            'form_schema': {
                'fields': [
                    {'name': 'activity_name', 'label': '活动名称', 'type': 'text', 'required': True},
                    {'name': 'activity_area', 'label': '活动区域', 'type': 'select', 'required': True,
                     'options': ['大堂', '中庭', '会议室A', '会议室B', '户外广场']},
                    {'name': 'activity_date', 'label': '活动日期', 'type': 'date', 'required': True},
                    {'name': 'start_time', 'label': '开始时间', 'type': 'time', 'required': True},
                    {'name': 'end_time', 'label': '结束时间', 'type': 'time', 'required': True},
                    {'name': 'content', 'label': '活动内容', 'type': 'textarea', 'required': True, 'max': 1000},
                    {'name': 'setup_require', 'label': '布置要求', 'type': 'textarea', 'required': True, 'max': 500},
                    {'name': 'people_count', 'label': '预计人数', 'type': 'number', 'required': True, 'min': 1, 'max': 500},
                    {'name': 'need_power', 'label': '是否需要用电', 'type': 'radio', 'required': True,
                     'options': [{'value': '1', 'label': '是'}, {'value': '0', 'label': '否'}]},
                    {'name': 'need_security', 'label': '是否需要安保', 'type': 'radio', 'required': True,
                     'options': [{'value': '1', 'label': '是'}, {'value': '0', 'label': '否'}]}
                ]
            },
            'approve_flow': {
                'steps': 2, 
                'nodes': [
                    {'step': 1, 'name': '物业初审', 'role': 'property_manager'},
                    {'step': 2, 'name': '运营终审', 'role': 'operation_manager'}
                ]
            },
            'need_remind': 0,
            'sort_order': 4
        },
        {
            'type_code': 'monitor_query',
            'type_name': '监控录像调用申请',
            'category': '物业申请',
            'icon': '📹',
            'description': '申请调取监控录像',
            'form_schema': {
                'fields': [
                    {'name': 'query_date', 'label': '查询日期', 'type': 'date', 'required': True},
                    {'name': 'start_time', 'label': '开始时间', 'type': 'time', 'required': True},
                    {'name': 'end_time', 'label': '结束时间', 'type': 'time', 'required': True},
                    {'name': 'monitor_point', 'label': '监控点位', 'type': 'select', 'required': True,
                     'options': ['大堂入口', '电梯厅', '走廊A区', '走廊B区', '停车场', '其他']},
                    {'name': 'query_reason', 'label': '查询原因', 'type': 'textarea', 'required': True, 'max': 500},
                    {'name': 'incident_desc', 'label': '事件描述', 'type': 'textarea', 'required': False, 'max': 1000}
                ]
            },
            'approve_flow': {'steps': 1, 'nodes': [{'step': 1, 'name': '物业审批', 'role': 'security_manager'}]},
            'need_remind': 0,
            'sort_order': 5
        },
        {
            'type_code': 'hvac_overtime',
            'type_name': '加时鲜风供应申请',
            'category': '设备申请',
            'icon': '❄️',
            'description': '申请延长空调/新风供应时间',
            'form_schema': {
                'fields': [
                    {'name': 'supply_date', 'label': '供应日期', 'type': 'date', 'required': True},
                    {'name': 'start_time', 'label': '开始时间', 'type': 'time', 'required': True},
                    {'name': 'end_time', 'label': '结束时间', 'type': 'time', 'required': True},
                    {'name': 'area', 'label': '供应区域', 'type': 'select', 'required': True,
                     'options': ['整层A区', '整层B区', '整层C区', '独立办公室']},
                    {'name': 'area_size', 'label': '面积(㎡)', 'type': 'number', 'required': True, 'min': 10},
                    {'name': 'people_count', 'label': '使用人数', 'type': 'number', 'required': True, 'min': 1},
                    {'name': 'reason', 'label': '申请原因', 'type': 'textarea', 'required': True, 'max': 300}
                ]
            },
            'approve_flow': {'steps': 1, 'nodes': [{'step': 1, 'name': '工程部审批', 'role': 'engineering_manager'}]},
            'need_remind': 0,
            'sort_order': 6
        },
        {
            'type_code': 'cargo_lift',
            'type_name': '货梯使用预约申请',
            'category': '设备申请',
            'icon': '🛗',
            'description': '预约使用货梯搬运货物',
            'form_schema': {
                'fields': [
                    {'name': 'lift_no', 'label': '货梯编号', 'type': 'select', 'required': True,
                     'options': ['货梯1号', '货梯2号', '货梯3号']},
                    {'name': 'use_date', 'label': '使用日期', 'type': 'date', 'required': True},
                    {'name': 'start_time', 'label': '开始时间', 'type': 'time', 'required': True},
                    {'name': 'end_time', 'label': '结束时间', 'type': 'time', 'required': True},
                    {'name': 'from_floor', 'label': '起始楼层', 'type': 'select', 'required': True,
                     'options': ['B2', 'B1', '1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F']},
                    {'name': 'to_floor', 'label': '目的楼层', 'type': 'select', 'required': True,
                     'options': ['B2', 'B1', '1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F']},
                    {'name': 'cargo_desc', 'label': '货物描述', 'type': 'textarea', 'required': True, 'max': 300},
                    {'name': 'cargo_weight', 'label': '货物重量(kg)', 'type': 'number', 'required': True, 'min': 1, 'max': 2000},
                    {'name': 'purpose', 'label': '使用目的', 'type': 'select', 'required': True,
                     'options': ['搬家', '设备搬运', '材料运输', '货物配送', '其他']}
                ]
            },
            'approve_flow': {'steps': 1, 'nodes': [{'step': 1, 'name': '物业审批', 'role': 'property_manager'}]},
            'need_remind': 1,
            'remind_before_hours': 2,
            'sort_order': 7
        },
        {
            'type_code': 'signage_print',
            'type_name': '指示牌印制申请',
            'category': '物业申请',
            'icon': '📋',
            'description': '申请印制大厦租户指示牌',
            'form_schema': {
                'fields': [
                    {'name': 'content', 'label': '指示内容', 'type': 'text', 'required': True},
                    {'name': 'spec', 'label': '规格尺寸', 'type': 'select', 'required': True,
                     'options': ['30x20cm', '40x30cm', '60x40cm', '其他']},
                    {'name': 'quantity', 'label': '数量', 'type': 'number', 'required': True, 'min': 1, 'max': 20},
                    {'name': 'material', 'label': '材质要求', 'type': 'select', 'required': True,
                     'options': ['亚克力', 'PVC', '金属', '纸质', '其他']},
                    {'name': 'install_location', 'label': '安装位置', 'type': 'text', 'required': True},
                    {'name': 'install_date', 'label': '安装日期', 'type': 'date', 'required': True},
                    {'name': 'design_file', 'label': '设计稿', 'type': 'file', 'required': True,
                     'accept': 'image/*,.pdf,.ai,.psd', 'max': 3}
                ]
            },
            'approve_flow': {'steps': 1, 'nodes': [{'step': 1, 'name': '物业审批', 'role': 'property_manager'}]},
            'require_attachment': 1,
            'max_attachment': 3,
            'need_remind': 0,
            'sort_order': 8
        }
    ]
    
    for t in types:
        try:
            existing = db.get_one("SELECT id FROM business_application_types WHERE type_code=%s", [t['type_code']])
            if existing:
                # 更新
                db.execute("""
                    UPDATE business_application_types 
                    SET type_name=%s, category=%s, icon=%s, description=%s,
                        form_schema=%s, approve_flow=%s, need_remind=%s, 
                        remind_before_hours=%s, sort_order=%s
                    WHERE type_code=%s
                """, [t['type_name'], t['category'], t['icon'], t['description'],
                      json.dumps(t['form_schema']), json.dumps(t['approve_flow']),
                      t['need_remind'], t.get('remind_before_hours', 24), t['sort_order'], t['type_code']])
                print(f"  更新申请类型: {t['type_name']}")
            else:
                # 插入
                db.execute("""
                    INSERT INTO business_application_types 
                    (type_code, type_name, category, icon, description, form_schema, 
                     approve_flow, need_remind, remind_before_hours, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [t['type_code'], t['type_name'], t['category'], t['icon'], t['description'],
                      json.dumps(t['form_schema']), json.dumps(t['approve_flow']),
                      t['need_remind'], t.get('remind_before_hours', 24), t['sort_order']])
                print(f"  新增申请类型: {t['type_name']}")
        except Exception as e:
            print(f"  警告: {t['type_name']} 初始化失败: {e}")

def run_migration():
    print("=" * 60)
    print("V29.0 申请审批系统数据库迁移开始")
    print("=" * 60)

    for i, sql in enumerate(MIGRATIONS, 1):
        if not sql.strip():
            continue
        print(f"\n[{i}/{len(MIGRATIONS)}] 执行迁移...")
        
        # 处理MySQL语法
        sql_clean = sql.replace('IF NOT EXISTS', '').replace('IF EXISTS', '')
        
        try:
            db.execute(sql_clean)
            print(f"  ✓ 执行成功")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"  ⚠ 已存在，跳过")
            else:
                print(f"  ✗ 执行失败: {e}")
    
    # 初始化申请类型
    print("\n初始化申请类型配置...")
    init_application_types()
    
    print("\n" + "=" * 60)
    print("V29.0 数据库迁移完成")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    import json
    run_migration()
