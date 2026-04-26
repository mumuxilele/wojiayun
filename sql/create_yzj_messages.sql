CREATE TABLE IF NOT EXISTS yzj_messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键自增ID',
    msg_type VARCHAR(32) NOT NULL DEFAULT 'text' COMMENT '消息类型: text/image/file/system',
    sender VARCHAR(64) NOT NULL DEFAULT '' COMMENT '发送者标识',
    content TEXT NOT NULL COMMENT '消息内容',
    extra_data TEXT DEFAULT NULL COMMENT '附加数据(JSON)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_msg_type (msg_type),
    INDEX idx_sender (sender),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='YZJ频道消息表';
