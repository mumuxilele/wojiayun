-- ============================================
-- 走访台账系统 - 数据库更新脚本
-- 说明: 每次数据库结构变更时添加新的更新块
-- ============================================

USE visit_system;

-- ============================================
-- 更新001: 添加creator字段
-- 时间: 2026-03-15
-- ============================================
-- 检查creator字段是否存在，不存在则添加
-- 注意: 如果creator字段已存在，请注释掉以下SQL
-- ALTER TABLE visit_records ADD COLUMN creator VARCHAR(50) COMMENT '创建人ID' AFTER visit_time;
-- ALTER TABLE visit_records ADD INDEX idx_creator (creator);

-- ============================================
-- 更新002: 示例 - 添加新字段模板
-- 时间: YYYY-MM-DD
-- ============================================
-- ALTER TABLE visit_records ADD COLUMN new_field VARCHAR(100) COMMENT '新字段说明' AFTER visit_time;
-- ALTER TABLE visit_records ADD INDEX idx_new_field (new_field);

-- ============================================
-- 执行记录表
-- ============================================
CREATE TABLE IF NOT EXISTS db_version (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(10) NOT NULL COMMENT '版本号',
    description VARCHAR(500) COMMENT '更新描述',
    execute_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
    UNIQUE KEY uk_version (version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据库版本记录';

-- 记录本次更新
INSERT INTO db_version (version, description) VALUES ('001', '初始化: 添加creator字段')
ON DUPLICATE KEY UPDATE description = VALUES(description);
