#!/usr/bin/env python3
"""V46.0 数据库迁移 - 添加 ec_id 和 project_id 字段"""
import pymysql

conn = pymysql.connect(
    host='47.98.238.209',
    user='root',
    password='Wojiacloud$2023',
    database='visit_system'
)
cursor = conn.cursor()

# 需要添加字段的表配置
# 格式: (表名, 字段位置说明)
tables_to_update = [
    # 业务单据表
    ('business_application_attachments', '业务申请附件表'),
    ('business_application_logs', '业务申请日志表'),
    ('business_application_reminds', '业务申请提醒表'),
    ('business_checkin_logs', '打卡记录表'),
    ('business_feedback', '反馈表'),
    ('business_logistics_subscriptions', '物流订阅表'),
    ('business_logistics_traces', '物流追踪表'),
    ('business_order_items', '订单项表'),
    ('business_payment_logs', '支付日志表'),
    ('business_ratings', '评分表'),
    ('business_venue_reviews', '场地评价表'),
    ('visit_records', '走访记录表'),
    # 配置表
    ('business_application_types', '申请类型表'),
    ('business_system_config', '系统配置表'),
    ('business_user_points', '用户积分表'),
    # 其他表
    ('auth_accounts', '认证账户表'),
    ('business_approve_nodes', '审批节点表'),
    ('business_venue_favorites', '场地收藏表'),
    ('chat_groups', '聊天群组表'),
    ('chat_message_reads', '消息已读表'),
    ('chat_messages', '聊天消息表'),
    ('chat_sessions', '聊天会话表'),
    ('t_pc_employee', '员工表'),
    ('t_csc_wotype', '工单类型表'),
]

success_count = 0
failed_count = 0
failed_tables = []

print("=" * 70)
print("V46.0 数据库迁移 - 添加 ec_id 和 project_id 字段")
print("=" * 70)

for table_name, description in tables_to_update:
    try:
        print(f"\n处理: {table_name} ({description})")
        
        # 检查是否已有这些字段
        cursor.execute(f"DESCRIBE {table_name}")
        columns = [col[0] for col in cursor.fetchall()]
        
        if 'ec_id' in columns and 'project_id' in columns:
            print(f"  ⏭️  已存在 ec_id 和 project_id，跳过")
            continue
        
        # 获取第一个字段名用于 AFTER 定位
        first_col = columns[0] if columns else 'id'
        
        # 构建 ALTER TABLE 语句
        alter_parts = []
        if 'ec_id' not in columns:
            alter_parts.append(f"ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER {first_col}")
        if 'project_id' not in columns:
            alter_parts.append("ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id")
        
        # 添加索引
        if 'ec_id' not in columns:
            alter_parts.append("ADD INDEX idx_ec_id (ec_id)")
        if 'project_id' not in columns:
            alter_parts.append("ADD INDEX idx_project_id (project_id)")
        
        if alter_parts:
            sql = f"ALTER TABLE {table_name} " + ", ".join(alter_parts)
            cursor.execute(sql)
            conn.commit()
            print(f"  ✅ 成功添加字段")
            success_count += 1
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        failed_count += 1
        failed_tables.append((table_name, str(e)))
        conn.rollback()

cursor.close()
conn.close()

print("\n" + "=" * 70)
print(f"迁移完成: 成功 {success_count} 个表, 失败 {failed_count} 个表")
print("=" * 70)

if failed_tables:
    print("\n失败的表:")
    for table, error in failed_tables:
        print(f"  - {table}: {error}")
