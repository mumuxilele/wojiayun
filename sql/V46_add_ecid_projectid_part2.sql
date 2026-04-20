-- V46.0 数据库迁移脚本 - 第2部分
-- 配置表和其他业务表添加 ec_id 和 project_id 字段

-- 配置/基础数据表
ALTER TABLE business_application_types 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE business_system_config 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE business_user_points 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 其他业务表
ALTER TABLE auth_accounts 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE business_approve_nodes 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE business_venue_favorites 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE chat_groups 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE chat_message_reads 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE chat_messages 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE chat_sessions 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE t_pc_employee 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

ALTER TABLE t_csc_wotype 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);
