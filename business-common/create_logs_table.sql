CREATE TABLE IF NOT EXISTS business_application_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL COMMENT '申请单ID',
    action VARCHAR(50) NOT NULL COMMENT '操作类型',
    handler_id VARCHAR(64) COMMENT '处理人ID',
    handler_name VARCHAR(100) COMMENT '处理人姓名',
    remark TEXT COMMENT '处理意见',
    images TEXT COMMENT '图片JSON',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_app_id (application_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
