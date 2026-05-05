-- 商品分类表（支持三级类目）
-- 执行此SQL创建分类表

CREATE TABLE IF NOT EXISTS business_product_categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '分类名称',
    parent_id INT DEFAULT 0 COMMENT '父级ID，0表示一级分类',
    level INT DEFAULT 1 COMMENT '层级：1一级 2二级 3三级',
    sort_order INT DEFAULT 0 COMMENT '排序（数字越小越靠前）',
    icon VARCHAR(255) DEFAULT NULL COMMENT '图标URL',
    status TINYINT DEFAULT 1 COMMENT '状态：1启用 0禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted TINYINT DEFAULT 0 COMMENT '软删除：0正常 1已删除',
    INDEX idx_parent (parent_id),
    INDEX idx_level (level),
    INDEX idx_status (status, deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';

-- 示例数据（可选）
INSERT INTO business_product_categories (name, parent_id, level, sort_order) VALUES
('生鲜果蔬', 0, 1, 1),
('日用百货', 0, 1, 2),
('休闲食品', 0, 1, 3),
('水果', 1, 2, 1),
('蔬菜', 1, 2, 2),
('苹果', 4, 3, 1),
('香蕉', 4, 3, 2);
