"""
V40.0 数据库迁移脚本

本版本新增功能：
1. 会员生命周期管理表 (business_member_lifecycle)
2. 触达策略表 (business_lifecycle_strategies)
3. 用户行为记录表 (business_user_behaviors)
4. 用户画像表 (business_user_profiles)
5. 用户漏斗分析表 (business_user_funnel)

执行方式:
    cd business-common
    python migrate_v40.py
"""
import sys
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db


def check_table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    result = db.get_one("SHOW TABLES LIKE %s", [table_name])
    return result is not None


def migrate():
    """执行迁移"""
    logger.info("=" * 50)
    logger.info("开始 V40.0 数据库迁移...")
    logger.info("=" * 50)

    try:
        # ========== 1. 会员生命周期管理表 ==========
        if not check_table_exists('business_member_lifecycle'):
            logger.info("[1/5] 创建会员生命周期表 business_member_lifecycle...")
            db.execute("""
                CREATE TABLE IF NOT EXISTS business_member_lifecycle (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL COMMENT '用户ID',
                    ec_id INT DEFAULT 1 COMMENT '企业ID',
                    project_id INT DEFAULT 1 COMMENT '项目ID',
                    current_stage VARCHAR(20) DEFAULT 'new_user' COMMENT '当前阶段',
                    stage_updated_at DATETIME COMMENT '阶段更新时间',
                    last_action_at DATETIME COMMENT '最后活动时间',
                    action_count INT DEFAULT 0 COMMENT '行为次数',
                    health_score INT DEFAULT 100 COMMENT '健康度评分 0-100',
                    risk_level VARCHAR(20) DEFAULT 'none' COMMENT '风险等级',
                    tags TEXT COMMENT '用户标签 JSON',
                    next_action_at DATETIME COMMENT '下次触达时间',
                    action_history TEXT COMMENT '触达历史 JSON',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user (user_id),
                    INDEX idx_stage (current_stage),
                    INDEX idx_ec_project (ec_id, project_id),
                    INDEX idx_last_action (last_action_at),
                    INDEX idx_health_score (health_score)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '会员生命周期表';
            """)
            logger.info("✓ business_member_lifecycle 表创建成功")
        else:
            logger.info("[1/5] business_member_lifecycle 表已存在，跳过")

        # ========== 2. 触达策略表 ==========
        if not check_table_exists('business_lifecycle_strategies'):
            logger.info("[2/5] 创建触达策略表 business_lifecycle_strategies...")
            db.execute("""
                CREATE TABLE IF NOT EXISTS business_lifecycle_strategies (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    strategy_code VARCHAR(50) NOT NULL COMMENT '策略代码',
                    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
                    stage VARCHAR(20) NOT NULL COMMENT '适用阶段',
                    trigger_condition VARCHAR(200) COMMENT '触发条件',
                    action_type VARCHAR(20) NOT NULL COMMENT '动作类型: notification/sms/coupon/points',
                    action_config TEXT COMMENT '动作配置 JSON',
                    priority INT DEFAULT 100 COMMENT '优先级 1-100',
                    status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/paused',
                    ec_id INT COMMENT '企业ID（NULL表示通用）',
                    project_id INT COMMENT '项目ID（NULL表示通用）',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_strategy_code (strategy_code),
                    INDEX idx_stage (stage),
                    INDEX idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '触达策略表';
            """)
            logger.info("✓ business_lifecycle_strategies 表创建成功")

            # 插入默认策略
            logger.info("    插入默认触达策略...")
            default_strategies = [
                ('new_user_welcome', '新用户欢迎礼包', 'new_user', None, 'notification',
                 '{"title": "欢迎加入", "content": "恭喜您成为会员，新人专属福利等你来领！", "coupon": true, "points": 50}', 100),
                ('active_birthday', '生日祝福', 'active', 'is_birthday = true', 'coupon',
                 '{"coupon_type": "birthday", "discount": 10, "amount": 100}', 90),
                ('hot_vip_exclusive', 'VIP专属优惠', 'hot', None, 'coupon',
                 '{"coupon_type": "vip", "discount": 20, "amount": 200, "threshold": 500}', 80),
                ('sleep_awaken_v1', '沉睡唤醒-小额券', 'sleeping', None, 'coupon',
                 '{"coupon_type": "awaken", "discount": 5, "amount": 50, "threshold": 100}', 70),
                ('churning_recover_v1', '流失召回-大额券', 'churning', None, 'coupon',
                 '{"coupon_type": "winback", "discount": 20, "amount": 100, "threshold": 200}', 60),
                ('churned_winback', '流失挽回-超级礼包', 'churned', None, 'coupon',
                 '{"coupon_type": "winback", "discount": 30, "amount": 200, "threshold": 300}', 50),
            ]

            for strategy in default_strategies:
                db.execute("""
                    INSERT INTO business_lifecycle_strategies
                    (strategy_code, strategy_name, stage, trigger_condition, action_type, action_config, priority)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, strategy)
            logger.info("    ✓ 6条默认策略插入成功")
        else:
            logger.info("[2/5] business_lifecycle_strategies 表已存在，跳过")

        # ========== 3. 用户行为记录表 ==========
        if not check_table_exists('business_user_behaviors'):
            logger.info("[3/5] 创建用户行为记录表 business_user_behaviors...")
            db.execute("""
                CREATE TABLE IF NOT EXISTS business_user_behaviors (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL COMMENT '用户ID',
                    behavior_type VARCHAR(50) NOT NULL COMMENT '行为类型',
                    target_type VARCHAR(50) COMMENT '目标类型: product/category/shop/order',
                    target_id INT COMMENT '目标ID',
                    target_name VARCHAR(200) COMMENT '目标名称（冗余存储）',
                    ec_id INT DEFAULT 1 COMMENT '企业ID',
                    project_id INT DEFAULT 1 COMMENT '项目ID',
                    session_id VARCHAR(100) COMMENT '会话ID',
                    duration INT DEFAULT 0 COMMENT '停留时长(秒)',
                    extra_data TEXT COMMENT '扩展数据 JSON',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_type (user_id, behavior_type),
                    INDEX idx_user_time (user_id, created_at),
                    INDEX idx_target (target_type, target_id),
                    INDEX idx_ec_project (ec_id, project_id),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '用户行为记录表';
            """)
            logger.info("✓ business_user_behaviors 表创建成功")
        else:
            logger.info("[3/5] business_user_behaviors 表已存在，跳过")

        # ========== 4. 用户画像表 ==========
        if not check_table_exists('business_user_profiles'):
            logger.info("[4/5] 创建用户画像表 business_user_profiles...")
            db.execute("""
                CREATE TABLE IF NOT EXISTS business_user_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL COMMENT '用户ID',
                    ec_id INT DEFAULT 1 COMMENT '企业ID',
                    project_id INT DEFAULT 1 COMMENT '项目ID',
                    interest_products TEXT COMMENT '感兴趣的商品ID列表 JSON',
                    interest_categories TEXT COMMENT '感兴趣的分类 JSON',
                    interest_shops TEXT COMMENT '感兴趣的门店 JSON',
                    interest_tags TEXT COMMENT '兴趣标签 JSON',
                    preference_price_min DECIMAL(10,2) DEFAULT 0 COMMENT '价格偏好下限',
                    preference_price_max DECIMAL(10,2) DEFAULT 0 COMMENT '价格偏好上限',
                    purchase_power VARCHAR(20) DEFAULT 'normal' COMMENT '购买力: low/normal/high/vip',
                    active_score INT DEFAULT 0 COMMENT '活跃度得分 0-100',
                    engagement_score INT DEFAULT 0 COMMENT '参与度得分 0-100',
                    conversion_score INT DEFAULT 0 COMMENT '转化得分 0-100',
                    last_active_at DATETIME COMMENT '最后活跃时间',
                    behavior_count INT DEFAULT 0 COMMENT '累计行为次数',
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user (user_id),
                    INDEX idx_ec_project (ec_id, project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '用户画像表';
            """)
            logger.info("✓ business_user_profiles 表创建成功")
        else:
            logger.info("[4/5] business_user_profiles 表已存在，跳过")

        # ========== 5. 用户漏斗分析表 ==========
        if not check_table_exists('business_user_funnel'):
            logger.info("[5/5] 创建用户漏斗分析表 business_user_funnel...")
            db.execute("""
                CREATE TABLE IF NOT EXISTS business_user_funnel (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL COMMENT '用户ID',
                    ec_id INT DEFAULT 1 COMMENT '企业ID',
                    project_id INT DEFAULT 1 COMMENT '项目ID',
                    funnel_date DATE NOT NULL COMMENT '漏斗日期',
                    step1_visit INT DEFAULT 0 COMMENT '步骤1: 访问',
                    step2_browse INT DEFAULT 0 COMMENT '步骤2: 浏览商品',
                    step3_cart INT DEFAULT 0 COMMENT '步骤3: 加购',
                    step4_favorite INT DEFAULT 0 COMMENT '步骤4: 收藏',
                    step5_order INT DEFAULT 0 COMMENT '步骤5: 下单',
                    step6_pay INT DEFAULT 0 COMMENT '步骤6: 支付',
                    total_amount DECIMAL(12,2) DEFAULT 0 COMMENT '当日消费金额',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_date (user_id, funnel_date),
                    INDEX idx_ec_project (ec_id, project_id),
                    INDEX idx_funnel_date (funnel_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '用户行为漏斗表';
            """)
            logger.info("✓ business_user_funnel 表创建成功")
        else:
            logger.info("[5/5] business_user_funnel 表已存在，跳过")

        logger.info("=" * 50)
        logger.info("V40.0 数据库迁移完成!")
        logger.info("=" * 50)

        # 输出新增功能汇总
        logger.info("")
        logger.info("新增表结构:")
        logger.info("  1. business_member_lifecycle - 会员生命周期阶段管理")
        logger.info("  2. business_lifecycle_strategies - 自动化触达策略")
        logger.info("  3. business_user_behaviors - 用户行为事件记录")
        logger.info("  4. business_user_profiles - 用户画像数据")
        logger.info("  5. business_user_funnel - 行为漏斗分析")
        logger.info("")
        logger.info("新增服务:")
        logger.info("  - member_lifecycle_service.py - 会员生命周期自动化")
        logger.info("  - user_behavior_service.py - 用户行为追踪分析")
        logger.info("  - cart_recommendation_service.py - 购物车智能推荐 (V40)")

        return True

    except Exception as e:
        logger.error(f"迁移失败: {e}")
        return False


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
