-- 收藏表结构
-- 用于存储用户收藏的场馆、门店、商品等

CREATE TABLE IF NOT EXISTS business_favorites (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    user_name VARCHAR(100) DEFAULT '' COMMENT '用户名（冗余，便于查询）',
    target_type ENUM('venue', 'shop', 'product') NOT NULL COMMENT '收藏对象类型',
    target_id INT NOT NULL COMMENT '收藏对象ID',
    target_name VARCHAR(200) DEFAULT '' COMMENT '收藏对象名称（冗余）',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一索引：同一用户不能重复收藏同一对象
    UNIQUE KEY uk_user_target (user_id, target_type, target_id),
    -- 查询索引
    KEY idx_user_id (user_id),
    KEY idx_target (target_type, target_id),
    KEY idx_ec_project (ec_id, project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户收藏表';