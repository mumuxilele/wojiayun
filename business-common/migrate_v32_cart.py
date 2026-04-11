"""
V32.0 迁移脚本 - 购物车增强
- 添加 session_id 字段支持游客购物车
- 添加 selected 字段支持部分选择结算
- 优化索引支持快速查询
"""
import logging
from . import db

logger = logging.getLogger(__name__)


def run():
    """执行迁移"""
    logger.info("开始 V32.0 购物车增强迁移...")

    # 1. 检查并添加字段
    migrations = [
        # session_id: 支持游客购物车
        ("session_id", "VARCHAR(64) DEFAULT NULL COMMENT '游客会话ID'"),
        # selected: 是否选中结算
        ("selected", "TINYINT(1) DEFAULT 1 COMMENT '是否选中结算: 0-未选中, 1-选中'"),
        # ec_id, project_id: 多租户字段
        ("ec_id", "VARCHAR(64) DEFAULT NULL COMMENT '企业ID'"),
        ("project_id", "VARCHAR(64) DEFAULT NULL COMMENT '项目ID'"),
    ]

    for field, field_def in migrations:
        try:
            # 检查字段是否存在
            result = db.get_one("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'business_cart'
                AND COLUMN_NAME = %s
            """, [field])

            if result and result.get('cnt', 0) == 0:
                db.execute(f"ALTER TABLE business_cart ADD COLUMN {field} {field_def}")
                logger.info(f"  ✓ 添加字段: {field}")
            else:
                logger.info(f"  - 字段已存在: {field}")
        except Exception as e:
            logger.warning(f"  ! 添加字段 {field} 失败: {e}")

    # 2. 添加索引
    indexes = [
        ("idx_user_session", "user_id, session_id"),
        ("idx_selected", "user_id, selected"),
        ("idx_ec_project", "ec_id, project_id"),
    ]

    for idx_name, idx_cols in indexes:
        try:
            # 检查索引是否存在
            result = db.get_one("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'business_cart'
                AND INDEX_NAME = %s
            """, [idx_name])

            if result and result.get('cnt', 0) == 0:
                db.execute(f"ALTER TABLE business_cart ADD INDEX {idx_name} ({idx_cols})")
                logger.info(f"  ✓ 添加索引: {idx_name} ({idx_cols})")
            else:
                logger.info(f"  - 索引已存在: {idx_name}")
        except Exception as e:
            logger.warning(f"  ! 添加索引 {idx_name} 失败: {e}")

    # 3. 创建购物车会话表（可选，用于游客购物车持久化）
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_cart_sessions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(64) NOT NULL UNIQUE COMMENT '会话ID',
                user_id VARCHAR(64) DEFAULT NULL COMMENT '绑定用户ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                expires_at DATETIME DEFAULT NULL COMMENT '过期时间(默认7天)',
                INDEX idx_user (user_id),
                INDEX idx_session (session_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购物车会话表'
        """)
        logger.info("  ✓ 创建表: business_cart_sessions")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_cart_sessions 失败: {e}")

    logger.info("V32.0 购物车增强迁移完成!")


if __name__ == '__main__':
    run()
