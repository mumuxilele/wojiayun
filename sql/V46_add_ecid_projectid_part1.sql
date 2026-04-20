-- V46.0 数据库迁移脚本 - 第1部分
-- 业务单据表添加 ec_id 和 project_id 字段

-- 申请附件表
ALTER TABLE business_application_attachments 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 申请日志表
ALTER TABLE business_application_logs 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 申请提醒表
ALTER TABLE business_application_reminds 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 打卡记录表
ALTER TABLE business_checkin_logs 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 反馈表
ALTER TABLE business_feedback 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 物流订阅表
ALTER TABLE business_logistics_subscriptions 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 物流追踪表
ALTER TABLE business_logistics_traces 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 订单项表
ALTER TABLE business_order_items 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 支付日志表
ALTER TABLE business_payment_logs 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 评分表
ALTER TABLE business_ratings 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 场地评价表
ALTER TABLE business_venue_reviews 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID' AFTER id,
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID' AFTER ec_id,
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);

-- 走访记录表
ALTER TABLE visit_records 
ADD COLUMN ec_id VARCHAR(64) NOT NULL DEFAULT '' COMMENT '企业ID',
ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
ADD INDEX idx_ec_id (ec_id),
ADD INDEX idx_project_id (project_id);
