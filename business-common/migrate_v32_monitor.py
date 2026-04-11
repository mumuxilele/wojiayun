"""
V32.0 迁移脚本 - 告警系统
- 创建告警表
"""
import logging
from . import db

logger = logging.getLogger(__name__)


def run():
    """执行迁移"""
    logger.info("开始 V32.0 告警系统迁移...")

    # 创建告警表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_alerts (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                level VARCHAR(20) NOT NULL DEFAULT 'warning' COMMENT '告警级别: info/warning/error/critical',
                title VARCHAR(200) NOT NULL COMMENT '告警标题',
                message TEXT NOT NULL COMMENT '告警内容',
                alert_data JSON DEFAULT NULL COMMENT '附加数据',
                status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '状态: active/resolved',
                resolved_by VARCHAR(64) DEFAULT NULL COMMENT '处理人',
                resolved_at DATETIME DEFAULT NULL COMMENT '解决时间',
                resolution_note VARCHAR(500) DEFAULT NULL COMMENT '处理备注',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_level (level),
                INDEX idx_status (status),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统告警表'
        """)
        logger.info("  ✓ 创建表: business_alerts")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_alerts 失败: {e}")

    logger.info("V32.0 告警系统迁移完成!")


if __name__ == '__main__':
    run()
