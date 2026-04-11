"""
V38.0 数据库迁移脚本
创建成长任务、分享记录、评价奖励相关表

迁移内容：
1. business_growth_tasks - 成长任务配置表
2. business_user_growth_progress - 用户成长任务进度表
3. business_share_logs - 分享记录表
4. business_review_rewards - 评价积分奖励记录表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db


def migrate():
    """执行V38.0数据库迁移"""
    print("=" * 60)
    print("V38.0 数据库迁移开始")
    print("=" * 60)
    
    migrations = [
        # 成长任务配置表
        """
        CREATE TABLE IF NOT EXISTS business_growth_tasks (
            id INT PRIMARY KEY AUTO_INCREMENT,
            task_code VARCHAR(32) NOT NULL COMMENT '任务代码',
            task_name VARCHAR(64) NOT NULL COMMENT '任务名称',
            task_type VARCHAR(16) NOT NULL COMMENT 'order/checkin/review/share/invite',
            description VARCHAR(255) COMMENT '任务描述',
            target_count INT DEFAULT 1 COMMENT '目标次数',
            growth_reward INT NOT NULL COMMENT '成长值奖励',
            points_reward INT DEFAULT 0 COMMENT '积分奖励',
            icon VARCHAR(64) DEFAULT '📋' COMMENT '任务图标',
            status TINYINT DEFAULT 1 COMMENT '0禁用 1启用',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_code (task_code, ec_id, project_id),
            KEY idx_type (task_type),
            KEY idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成长任务配置表';
        """,
        
        # 用户成长任务进度表
        """
        CREATE TABLE IF NOT EXISTS business_user_growth_progress (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL COMMENT '用户ID',
            task_id INT NOT NULL COMMENT '任务ID',
            current_count INT DEFAULT 0 COMMENT '当前完成次数',
            status TINYINT DEFAULT 0 COMMENT '0进行中 1已完成',
            completed_at DATETIME COMMENT '完成时间',
            period_start DATE COMMENT '周期开始日期',
            period_end DATE COMMENT '周期结束日期',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_task (task_id),
            INDEX idx_period (period_start, period_end),
            INDEX idx_status (status),
            UNIQUE KEY uk_user_task (user_id, task_id, period_start)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户成长任务进度表';
        """,
        
        # 分享记录表
        """
        CREATE TABLE IF NOT EXISTS business_share_logs (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL COMMENT '分享用户ID',
            share_type VARCHAR(16) NOT NULL COMMENT 'share/product/order/coupon',
            target_id INT NOT NULL COMMENT '被分享对象ID',
            target_title VARCHAR(128) COMMENT '分享标题',
            share_channel VARCHAR(32) COMMENT '分享渠道: wechat/moments/friend/poster',
            click_count INT DEFAULT 0 COMMENT '点击次数',
            convert_count INT DEFAULT 0 COMMENT '转化次数(下单)',
            convert_amount DECIMAL(10,2) DEFAULT 0 COMMENT '转化金额',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_target (share_type, target_id),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分享记录表';
        """,
        
        # 评价积分奖励记录表
        """
        CREATE TABLE IF NOT EXISTS business_review_rewards (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL COMMENT '用户ID',
            review_id INT NOT NULL COMMENT '评价ID',
            order_id INT DEFAULT 0 COMMENT '关联订单ID',
            rating TINYINT NOT NULL COMMENT '评分 1-5',
            points_reward INT NOT NULL COMMENT '积分奖励',
            growth_reward INT DEFAULT 0 COMMENT '成长值奖励',
            status TINYINT DEFAULT 1 COMMENT '0已撤销 1正常',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_review (review_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评价积分奖励记录表';
        """,
        
        # business_orders 添加分享来源字段
        """
        ALTER TABLE business_orders 
        ADD COLUMN share_from_user_id INT DEFAULT 0 COMMENT '分享来源用户ID' 
        AFTER points_deduction;
        """,
        
        # business_orders 添加评价奖励字段
        """
        ALTER TABLE business_orders 
        ADD COLUMN review_reward_points INT DEFAULT 0 COMMENT '评价奖励积分' 
        AFTER share_from_user_id;
        """,
    ]
    
    success_count = 0
    failed_count = 0
    
    for i, sql in enumerate(migrations, 1):
        try:
            # 清理SQL注释和多余空白
            sql_clean = ' '.join(sql.split())
            
            # 检查是否需要执行（表是否存在等）
            if 'CREATE TABLE IF NOT EXISTS' in sql_clean:
                # 提取表名
                table_name = sql_clean.split('CREATE TABLE IF NOT EXISTS ')[1].split(' ')[0]
                # 检查表是否存在
                existing = db.get_one(f"SHOW TABLES LIKE '{table_name}'")
                if existing:
                    print(f"  [{i}/{len(migrations)}] 表 {table_name} 已存在，跳过")
                    success_count += 1
                    continue
            
            elif 'ALTER TABLE' in sql_clean:
                # 提取表名和添加的字段
                table_name = sql_clean.split('ALTER TABLE ')[1].split(' ')[0]
                # 提取字段名
                if 'ADD COLUMN' in sql_clean:
                    field_part = sql_clean.split('ADD COLUMN ')[1].split(' ')[0]
                    field_name = field_part.strip()
                    # 检查字段是否存在
                    existing = db.get_one(f"SHOW COLUMNS FROM {table_name} LIKE '{field_name}'")
                    if existing:
                        print(f"  [{i}/{len(migrations)}] 表 {table_name} 的字段 {field_name} 已存在，跳过")
                        success_count += 1
                        continue
            
            # 执行SQL
            db.execute(sql_clean)
            print(f"  [{i}/{len(migrations)}] 执行成功")
            success_count += 1
            
        except Exception as e:
            error_msg = str(e)
            # 忽略"已经存在"的错误
            if 'Duplicate' in error_msg or 'already exists' in error_msg.lower():
                print(f"  [{i}/{len(migrations)}] 已存在，跳过")
                success_count += 1
            else:
                print(f"  [{i}/{len(migrations)}] 执行失败: {error_msg}")
                failed_count += 1
    
    print("=" * 60)
    print(f"V38.0 数据库迁移完成")
    print(f"  成功: {success_count} 项")
    print(f"  失败: {failed_count} 项")
    print("=" * 60)
    
    # 插入默认成长任务数据
    if failed_count == 0:
        insert_default_tasks()
    
    return failed_count == 0


def insert_default_tasks():
    """插入默认成长任务"""
    print("\n插入默认成长任务...")
    
    tasks = [
        # ec_id=1, project_id=1 的任务
        (1, 1, 'first_order', '完成首单', 'order', '完成您的第一笔订单', 1, 50, 20, '🛒', 1),
        (1, 1, 'order_5', '完成5笔订单', 'order', '累计完成5笔订单', 5, 100, 50, '📦', 1),
        (1, 1, 'order_10', '完成10笔订单', 'order', '累计完成10笔订单', 10, 200, 100, '🎁', 1),
        (1, 1, 'checkin_3', '连续签到3天', 'checkin', '连续签到3天', 3, 30, 10, '📅', 1),
        (1, 1, 'checkin_7', '连续签到7天', 'checkin', '连续签到7天', 7, 70, 30, '🔥', 1),
        (1, 1, 'checkin_30', '连续签到30天', 'checkin', '连续签到30天', 30, 300, 100, '⭐', 1),
        (1, 1, 'review_1', '首次评价', 'review', '完成您的第一次商品评价', 1, 20, 10, '📝', 1),
        (1, 1, 'review_5', '评价达人', 'review', '累计完成5次商品评价', 5, 50, 25, '✍️', 1),
        (1, 1, 'share_3', '分享达人', 'share', '分享商品给好友3次', 3, 30, 15, '📤', 1),
        (1, 1, 'invite_1', '邀请好友', 'invite', '成功邀请1位好友注册', 1, 100, 50, '👥', 1),
        (1, 1, 'consume_500', '消费达人', 'order', '累计消费满500元', 1, 150, 75, '💰', 1),
        (1, 1, 'consume_2000', 'VIP消费者', 'order', '累计消费满2000元', 1, 500, 200, '👑', 1),
    ]
    
    for task in tasks:
        try:
            # 检查是否已存在
            existing = db.get_one(
                "SELECT id FROM business_growth_tasks WHERE task_code=%s AND ec_id=%s AND project_id=%s",
                [task[2], task[0], task[1]]
            )
            if existing:
                continue
            
            db.execute("""
                INSERT INTO business_growth_tasks 
                (ec_id, project_id, task_code, task_name, task_type, description, 
                 target_count, growth_reward, points_reward, icon, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, task)
        except Exception as e:
            print(f"  插入任务 {task[2]} 失败: {e}")
    
    print("默认成长任务插入完成")


if __name__ == '__main__':
    migrate()
