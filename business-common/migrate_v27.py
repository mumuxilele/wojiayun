#!/usr/bin/env python3
"""
V27.0 数据库迁移脚本
主要变更:
1. 浏览足迹表 - 用户行为追踪
2. 成就系统表 - 用户成就与徽章
3. 签到连续奖励配置表 - 阶梯奖励规则
4. 客户标签表 - 员工客户管理
5. 消息模板表 - 统一消息模板管理
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db


def migrate():
    """执行迁移"""
    print("开始 V27.0 数据库迁移...")

    # 1. 创建浏览足迹表
    create_recently_viewed_table()
    
    # 2. 创建成就系统表
    create_achievements_table()
    create_user_achievements_table()
    
    # 3. 创建签到连续奖励配置表
    create_checkin_rewards_config_table()
    
    # 4. 创建客户标签表
    create_customer_tags_table()
    create_customer_tag_relations_table()
    
    # 5. 创建消息模板表
    create_message_templates_table()
    
    # 6. 创建积分过期追踪视图增强
    create_rfm_analysis_view()

    print("V27.0 数据库迁移完成!")


def create_recently_viewed_table():
    """创建浏览足迹表"""
    print("创建 business_recently_viewed 表...")
    
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_recently_viewed'
    """)
    
    if check and check['cnt'] > 0:
        print("  business_recently_viewed 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_recently_viewed (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL COMMENT '用户ID',
            view_type VARCHAR(20) NOT NULL COMMENT '浏览类型: product/venue/shop',
            target_id INT NOT NULL COMMENT '目标ID(商品/场馆/门店ID)',
            target_name VARCHAR(200) COMMENT '目标名称',
            target_image VARCHAR(500) COMMENT '目标封面图',
            target_price DECIMAL(10,2) COMMENT '目标价格(记录浏览时的价格)',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '浏览时间',
            INDEX idx_user_viewed (user_id, viewed_at DESC),
            INDEX idx_user_type (user_id, view_type, viewed_at DESC),
            INDEX idx_target (target_id, view_type),
            UNIQUE KEY uk_user_view (user_id, view_type, target_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='浏览足迹表'
    """)
    print("  business_recently_viewed 表创建成功")


def create_achievements_table():
    """创建成就定义表"""
    print("创建 business_achievements 表...")
    
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_achievements'
    """)
    
    if check and check['cnt'] > 0:
        print("  business_achievements 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_achievements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(50) NOT NULL UNIQUE COMMENT '成就代码',
            name VARCHAR(100) NOT NULL COMMENT '成就名称',
            description VARCHAR(500) COMMENT '成就描述',
            icon VARCHAR(255) COMMENT '图标URL',
            category VARCHAR(30) DEFAULT 'general' COMMENT '分类: general/consume/checkin/social',
            condition_type VARCHAR(30) NOT NULL COMMENT '条件类型: order_count/order_amount/checkin_days/first_order/referral',
            condition_value INT NOT NULL COMMENT '条件阈值',
            points_reward INT DEFAULT 0 COMMENT '积分奖励',
            badge_level VARCHAR(20) DEFAULT 'bronze' COMMENT '徽章等级: bronze/silver/gold',
            sort_order INT DEFAULT 0 COMMENT '排序',
            status TINYINT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_code (code),
            INDEX idx_category (category),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成就定义表'
    """)
    
    # 插入默认成就数据
    insert_default_achievements()
    print("  business_achievements 表创建成功")


def insert_default_achievements():
    """插入默认成就数据"""
    achievements = [
        # 消费类成就
        ("first_order", "首次下单", "完成您的第一笔订单", "badge_first_order", "general", "first_order", 1, 10, "bronze", 1),
        ("order_5", "消费达人", "累计完成5笔订单", "badge_order_5", "consume", "order_count", 5, 50, "silver", 2),
        ("order_20", "购物狂人", "累计完成20笔订单", "badge_order_20", "consume", "order_count", 20, 200, "gold", 3),
        ("order_50", "超级会员", "累计完成50笔订单", "badge_order_50", "consume", "order_count", 50, 500, "gold", 4),
        ("consume_1000", "千元玩家", "累计消费满1000元", "badge_consume_1000", "consume", "order_amount", 1000, 100, "bronze", 5),
        ("consume_5000", "万元大户", "累计消费满5000元", "badge_consume_5000", "consume", "order_amount", 5000, 500, "silver", 6),
        ("consume_10000", "钻石会员", "累计消费满10000元", "badge_consume_10000", "consume", "order_amount", 10000, 1000, "gold", 7),
        
        # 签到类成就
        ("checkin_7", "坚持不懈", "连续签到7天", "badge_checkin_7", "checkin", "checkin_days", 7, 70, "bronze", 10),
        ("checkin_30", "持之以恒", "连续签到30天", "badge_checkin_30", "checkin", "checkin_days", 30, 300, "silver", 11),
        ("checkin_100", "签到王者", "连续签到100天", "badge_checkin_100", "checkin", "checkin_days", 100, 1000, "gold", 12),
        
        # 社交类成就
        ("referral_3", "分享达人", "成功邀请3位好友", "badge_referral_3", "social", "referral", 3, 30, "bronze", 20),
        ("referral_10", "社交明星", "成功邀请10位好友", "badge_referral_10", "social", "referral", 10, 100, "silver", 21),
    ]
    
    for ach in achievements:
        try:
            db.execute("""
                INSERT IGNORE INTO business_achievements 
                (code, name, description, icon, category, condition_type, condition_value, points_reward, badge_level, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, ach)
        except Exception as e:
            logging.warning(f"插入成就失败: {e}")


def create_user_achievements_table():
    """创建用户成就表"""
    print("创建 business_user_achievements 表...")
    
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_user_achievements'
    """)
    
    if check and check['cnt'] > 0:
        print("  business_user_achievements 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_user_achievements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL COMMENT '用户ID',
            achievement_code VARCHAR(50) NOT NULL COMMENT '成就代码',
            achievement_name VARCHAR(100) COMMENT '成就名称(冗余)',
            badge_icon VARCHAR(255) COMMENT '徽章图标(冗余)',
            points_earned INT DEFAULT 0 COMMENT '获得的积分',
            earned_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '获得时间',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            INDEX idx_user (user_id),
            INDEX idx_achievement (achievement_code),
            UNIQUE KEY uk_user_achievement (user_id, achievement_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户成就表'
    """)
    print("  business_user_achievements 表创建成功")


def create_checkin_rewards_config_table():
    """创建签到连续奖励配置表"""
    print("创建 business_checkin_rewards_config 表...")
    
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_checkin_rewards_config'
    """)
    
    if check and check['cnt'] > 0:
        print("  business_checkin_rewards_config 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_checkin_rewards_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            streak_days INT NOT NULL COMMENT '连续签到天数',
            base_points INT NOT NULL COMMENT '基础积分',
            bonus_points INT DEFAULT 0 COMMENT '额外奖励积分',
            bonus_type VARCHAR(20) DEFAULT 'fixed' COMMENT '奖励类型: fixed/percentage',
            bonus_threshold INT COMMENT '触发额外奖励的门槛(如满7天额外奖励)',
            description VARCHAR(200) COMMENT '奖励说明',
            status TINYINT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_streak_days (streak_days)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='签到连续奖励配置表'
    """)
    
    # 插入默认配置
    insert_default_checkin_rewards()
    print("  business_checkin_rewards_config 表创建成功")


def insert_default_checkin_rewards():
    """插入默认签到奖励配置"""
    rewards = [
        (1, 5, 0, 'fixed', None, '每日签到', 1),
        (3, 5, 10, 'fixed', 3, '连续签到3天，额外奖励10积分', 1),
        (7, 5, 30, 'fixed', 7, '连续签到7天，额外奖励30积分', 1),
        (14, 5, 50, 'fixed', 14, '连续签到14天，额外奖励50积分', 1),
        (30, 5, 100, 'fixed', 30, '连续签到30天，额外奖励100积分', 1),
        (60, 5, 200, 'fixed', 60, '连续签到60天，额外奖励200积分', 1),
        (90, 5, 500, 'fixed', 90, '连续签到90天，额外奖励500积分', 1),
    ]
    
    for r in rewards:
        try:
            db.execute("""
                INSERT IGNORE INTO business_checkin_rewards_config 
                (streak_days, base_points, bonus_points, bonus_type, bonus_threshold, description, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, r)
        except Exception as e:
            logging.warning(f"插入签到奖励配置失败: {e}")


def create_customer_tags_table():
    """创建客户标签定义表"""
    print("创建 business_customer_tags 表...")
    
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_customer_tags'
    """)
    
    if check and check['cnt'] > 0:
        print("  business_customer_tags 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_customer_tags (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tag_name VARCHAR(50) NOT NULL COMMENT '标签名称',
            tag_color VARCHAR(20) DEFAULT '#1890ff' COMMENT '标签颜色',
            tag_type VARCHAR(20) DEFAULT 'custom' COMMENT '标签类型: custom/system',
            description VARCHAR(200) COMMENT '标签描述',
            sort_order INT DEFAULT 0 COMMENT '排序',
            status TINYINT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
            created_by VARCHAR(50) COMMENT '创建人',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_name (tag_name),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户标签定义表'
    """)
    
    # 插入默认标签
    insert_default_customer_tags()
    print("  business_customer_tags 表创建成功")


def insert_default_customer_tags():
    """插入默认客户标签"""
    tags = [
        ("重要客户", "#ff4d4f", "system", "高价值客户"),
        ("潜在客户", "#1890ff", "system", "有购买意向"),
        ("沉睡客户", "#faad14", "system", "长期未消费"),
        ("新客户", "#52c41a", "system", "近30天新注册"),
        ("VIP客户", "#722ed1", "system", "高消费频次"),
        ("需要跟进", "#13c2c2", "system", "需要主动联系"),
    ]
    
    for t in tags:
        try:
            db.execute("""
                INSERT IGNORE INTO business_customer_tags 
                (tag_name, tag_color, tag_type, description, sort_order, status)
                VALUES (%s, %s, %s, %s, %s, 1)
            """, (*t, 0))
        except Exception as e:
            logging.warning(f"插入客户标签失败: {e}")


def create_customer_tag_relations_table():
    """创建客户标签关系表"""
    print("创建 business_customer_tag_relations 表...")
    
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_customer_tag_relations'
    """)
    
    if check and check['cnt'] > 0:
        print("  business_customer_tag_relations 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_customer_tag_relations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            staff_id INT NOT NULL COMMENT '员工ID',
            customer_user_id INT NOT NULL COMMENT '客户用户ID',
            tag_id INT NOT NULL COMMENT '标签ID',
            note VARCHAR(500) COMMENT '备注',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_staff (staff_id),
            INDEX idx_customer (customer_user_id),
            INDEX idx_tag (tag_id),
            UNIQUE KEY uk_relation (staff_id, customer_user_id, tag_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户标签关系表'
    """)
    print("  business_customer_tag_relations 表创建成功")


def create_message_templates_table():
    """创建消息模板表"""
    print("创建 business_message_templates 表...")
    
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_message_templates'
    """)
    
    if check and check['cnt'] > 0:
        print("  business_message_templates 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_message_templates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            template_code VARCHAR(50) NOT NULL UNIQUE COMMENT '模板代码',
            template_name VARCHAR(100) NOT NULL COMMENT '模板名称',
            template_type VARCHAR(20) NOT NULL COMMENT '模板类型: sms/wechat/email/system',
            content TEXT NOT NULL COMMENT '模板内容，支持变量占位符 {name}',
            variables VARCHAR(500) COMMENT '变量列表，JSON格式 ["name","orderNo"]',
            scene VARCHAR(50) COMMENT '使用场景: order_paid/order_shipped/checkin_reward/achievement_unlock',
            status TINYINT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
            created_by VARCHAR(50) COMMENT '创建人',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_code (template_code),
            INDEX idx_type (template_type),
            INDEX idx_scene (scene),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息模板表'
    """)
    
    # 插入默认模板
    insert_default_message_templates()
    print("  business_message_templates 表创建成功")


def insert_default_message_templates():
    """插入默认消息模板"""
    templates = [
        # 系统通知模板
        ("order_paid_notify", "订单支付成功通知", "system", 
         "您的订单 {orderNo} 已支付成功，支付金额 {amount} 元，感谢您的购买！", 
         '["orderNo","amount"]', "order_paid", 1),
        ("order_shipped_notify", "订单发货通知", "system",
         "您的订单 {orderNo} 已发货，快递单号：{trackingNo}，预计 {deliveryDate} 送达。",
         '["orderNo","trackingNo","deliveryDate"]', "order_shipped", 1),
        ("order_refunded_notify", "退款到账通知", "system",
         "您的退款申请已通过，{amount} 元已退回至您的支付账户，预计1-3个工作日到账。",
         '["amount"]', "order_refunded", 1),
        ("checkin_reward_notify", "签到奖励通知", "system",
         "恭喜您完成今日签到！获得 {points} 积分，当前连续签到 {streakDays} 天。",
         '["points","streakDays"]', "checkin_reward", 1),
        ("achievement_unlock_notify", "成就解锁通知", "system",
         "恭喜您解锁新成就：{achievementName}！获得 {points} 积分奖励。",
         '["achievementName","points"]', "achievement_unlock", 1),
        ("coupon_expiring_notify", "优惠券即将过期", "system",
         "您有一张 {couponName} 即将在 {expireDate} 到期，请尽快使用！",
         '["couponName","expireDate"]', "coupon_expiring", 1),
        
        # 微信模板（示例）
        ("wechat_order_remind", "订单提醒", "wechat",
         "您有新的订单待处理，订单号：{orderNo}，金额：{amount}元",
         '["orderNo","amount"]', "order_new", 1),
    ]
    
    for t in templates:
        try:
            db.execute("""
                INSERT IGNORE INTO business_message_templates 
                (template_code, template_name, template_type, content, variables, scene, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, t)
        except Exception as e:
            logging.warning(f"插入消息模板失败: {e}")


def create_rfm_analysis_view():
    """创建RFM分析视图（增强版）"""
    print("创建 rfm_analysis_view 视图...")
    
    try:
        # 先删除旧视图（如果存在）
        db.execute("DROP VIEW IF EXISTS rfm_analysis_view")
    except:
        pass
    
    db.execute("""
        CREATE OR REPLACE VIEW rfm_analysis_view AS
        SELECT 
            m.id as member_id,
            m.user_name,
            m.phone,
            m.member_level,
            m.total_consume,
            m.points,
            m.last_checkin_date,
            m.checkin_streak,
            -- R: 最近一次消费距今天数
            DATEDIFF(CURDATE(), COALESCE(MAX(o.created_at), m.created_at)) as recency_days,
            -- F: 累计消费频次
            COUNT(DISTINCT o.id) as frequency_orders,
            -- M: 累计消费金额
            COALESCE(SUM(CASE WHEN o.pay_status = 'paid' THEN o.actual_amount ELSE 0 END), 0) as monetary_total,
            -- RFM评分
            CASE 
                WHEN DATEDIFF(CURDATE(), COALESCE(MAX(o.created_at), m.created_at)) <= 7 THEN 5
                WHEN DATEDIFF(CURDATE(), COALESCE(MAX(o.created_at), m.created_at)) <= 30 THEN 4
                WHEN DATEDIFF(CURDATE(), COALESCE(MAX(o.created_at), m.created_at)) <= 90 THEN 3
                WHEN DATEDIFF(CURDATE(), COALESCE(MAX(o.created_at), m.created_at)) <= 180 THEN 2
                ELSE 1
            END as r_score,
            CASE 
                WHEN COUNT(DISTINCT o.id) >= 10 THEN 5
                WHEN COUNT(DISTINCT o.id) >= 5 THEN 4
                WHEN COUNT(DISTINCT o.id) >= 3 THEN 3
                WHEN COUNT(DISTINCT o.id) >= 1 THEN 2
                ELSE 1
            END as f_score,
            CASE 
                WHEN COALESCE(SUM(CASE WHEN o.pay_status = 'paid' THEN o.actual_amount ELSE 0 END), 0) >= 5000 THEN 5
                WHEN COALESCE(SUM(CASE WHEN o.pay_status = 'paid' THEN o.actual_amount ELSE 0 END), 0) >= 2000 THEN 4
                WHEN COALESCE(SUM(CASE WHEN o.pay_status = 'paid' THEN o.actual_amount ELSE 0 END), 0) >= 500 THEN 3
                WHEN COALESCE(SUM(CASE WHEN o.pay_status = 'paid' THEN o.actual_amount ELSE 0 END), 0) >= 100 THEN 2
                ELSE 1
            END as m_score,
            -- RFM类型
            CASE 
                WHEN DATEDIFF(CURDATE(), COALESCE(MAX(o.created_at), m.created_at)) <= 30 
                    AND COUNT(DISTINCT o.id) >= 3 
                    AND COALESCE(SUM(CASE WHEN o.pay_status = 'paid' THEN o.actual_amount ELSE 0 END), 0) >= 500
                THEN '重要价值用户'
                WHEN DATEDIFF(CURDATE(), COALESCE(MAX(o.created_at), m.created_at)) <= 30 
                    AND COUNT(DISTINCT o.id) < 3
                THEN '重要发展用户'
                WHEN DATEDIFF(CURDATE(), COALESCE(MAX(o.created_at), m.created_at)) > 30 
                    AND COUNT(DISTINCT o.id) >= 3
                THEN '重要保持用户'
                ELSE '重要挽留用户'
            END as rfm_type
        FROM business_members m
        LEFT JOIN business_orders o ON m.user_id = o.user_id AND o.deleted = 0
        GROUP BY m.id, m.user_name, m.phone, m.member_level, m.total_consume, m.points, m.last_checkin_date, m.checkin_streak, m.created_at
    """)
    print("  rfm_analysis_view 视图创建成功")


def rollback():
    """回滚迁移"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("开始回滚 V27.0 数据库迁移...")
    
    try:
        # 删除视图
        db.execute("DROP VIEW IF EXISTS rfm_analysis_view")
        print("  rfm_analysis_view 视图已删除")
        
        # 删除表（按依赖顺序）
        db.execute("DROP TABLE IF EXISTS business_customer_tag_relations")
        print("  business_customer_tag_relations 表已删除")
        
        db.execute("DROP TABLE IF EXISTS business_customer_tags")
        print("  business_customer_tags 表已删除")
        
        db.execute("DROP TABLE IF EXISTS business_message_templates")
        print("  business_message_templates 表已删除")
        
        db.execute("DROP TABLE IF EXISTS business_checkin_rewards_config")
        print("  business_checkin_rewards_config 表已删除")
        
        db.execute("DROP TABLE IF EXISTS business_user_achievements")
        print("  business_user_achievements 表已删除")
        
        db.execute("DROP TABLE IF EXISTS business_achievements")
        print("  business_achievements 表已删除")
        
        db.execute("DROP TABLE IF EXISTS business_recently_viewed")
        print("  business_recently_viewed 表已删除")
        
        print("V27.0 回滚完成!")
    except Exception as e:
        print(f"回滚失败: {e}")


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        rollback()
    else:
        migrate()
