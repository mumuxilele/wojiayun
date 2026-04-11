"""
V35.0 数据库迁移脚本

本迁移脚本为V35.0版本的安全增强功能创建必要的数据库结构变更：

1. business_members表新增字段：
   - password_version: 密码哈希版本（1=SHA256旧版, 2=bcrypt新版）
   - login_fail_count: 连续登录失败次数
   - lock_until: 账户锁定截止时间

2. business_order_details表（如果不存在）

执行前请务必备份数据库！

用法:
    python migrate_v35.py [--check]
    python migrate_v35.py [--execute]

Author: AI产品经理
Date: 2026-04-05
"""

import sys
import os
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_migration_needed() -> bool:
    """检查是否需要进行迁移"""
    try:
        # 检查password_version字段是否存在
        result = db.get_one("SHOW COLUMNS FROM business_members LIKE 'password_version'")
        if result:
            logger.info("✓ password_version字段已存在")
            return False
        
        logger.info("需要进行V35.0迁移")
        return True
        
    except Exception as e:
        logger.error(f"检查迁移状态失败: {e}")
        return True


def get_executed_migrations() -> list:
    """获取已执行的迁移列表"""
    try:
        # 尝试从migrations表获取
        result = db.get_all("""
            SELECT migration_name FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = 'schema_migrations'
        """)
        if result:
            return [r['migration_name'] for r in result]
    except:
        pass
    
    # 如果表不存在，返回空列表
    return []


def create_migrations_table():
    """创建迁移记录表"""
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_migration_name (migration_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        logger.info("✓ schema_migrations表创建成功")
    except Exception as e:
        logger.warning(f"创建迁移记录表失败: {e}")


def record_migration(migration_name: str):
    """记录迁移"""
    try:
        db.execute(
            "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
            [migration_name]
        )
        logger.info(f"✓ 记录迁移: {migration_name}")
    except Exception as e:
        logger.warning(f"记录迁移失败: {e}")


def migrate():
    """执行V35.0迁移"""
    logger.info("=" * 60)
    logger.info("开始V35.0数据库迁移")
    logger.info("=" * 60)
    
    try:
        # 确保迁移记录表存在
        create_migrations_table()
        
        # 检查是否已执行过迁移
        executed = get_executed_migrations()
        if 'v35_member_security' in executed:
            logger.info("V35.0迁移已执行，跳过")
            return
        
        # ========== 1. 迁移business_members表 ==========
        logger.info("\n[1/3] 迁移business_members表...")
        
        # 1.1 添加password_version字段
        try:
            db.execute("""
                ALTER TABLE business_members 
                ADD COLUMN password_version TINYINT DEFAULT 1 
                COMMENT '密码版本：1-SHA256旧版, 2-bcrypt新版' 
                AFTER password
            """)
            logger.info("✓ 添加password_version字段成功")
        except Exception as e:
            if 'Duplicate column' in str(e):
                logger.info("  password_version字段已存在，跳过")
            else:
                raise
        
        # 1.2 添加login_fail_count字段
        try:
            db.execute("""
                ALTER TABLE business_members 
                ADD COLUMN login_fail_count INT DEFAULT 0 
                COMMENT '连续登录失败次数' 
                AFTER password_version
            """)
            logger.info("✓ 添加login_fail_count字段成功")
        except Exception as e:
            if 'Duplicate column' in str(e):
                logger.info("  login_fail_count字段已存在，跳过")
            else:
                raise
        
        # 1.3 添加lock_until字段
        try:
            db.execute("""
                ALTER TABLE business_members 
                ADD COLUMN lock_until DATETIME DEFAULT NULL 
                COMMENT '账户锁定截止时间' 
                AFTER login_fail_count
            """)
            logger.info("✓ 添加lock_until字段成功")
        except Exception as e:
            if 'Duplicate column' in str(e):
                logger.info("  lock_until字段已存在，跳过")
            else:
                raise
        
        # ========== 2. 创建任务队列表 ==========
        logger.info("\n[2/3] 检查任务队列相关表...")
        
        # 检查business_tasks表
        try:
            result = db.get_one("SHOW TABLES LIKE 'business_tasks'")
            if not result:
                db.execute("""
                    CREATE TABLE business_tasks (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        task_type VARCHAR(50) NOT NULL COMMENT '任务类型',
                        task_name VARCHAR(200) COMMENT '任务名称',
                        priority INT DEFAULT 5 COMMENT '优先级 1-10',
                        status ENUM('pending', 'running', 'completed', 'failed', 'cancelled') DEFAULT 'pending',
                        payload JSON COMMENT '任务参数',
                        result JSON COMMENT '执行结果',
                        error_msg TEXT COMMENT '错误信息',
                        max_retries INT DEFAULT 3 COMMENT '最大重试次数',
                        retry_count INT DEFAULT 0 COMMENT '已重试次数',
                        scheduled_at DATETIME COMMENT '计划执行时间',
                        started_at DATETIME COMMENT '开始执行时间',
                        completed_at DATETIME COMMENT '完成时间',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_status (status),
                        INDEX idx_type (task_type),
                        INDEX idx_scheduled (scheduled_at),
                        INDEX idx_priority (priority)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='异步任务队列表'
                """)
                logger.info("✓ 创建business_tasks表成功")
            else:
                logger.info("  business_tasks表已存在，跳过")
        except Exception as e:
            logger.warning(f"  创建business_tasks表失败: {e}")
        
        # ========== 3. 创建Token黑名单表 ==========
        logger.info("\n[3/3] 检查Token黑名单表...")
        
        try:
            result = db.get_one("SHOW TABLES LIKE 'business_token_blacklist'")
            if not result:
                db.execute("""
                    CREATE TABLE business_token_blacklist (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        token_jti VARCHAR(255) NOT NULL COMMENT 'Token唯一标识',
                        user_id INT NOT NULL COMMENT '用户ID',
                        revoked_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '失效时间',
                        expires_at DATETIME COMMENT 'Token原始过期时间',
                        reason VARCHAR(500) COMMENT '失效原因',
                        INDEX idx_token_jti (token_jti),
                        INDEX idx_user (user_id),
                        INDEX idx_revoked_at (revoked_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Token黑名单表'
                """)
                logger.info("✓ 创建business_token_blacklist表成功")
            else:
                logger.info("  business_token_blacklist表已存在，跳过")
        except Exception as e:
            logger.warning(f"  创建business_token_blacklist表失败: {e}")
        
        # ========== 4. 验证迁移结果 ==========
        logger.info("\n[验证] 检查迁移结果...")
        
        # 验证business_members表新字段
        columns = db.get_all("DESCRIBE business_members")
        column_names = [c['Field'] for c in columns]
        
        required_fields = ['password_version', 'login_fail_count', 'lock_until']
        all_ok = True
        
        for field in required_fields:
            if field in column_names:
                logger.info(f"  ✓ {field} 字段存在")
            else:
                logger.error(f"  ✗ {field} 字段缺失!")
                all_ok = False
        
        if all_ok:
            # 记录迁移完成
            record_migration('v35_member_security')
            logger.info("\n" + "=" * 60)
            logger.info("✓ V35.0迁移完成!")
            logger.info("=" * 60)
        else:
            logger.error("\n迁移验证失败，请检查!")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"\n✗ 迁移失败: {e}")
        raise


def rollback():
    """回滚V35.0迁移（谨慎使用）"""
    logger.warning("开始回滚V35.0迁移...")
    
    try:
        # 回滚business_members表的字段变更
        columns = db.get_all("DESCRIBE business_members")
        column_names = [c['Field'] for c in columns]
        
        if 'lock_until' in column_names:
            db.execute("ALTER TABLE business_members DROP COLUMN lock_until")
            logger.info("✓ 删除lock_until字段")
        
        if 'login_fail_count' in column_names:
            db.execute("ALTER TABLE business_members DROP COLUMN login_fail_count")
            logger.info("✓ 删除login_fail_count字段")
        
        if 'password_version' in column_names:
            db.execute("ALTER TABLE business_members DROP COLUMN password_version")
            logger.info("✓ 删除password_version字段")
        
        # 删除迁移记录
        try:
            db.execute("DELETE FROM schema_migrations WHERE migration_name='v35_member_security'")
            logger.info("✓ 删除迁移记录")
        except:
            pass
        
        logger.info("✓ 回滚完成!")
        
    except Exception as e:
        logger.error(f"回滚失败: {e}")
        raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='V35.0数据库迁移')
    parser.add_argument('--check', action='store_true', help='检查迁移状态')
    parser.add_argument('--execute', action='store_true', help='执行迁移')
    parser.add_argument('--rollback', action='store_true', help='回滚迁移')
    
    args = parser.parse_args()
    
    if args.check:
        needed = check_migration_needed()
        if needed:
            print("需要进行V35.0迁移")
            sys.exit(0)
        else:
            print("V35.0迁移已完成或无需迁移")
            sys.exit(0)
    
    elif args.rollback:
        rollback()
    
    elif args.execute or len(sys.argv) == 1:
        migrate()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
