#!/usr/bin/env python3
"""
V28.0 数据库迁移脚本
变更内容:
1. 成长值体系表 (business_member_growth)
2. 批量操作日志表 (business_batch_operations)
3. 订单打印记录表 (business_print_logs)
4. 积分商城兑换物流表 (business_points_delivery)
5. 成长值规则配置表 (business_growth_rules)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db, config

MIGRATIONS = [
    # 1. 成长值记录表
    """
    CREATE TABLE IF NOT EXISTS business_member_growth (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL COMMENT '用户ID',
        user_name VARCHAR(50) DEFAULT '' COMMENT '用户名',
        growth_type VARCHAR(30) NOT NULL COMMENT '成长值类型: order-消费, checkin-签到, review-评价, referral-邀请, activity-活动',
        growth_value INT NOT NULL DEFAULT 0 COMMENT '成长值变化(正数)',
        total_growth INT DEFAULT 0 COMMENT '变化后总成长值',
        level_before INT DEFAULT 0 COMMENT '变化前等级',
        level_after INT DEFAULT 0 COMMENT '变化后等级',
        description VARCHAR(200) DEFAULT '' COMMENT '说明',
        ref_id VARCHAR(50) DEFAULT '' COMMENT '关联ID(订单号/活动ID等)',
        ref_type VARCHAR(30) DEFAULT '' COMMENT '关联类型(order/checkin/review/activity)',
        ec_id BIGINT DEFAULT NULL,
        project_id BIGINT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user_growth (user_id, created_at),
        INDEX idx_type_created (growth_type, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成长值记录表';
    """,

    # 2. 批量操作日志表
    """
    CREATE TABLE IF NOT EXISTS business_batch_operations (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        batch_no VARCHAR(50) NOT NULL COMMENT '批次号',
        operation_type VARCHAR(30) NOT NULL COMMENT '操作类型: batch_ship-批量发货, batch_process-批量处理申请, batch_refund-批量退款',
        target_type VARCHAR(30) NOT NULL COMMENT '目标类型: order-订单, application-申请单',
        total_count INT DEFAULT 0 COMMENT '总数量',
        success_count INT DEFAULT 0 COMMENT '成功数量',
        fail_count INT DEFAULT 0 COMMENT '失败数量',
        fail_details TEXT COMMENT '失败详情JSON',
        operator_id BIGINT NOT NULL COMMENT '操作人ID',
        operator_name VARCHAR(50) DEFAULT '' COMMENT '操作人姓名',
        ec_id BIGINT DEFAULT NULL,
        project_id BIGINT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_batch_no (batch_no),
        INDEX idx_operator_time (operator_id, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批量操作日志表';
    """,

    # 3. 订单打印记录表
    """
    CREATE TABLE IF NOT EXISTS business_print_logs (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        order_id BIGINT NOT NULL COMMENT '订单ID',
        order_no VARCHAR(50) NOT NULL COMMENT '订单号',
        print_type VARCHAR(30) NOT NULL COMMENT '打印类型: express-快递单, picking-配货单, invoice-发票',
        print_content TEXT COMMENT '打印内容JSON快照',
        printer_name VARCHAR(100) DEFAULT '' COMMENT '打印机名称',
        copies INT DEFAULT 1 COMMENT '打印份数',
        operator_id BIGINT DEFAULT NULL COMMENT '操作人ID',
        operator_name VARCHAR(50) DEFAULT '' COMMENT '操作人',
        ip_address VARCHAR(50) DEFAULT '' COMMENT 'IP地址',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_order_print (order_id, print_type),
        INDEX idx_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单打印记录表';
    """,

    # 4. 积分商城兑换物流表
    """
    CREATE TABLE IF NOT EXISTS business_points_delivery (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        exchange_id BIGINT NOT NULL COMMENT '兑换记录ID',
        exchange_no VARCHAR(50) NOT NULL COMMENT '兑换单号',
        logistics_company VARCHAR(50) DEFAULT '' COMMENT '物流公司',
        tracking_no VARCHAR(100) DEFAULT '' COMMENT '物流单号',
        ship_time DATETIME DEFAULT NULL COMMENT '发货时间',
        delivery_status VARCHAR(20) DEFAULT 'pending' COMMENT '配送状态: pending-待发货, shipped-已发货, in_transit-运输中, delivered-已签收',
        delivery_times INT DEFAULT 0 COMMENT '配送次数(查询物流公司次数)',
        last_query_time DATETIME DEFAULT NULL COMMENT '最后查询时间',
        signed_time DATETIME DEFAULT NULL COMMENT '签收时间',
        signature_image TEXT COMMENT '签收图片',
        ec_id BIGINT DEFAULT NULL,
        project_id BIGINT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_exchange (exchange_id, exchange_no),
        INDEX idx_tracking (tracking_no),
        INDEX idx_status (delivery_status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='积分兑换物流表';
    """,

    # 5. 成长值规则配置表
    """
    CREATE TABLE IF NOT EXISTS business_growth_rules (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        rule_code VARCHAR(50) NOT NULL UNIQUE COMMENT '规则代码',
        rule_name VARCHAR(100) NOT NULL COMMENT '规则名称',
        growth_type VARCHAR(30) NOT NULL COMMENT '成长类型',
        growth_value INT NOT NULL DEFAULT 0 COMMENT '每次获得成长值',
        daily_limit INT DEFAULT 0 COMMENT '每日上限(0=无限制)',
        total_limit INT DEFAULT 0 COMMENT '累计上限(0=无限制)',
        level_thresholds TEXT COMMENT '等级阈值JSON: [{"level":1,"threshold":100},...]',
        is_active TINYINT DEFAULT 1 COMMENT '是否启用',
        sort_order INT DEFAULT 0 COMMENT '排序',
        description VARCHAR(200) DEFAULT '' COMMENT '说明',
        ec_id BIGINT DEFAULT NULL,
        project_id BIGINT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_active_type (is_active, growth_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成长值规则配置表';
    """,

    # 6. 会员表新增成长值相关字段
    """
    ALTER TABLE business_members 
    ADD COLUMN IF NOT EXISTS growth_value INT DEFAULT 0 COMMENT '成长值总数' AFTER points,
    ADD COLUMN IF NOT EXISTS member_grade INT DEFAULT 1 COMMENT '会员等级(1-10)' AFTER member_level;
    """,

    # 7. 积分商城兑换表新增物流信息
    """
    ALTER TABLE business_points_exchanges
    ADD COLUMN IF NOT EXISTS logistics_company VARCHAR(50) DEFAULT '' COMMENT '物流公司' AFTER shipping_address,
    ADD COLUMN IF NOT EXISTS tracking_no VARCHAR(100) DEFAULT '' COMMENT '物流单号' AFTER logistics_company;
    """,
]

def run_migration():
    """执行数据库迁移"""
    print("=" * 60)
    print("V28.0 数据库迁移开始")
    print("=" * 60)

    for i, sql in enumerate(MIGRATIONS, 1):
        if not sql.strip():
            continue
        
        print(f"\n[{i}/{len(MIGRATIONS)}] 执行迁移...")
        
        # 处理MySQL特定的语法
        sql = sql.replace('IF NOT EXISTS', '')
        
        # 提取表名
        table_match = None
        if 'CREATE TABLE' in sql.upper():
            import re
            match = re.search(r'CREATE TABLE.*?`?(\w+)`?', sql, re.IGNORECASE)
            if match:
                table_match = match.group(1)
                # 检查表是否存在
                existing = db.get_one(f"SHOW TABLES LIKE '{table_match}'")
                if existing:
                    print(f"  表 {table_match} 已存在，跳过创建")
                    # 继续执行ALTER TABLE部分
                    if 'ADD COLUMN' in sql:
                        alter_sqls = sql.split(';')
                        for alter_sql in alter_sqls:
                            if 'ADD COLUMN' in alter_sql and 'ALTER TABLE' not in alter_sql:
                                col_match = re.search(r'ADD COLUMN IF NOT EXISTS\s+(\w+)', alter_sql)
                                if col_match:
                                    col_name = col_match.group(1)
                                    try:
                                        db.execute(f"ALTER TABLE {table_match} ADD COLUMN {col_name.split('ADD COLUMN IF NOT EXISTS')[1].strip()}")
                                        print(f"  添加字段 {col_name}")
                                    except Exception as e:
                                        if 'Duplicate column' in str(e):
                                            print(f"  字段 {col_name} 已存在")
                                        else:
                                            print(f"  警告: {e}")
                    continue
        
        try:
            db.execute(sql)
            if table_match:
                print(f"  ✓ 表 {table_match} 创建成功")
            else:
                print(f"  ✓ SQL执行成功")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print(f"  ⚠ 表或字段已存在，跳过")
            else:
                print(f"  ✗ 执行失败: {e}")
    
    # 插入默认成长值规则
    print("\n插入默认成长值规则...")
    default_rules = [
        ('order_consume', '消费成长', 'order', 1, 0, 0, '[{"level":1,"threshold":0},{"level":2,"threshold":100},{"level":3,"threshold":500},{"level":4,"threshold":1000},{"level":5,"threshold":2000}]', '每消费1元获得1成长值'),
        ('daily_checkin', '每日签到', 'checkin', 5, 1, 0, '', '每日签到获得5成长值'),
        ('order_review', '订单评价', 'review', 10, 5, 0, '', '每评价一次订单获得10成长值'),
        ('invite_friend', '邀请好友', 'referral', 50, 0, 0, '', '邀请一位好友注册获得50成长值'),
        ('activity_participate', '参与活动', 'activity', 20, 3, 0, '', '参与平台活动获得20成长值'),
    ]
    
    for rule in default_rules:
        try:
            db.execute("""
                INSERT IGNORE INTO business_growth_rules 
                (rule_code, rule_name, growth_type, growth_value, daily_limit, total_limit, level_thresholds, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, rule)
            print(f"  ✓ 插入规则: {rule[1]}")
        except Exception as e:
            if 'duplicate' not in str(e).lower():
                print(f"  ⚠ 规则 {rule[1]} 插入失败: {e}")
    
    print("\n" + "=" * 60)
    print("V28.0 数据库迁移完成")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    run_migration()
