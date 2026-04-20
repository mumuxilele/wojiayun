-- 应用配置表 V45.0
-- 存储企业开放平台AppKey/AppSecret，用于消息推送

CREATE TABLE IF NOT EXISTS `t_bdc_application` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `ec_id` VARCHAR(64) NOT NULL COMMENT '企业ID',
    `app_key` VARCHAR(128) NOT NULL COMMENT '开放平台AppKey',
    `app_secret` VARCHAR(256) NOT NULL COMMENT '开放平台AppSecret',
    `app_name` VARCHAR(100) DEFAULT NULL COMMENT '应用名称',
    `status` TINYINT DEFAULT 1 COMMENT '状态：1-启用，0-禁用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_ec_id` (`ec_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='企业应用配置表';

-- 初始数据示例（根据实际情况修改）
-- INSERT INTO `t_bdc_application` (`ec_id`, `app_key`, `app_secret`, `app_name`) 
-- VALUES ('enterprise_001', 'your_app_key', 'your_app_secret', '测试应用');
