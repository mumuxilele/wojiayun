-- V51.0: 云之家聊天机器人模块数据库表结构
-- 参照云之家开放平台 IM 接口规范设计
-- 文档: https://open.yunzhijia.com/opendocs/docs.html#/api/im/chatbot
-- 创建时间: 2026-04-25

-- =====================================================
-- 1. 聊天机器人配置表
-- =====================================================
CREATE TABLE IF NOT EXISTS yzj_chatbot_robots (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    robot_id VARCHAR(32) NOT NULL UNIQUE COMMENT '机器人唯一标识',
    robot_name VARCHAR(100) NOT NULL COMMENT '机器人显示名称',
    webhook_url VARCHAR(500) COMMENT '云之家 Webhook 推送地址',
    app_key VARCHAR(100) COMMENT '云之家开放平台 AppKey',
    app_secret VARCHAR(200) COMMENT '云之家开放平台 AppSecret',
    status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态: active-启用, inactive-禁用',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID(数据隔离)',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID(数据隔离)',
    deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记: 0-正常, 1-已删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_status (status),
    INDEX idx_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家聊天机器人配置表';

-- =====================================================
-- 2. 群组管理表
-- =====================================================
CREATE TABLE IF NOT EXISTS yzj_chatbot_groups (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    group_id VARCHAR(64) NOT NULL UNIQUE COMMENT '云之家群组ID',
    group_name VARCHAR(200) NOT NULL COMMENT '群组名称',
    member_count INT DEFAULT 0 COMMENT '群组成员数量',
    robot_id VARCHAR(32) COMMENT '绑定的机器人ID(关联yzj_chatbot_robots)',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID(数据隔离)',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID(数据隔离)',
    deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记: 0-正常, 1-已删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_robot_id (robot_id),
    INDEX idx_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家群组管理表';

-- =====================================================
-- 3. 消息模板表
-- =====================================================
CREATE TABLE IF NOT EXISTS yzj_chatbot_templates (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    template_id VARCHAR(32) NOT NULL UNIQUE COMMENT '模板唯一标识',
    template_name VARCHAR(100) NOT NULL COMMENT '模板名称',
    msg_type VARCHAR(20) NOT NULL COMMENT '消息类型: text/markdown/card/image',
    content JSON COMMENT '模板内容(JSON格式)',
    content_preview VARCHAR(200) COMMENT '内容预览(用于列表展示)',
    use_count INT DEFAULT 0 COMMENT '使用次数统计',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID(数据隔离)',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID(数据隔离)',
    deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记: 0-正常, 1-已删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_msg_type (msg_type),
    INDEX idx_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家消息模板表';

-- =====================================================
-- 4. 消息发送日志表
-- =====================================================
CREATE TABLE IF NOT EXISTS yzj_chatbot_send_logs (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    group_id VARCHAR(64) NOT NULL COMMENT '目标群组ID',
    group_name VARCHAR(200) COMMENT '群组名称(冗余存储)',
    robot_id VARCHAR(32) COMMENT '使用的机器人ID',
    msg_type VARCHAR(20) NOT NULL COMMENT '消息类型: text/markdown/card/image',
    content JSON COMMENT '消息内容(JSON格式)',
    status ENUM('pending', 'success', 'failed') DEFAULT 'pending' COMMENT '发送状态',
    response TEXT COMMENT '云之家接口响应内容',
    send_time DATETIME COMMENT '实际发送时间',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID(数据隔离)',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID(数据隔离)',
    deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记: 0-正常, 1-已删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_group_id (group_id),
    INDEX idx_robot_id (robot_id),
    INDEX idx_status (status),
    INDEX idx_send_time (send_time),
    INDEX idx_deleted (deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家消息发送日志表';

-- =====================================================
-- 5. 插入示例数据(可选)
-- =====================================================
-- INSERT INTO yzj_chatbot_robots (robot_id, robot_name, webhook_url, app_key, app_secret, status) 
-- VALUES ('bot_demo_001', '演示机器人', 'https://open.yunzhijia.com/webhook/xxx', 'app_key_xxx', 'app_secret_xxx', 'active');

-- =====================================================
-- 6. 权限说明
-- =====================================================
-- 本模块所有接口均需要管理员登录权限
-- 数据按照 ec_id 和 project_id 进行隔离
-- 所有查询操作自动过滤 deleted=0 的记录
