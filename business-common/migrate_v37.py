"""
V37.0 数据库迁移脚本
功能：积分抵扣功能相关表结构扩展

执行方式: python business-common/migrate_v37.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

def migrate():
    print("=" * 60)
    print("开始 V37.0 数据库迁移...")
    print("=" * 60)

    # ========== 1. 订单表添加积分抵扣字段 ==========
    print("\n[1/3] 订单表添加积分抵扣字段...")
    try:
        # 检查字段是否存在
        result = db.get_one("SHOW COLUMNS FROM business_orders LIKE 'points_deduction'")
        if result:
            print("  ✓ points_deduction 字段已存在，跳过")
        else:
            db.execute("""
                ALTER TABLE business_orders
                ADD COLUMN points_deduction DECIMAL(10,2) DEFAULT 0.00
                COMMENT '积分抵扣金额' AFTER discount_amount
            """)
            print("  ✓ 订单表添加 points_deduction 字段成功")
    except Exception as e:
        print(f"  ✗ 订单表修改失败: {e}")

    # ========== 2. 成长任务表 ==========
    print("\n[2/3] 创建成长任务表...")
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_growth_tasks (
                id INT PRIMARY KEY AUTO_INCREMENT,
                task_code VARCHAR(32) NOT NULL COMMENT '任务代码',
                task_name VARCHAR(64) NOT NULL COMMENT '任务名称',
                task_type VARCHAR(16) NOT NULL COMMENT '任务类型: order/checkin/review/share/invite',
                description VARCHAR(255) COMMENT '任务描述',
                target_count INT DEFAULT 1 COMMENT '目标次数',
                growth_reward INT NOT NULL DEFAULT 0 COMMENT '成长值奖励',
                points_reward INT DEFAULT 0 COMMENT '积分奖励',
                icon VARCHAR(32) DEFAULT '📋' COMMENT '任务图标',
                period_type VARCHAR(16) DEFAULT 'total' COMMENT '周期类型: total/daily/weekly',
                status TINYINT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
                ec_id INT DEFAULT 1 COMMENT '企业ID',
                project_id INT DEFAULT 1 COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_task_type (task_type),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成长任务配置表'
        """)

        # 插入默认成长任务
        default_tasks = [
            ('first_order', '完成首单', 'order', '完成您的第一笔订单', 1, 100, 50, '🛒', 'total'),
            ('order_10', '消费达人', 'order', '累计完成10笔订单', 10, 500, 200, '💎', 'total'),
            ('order_50', '超级会员', 'order', '累计完成50笔订单', 50, 2000, 500, '👑', 'total'),
            ('checkin_7', '连续签到', 'checkin', '连续签到7天', 7, 200, 100, '📅', 'weekly'),
            ('checkin_30', '签到达人', 'checkin', '累计签到30天', 30, 500, 200, '🏆', 'total'),
            ('review_5', '好评达人', 'review', '发表5条有效评价', 5, 300, 150, '⭐', 'total'),
            ('share_10', '分享达人', 'share', '分享商品10次', 10, 200, 100, '📤', 'weekly'),
            ('invite_3', '邀请好友', 'invite', '成功邀请3位好友注册', 3, 400, 200, '👥', 'total'),
        ]

        for task in default_tasks:
            try:
                db.execute("""
                    INSERT IGNORE INTO business_growth_tasks
                    (task_code, task_name, task_type, description, target_count, growth_reward, points_reward, icon, period_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, task)
            except Exception as e:
                print(f"  插入任务 {task[0]} 失败: {e}")
        print("  ✓ 成长任务表创建完成")
    except Exception as e:
        print(f"  ✗ 成长任务表创建失败: {e}")

    # ========== 3. 用户成长任务进度表 ==========
    print("\n[3/3] 创建用户成长任务进度表...")
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_user_growth_progress (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL COMMENT '用户ID',
                task_id INT NOT NULL COMMENT '任务ID',
                current_count INT DEFAULT 0 COMMENT '当前完成次数',
                status TINYINT DEFAULT 0 COMMENT '0进行中 1已完成',
                completed_at DATETIME COMMENT '完成时间',
                period_start DATE COMMENT '周期开始日期',
                period_end DATE COMMENT '周期结束日期',
                reward_claimed TINYINT DEFAULT 0 COMMENT '奖励是否已领取',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_task (user_id, task_id),
                INDEX idx_period (period_start, period_end),
                UNIQUE KEY uk_user_task_period (user_id, task_id, period_start)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户成长任务进度表'
        """)
        print("  ✓ 用户成长任务进度表创建完成")
    except Exception as e:
        print(f"  ✗ 用户成长任务进度表创建失败: {e}")

    print("\n" + "=" * 60)
    print("V37.0 数据库迁移完成！")
    print("=" * 60)

if __name__ == '__main__':
    migrate()
