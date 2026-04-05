"""
V16.0 数据库迁移脚本
功能：
  1. 会员等级表 business_member_levels
  2. 营销活动表 business_promotions / business_promotion_users
  3. 积分过期表 business_points_expiring
  4. WebSocket连接记录表 business_websocket_sessions
  5. 数据清理和索引优化

执行方式: python business-common/migrate_v16.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

def migrate():
    print("=" * 60)
    print("开始 V16.0 数据库迁移...")
    print("=" * 60)
    
    # ========== 1. 会员等级表 ==========
    print("\n[1/6] 创建会员等级表 business_member_levels...")
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_member_levels (
                id INT PRIMARY KEY AUTO_INCREMENT,
                level_code VARCHAR(20) NOT NULL UNIQUE COMMENT '等级编码 L1-L5',
                level_name VARCHAR(50) NOT NULL COMMENT '等级名称',
                min_amount DECIMAL(12,2) DEFAULT 0 COMMENT '升级门槛(累计消费)',
                max_amount DECIMAL(12,2) DEFAULT 0 COMMENT '最高门槛(0表示无上限)',
                discount_rate DECIMAL(5,2) DEFAULT 1.00 COMMENT '折扣率 0.95=95折',
                points_rate DECIMAL(5,2) DEFAULT 1.00 COMMENT '积分倍率 1.5=1.5倍',
                privileges TEXT COMMENT '权益说明 JSON',
                sort_order INT DEFAULT 0 COMMENT '排序',
                status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/inactive',
                ec_id VARCHAR(50) COMMENT '企业ID',
                project_id VARCHAR(50) COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_level_code (level_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员等级配置表'
        """)
        
        # 插入默认等级配置
        default_levels = [
            ('L1', '普通会员', 0, 500, 1.00, 1.00, '["基础积分倍率", "参与活动"]', 1),
            ('L2', '铜牌会员', 500, 2000, 0.95, 1.20, '["95折优惠", "积分1.2倍", "优先客服"]', 2),
            ('L3', '银牌会员', 2000, 5000, 0.90, 1.50, '["9折优惠", "积分1.5倍", "优先预约", "专属客服"]', 3),
            ('L4', '金牌会员', 5000, 10000, 0.85, 2.00, '["85折优惠", "积分2倍", "免费停车", "生日礼包"]', 4),
            ('L5', '钻石会员', 10000, 0, 0.80, 3.00, '["8折优惠", "积分3倍", "专属场地", "免费停车", "VIP客服"]', 5),
        ]
        for level in default_levels:
            try:
                db.execute("""
                    INSERT IGNORE INTO business_member_levels 
                    (level_code, level_name, min_amount, max_amount, discount_rate, points_rate, privileges, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, level)
            except Exception as e:
                print(f"  插入等级 {level[0]} 失败 (可能已存在): {e}")
        print("  ✓ 会员等级表创建完成")
    except Exception as e:
        print(f"  ✗ 会员等级表创建失败: {e}")

    # ========== 2. 营销活动表 ==========
    print("\n[2/6] 创建营销活动表...")
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_promotions (
                id INT PRIMARY KEY AUTO_INCREMENT,
                promo_name VARCHAR(100) NOT NULL COMMENT '活动名称',
                promo_type VARCHAR(20) NOT NULL COMMENT '类型 full_reduce/discount/seckill',
                description TEXT COMMENT '活动描述',
                reduce_amount DECIMAL(10,2) DEFAULT 0 COMMENT '满减金额',
                min_amount DECIMAL(10,2) DEFAULT 0 COMMENT '最低消费门槛',
                discount_rate DECIMAL(5,2) DEFAULT 1.00 COMMENT '折扣率',
                seckill_price DECIMAL(10,2) DEFAULT 0 COMMENT '秒杀价格',
                apply_type VARCHAR(20) DEFAULT 'all' COMMENT '适用范围 all/category/product',
                apply_ids TEXT COMMENT '适用ID列表 JSON',
                total_stock INT DEFAULT 0 COMMENT '总库存 0=不限',
                per_limit INT DEFAULT 1 COMMENT '每人限制 0=不限',
                start_time DATETIME NOT NULL COMMENT '开始时间',
                end_time DATETIME NOT NULL COMMENT '结束时间',
                status VARCHAR(20) DEFAULT 'pending' COMMENT '状态 pending/active/paused/ended',
                priority INT DEFAULT 0 COMMENT '优先级',
                ec_id VARCHAR(50) COMMENT '企业ID',
                project_id VARCHAR(50) COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='营销活动表'
        """)
        print("  ✓ 营销活动表创建完成")
    except Exception as e:
        print(f"  ✗ 营销活动表创建失败: {e}")

    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_promotion_users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                promotion_id INT NOT NULL COMMENT '活动ID',
                user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
                user_name VARCHAR(100) COMMENT '用户名',
                phone VARCHAR(20) COMMENT '手机号',
                use_count INT DEFAULT 0 COMMENT '使用次数',
                first_use_at DATETIME COMMENT '首次使用时间',
                last_use_at DATETIME COMMENT '最后使用时间',
                ec_id VARCHAR(50) COMMENT '企业ID',
                project_id VARCHAR(50) COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_promo_user (promotion_id, user_id),
                KEY idx_user_id (user_id),
                KEY idx_promotion_id (promotion_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户营销活动参与记录'
        """)
        print("  ✓ 用户营销参与表创建完成")
    except Exception as e:
        print(f"  ✗ 用户营销参与表创建失败: {e}")

    # ========== 3. 积分过期追踪表 ==========
    print("\n[3/6] 创建积分过期追踪表...")
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_points_expiring (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
                points_earned DECIMAL(10,2) NOT NULL COMMENT '获得积分数量',
                earned_at DATETIME NOT NULL COMMENT '获得时间',
                expires_at DATETIME NOT NULL COMMENT '过期时间',
                status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/expired/notified',
                notified_at DATETIME COMMENT '通知时间',
                notified_7days TINYINT DEFAULT 0 COMMENT '是否已发7天通知',
                notified_30days TINYINT DEFAULT 0 COMMENT '是否已发30天通知',
                expired_at DATETIME COMMENT '实际过期时间',
                ec_id VARCHAR(50) COMMENT '企业ID',
                project_id VARCHAR(50) COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                KEY idx_user_id (user_id),
                KEY idx_expires_at (expires_at),
                KEY idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='积分过期追踪表'
        """)
        print("  ✓ 积分过期追踪表创建完成")
    except Exception as e:
        print(f"  ✗ 积分过期追踪表创建失败: {e}")

    # ========== 4. WebSocket会话表 ==========
    print("\n[4/6] 创建WebSocket会话表...")
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_websocket_sessions (
                id INT PRIMARY KEY AUTO_INCREMENT,
                sid VARCHAR(100) NOT NULL COMMENT 'Socket ID',
                user_id VARCHAR(50) COMMENT '用户ID',
                user_name VARCHAR(100) COMMENT '用户名',
                room VARCHAR(50) COMMENT '所在房间',
                connect_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '连接时间',
                disconnect_at DATETIME COMMENT '断开时间',
                last_ping DATETIME COMMENT '最后心跳时间',
                ip_address VARCHAR(50) COMMENT 'IP地址',
                user_agent TEXT COMMENT '用户代理',
                ec_id VARCHAR(50) COMMENT '企业ID',
                project_id VARCHAR(50) COMMENT '项目ID',
                status VARCHAR(20) DEFAULT 'connected' COMMENT '状态 connected/disconnected',
                KEY idx_sid (sid),
                KEY idx_user_id (user_id),
                KEY idx_status (status),
                KEY idx_connect_at (connect_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='WebSocket会话记录表'
        """)
        print("  ✓ WebSocket会话表创建完成")
    except Exception as e:
        print(f"  ✗ WebSocket会话表创建失败: {e}")

    # ========== 5. 为business_members添加新字段 ==========
    print("\n[5/6] 为business_members添加新字段...")
    try:
        db.execute("""
            ALTER TABLE business_members 
            ADD COLUMN IF NOT EXISTS total_consume DECIMAL(12,2) DEFAULT 0 COMMENT '累计消费金额' AFTER balance,
            ADD COLUMN IF NOT EXISTS member_level VARCHAR(20) DEFAULT 'L1' COMMENT '会员等级 L1-L5' AFTER total_consume,
            ADD COLUMN IF NOT EXISTS member_level_updated_at DATETIME COMMENT '等级更新时间' AFTER member_level,
            ADD COLUMN IF NOT EXISTS total_checkin_days INT DEFAULT 0 COMMENT '累计签到天数' AFTER member_level_updated_at,
            ADD COLUMN IF NOT EXISTS max_checkin_days INT DEFAULT 0 COMMENT '最大连续签到天数' AFTER total_checkin_days,
            ADD COLUMN IF NOT EXISTS last_active_at DATETIME COMMENT '最后活跃时间' AFTER max_checkin_days
        """)
        print("  ✓ business_members字段添加完成")
    except Exception as e:
        # 某些字段可能已存在，忽略错误
        if 'Duplicate column' in str(e) or '已存在' in str(e):
            print("  ✓ 字段已存在，跳过")
        else:
            print(f"  ⚠ 字段添加警告: {e}")

    # ========== 6. 创建必要索引 ==========
    print("\n[6/6] 创建必要索引...")
    try:
        # 会员等级查询优化
        db.execute("CREATE INDEX IF NOT EXISTS idx_members_level ON business_members(member_level)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_members_ec ON business_members(ec_id)")
        
        # 营销活动查询优化
        db.execute("CREATE INDEX IF NOT EXISTS idx_promo_status ON business_promotions(status, start_time, end_time)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_promo_type ON business_promotions(promo_type)")
        
        # 积分日志优化
        db.execute("CREATE INDEX IF NOT EXISTS idx_points_expires ON business_points_log(created_at)")
        
        # 订单统计优化
        db.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON business_orders(DATE(created_at))")
        db.execute("CREATE INDEX IF NOT EXISTS idx_orders_pay ON business_orders(pay_status, order_status)")
        
        print("  ✓ 索引创建完成")
    except Exception as e:
        if 'Duplicate key name' in str(e) or '已存在' in str(e):
            print("  ✓ 索引已存在，跳过")
        else:
            print(f"  ⚠ 索引创建警告: {e}")

    print("\n" + "=" * 60)
    print("V16.0 数据库迁移完成!")
    print("=" * 60)
    print("\n新增表:")
    print("  - business_member_levels (会员等级配置)")
    print("  - business_promotions (营销活动)")
    print("  - business_promotion_users (用户参与记录)")
    print("  - business_points_expiring (积分过期追踪)")
    print("  - business_websocket_sessions (WebSocket会话)")
    print("\n新增字段(business_members):")
    print("  - total_consume (累计消费)")
    print("  - member_level (会员等级)")
    print("  - member_level_updated_at (等级更新时间)")
    print("  - total_checkin_days (累计签到天数)")
    print("  - max_checkin_days (最大连续签到)")
    print("  - last_active_at (最后活跃时间)")

if __name__ == '__main__':
    migrate()
