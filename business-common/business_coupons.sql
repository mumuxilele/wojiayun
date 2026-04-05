-- 优惠券表结构
-- 用于管理优惠券的发放和使用

CREATE TABLE IF NOT EXISTS business_coupons (
    id INT PRIMARY KEY AUTO_INCREMENT,
    coupon_name VARCHAR(100) NOT NULL COMMENT '优惠券名称',
    coupon_type ENUM('discount', 'cash', 'points') NOT NULL COMMENT '类型：折扣券/现金券/积分券',
    discount_value DECIMAL(10,2) NOT NULL COMMENT '折扣值(如0.8表示8折)或金额',
    min_amount DECIMAL(10,2) DEFAULT 0 COMMENT '最低消费金额',
    max_discount DECIMAL(10,2) DEFAULT NULL COMMENT '最大优惠金额',
    points_cost INT DEFAULT 0 COMMENT '兑换所需积分',
    total_count INT DEFAULT 0 COMMENT '发放总量，0表示不限量',
    used_count INT DEFAULT 0 COMMENT '已使用数量',
    valid_from DATE DEFAULT NULL COMMENT '有效期开始',
    valid_until DATE DEFAULT NULL COMMENT '有效期结束',
    status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    KEY idx_status (status),
    KEY idx_valid (valid_from, valid_until),
    KEY idx_ec_project (ec_id, project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券配置表';

-- 用户优惠券关联表
CREATE TABLE IF NOT EXISTS business_user_coupons (
    id INT PRIMARY KEY AUTO_INCREMENT,
    coupon_id INT NOT NULL COMMENT '优惠券ID',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    coupon_code VARCHAR(32) NOT NULL COMMENT '优惠券码',
    status ENUM('unused', 'used', 'expired') DEFAULT 'unused' COMMENT '状态',
    used_at DATETIME DEFAULT NULL COMMENT '使用时间',
    order_id INT DEFAULT NULL COMMENT '关联订单ID',
    ec_id VARCHAR(64) DEFAULT NULL,
    project_id VARCHAR(64) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_coupon_code (coupon_code),
    KEY idx_user_status (user_id, status),
    KEY idx_coupon_id (coupon_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户优惠券表';