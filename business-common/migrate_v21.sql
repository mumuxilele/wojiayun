-- V21.0 数据库迁移脚本
-- 功能：
--   1. 秒杀订单表 business_seckill_orders
--   2. 评价管理增强
--   3. 物流信息字段

-- 执行方式: python business-common/migrate_v21.py

-- ========== 1. 秒杀订单表 ==========
CREATE TABLE IF NOT EXISTS business_seckill_orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(32) NOT NULL UNIQUE COMMENT '秒杀订单号',
    activity_id INT NOT NULL COMMENT '秒杀活动ID',
    user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
    user_name VARCHAR(100) COMMENT '用户名',
    user_phone VARCHAR(20) COMMENT '手机号',
    product_id INT COMMENT '商品ID',
    product_name VARCHAR(200) COMMENT '商品名称',
    quantity INT DEFAULT 1 COMMENT '购买数量',
    original_price DECIMAL(10,2) DEFAULT 0 COMMENT '原价',
    seckill_price DECIMAL(10,2) DEFAULT 0 COMMENT '秒杀价',
    total_amount DECIMAL(10,2) DEFAULT 0 COMMENT '订单总额',
    discount_amount DECIMAL(10,2) DEFAULT 0 COMMENT '优惠金额',
    address_snapshot TEXT COMMENT '收货地址快照',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态 pending/paid/cancelled',
    logistics_no VARCHAR(50) COMMENT '物流单号',
    logistics_company VARCHAR(50) COMMENT '物流公司',
    ec_id VARCHAR(50) COMMENT '企业ID',
    project_id VARCHAR(50) COMMENT '项目ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    paid_at DATETIME COMMENT '支付时间',
    shipped_at DATETIME COMMENT '发货时间',
    delivered_at DATETIME COMMENT '收货时间',
    UNIQUE KEY uk_order_no (order_no),
    KEY idx_activity_id (activity_id),
    KEY idx_user_id (user_id),
    KEY idx_status (status),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='秒杀订单表';

-- ========== 2. 订单表增加物流字段 ==========
ALTER TABLE business_orders 
ADD COLUMN IF NOT EXISTS logistics_no VARCHAR(50) COMMENT '物流单号' AFTER express_company,
ADD COLUMN IF NOT EXISTS shipped_at DATETIME COMMENT '发货时间' AFTER logistics_no,
ADD COLUMN IF NOT EXISTS delivered_at DATETIME COMMENT '收货时间' AFTER shipped_at;

-- ========== 3. 评价表增强 ==========
ALTER TABLE business_reviews 
ADD COLUMN IF NOT EXISTS reply_content TEXT COMMENT '商家回复' AFTER content,
ADD COLUMN IF NOT EXISTS replied_at DATETIME COMMENT '回复时间' AFTER reply_content,
ADD COLUMN IF NOT EXISTS reply_user_id VARCHAR(50) COMMENT '回复人ID' AFTER replied_at,
ADD COLUMN IF NOT EXISTS reply_user_name VARCHAR(100) COMMENT '回复人名称' AFTER reply_user_id;

-- ========== 4. 秒杀活动库存统计视图（可选）============
-- CREATE OR REPLACE VIEW business_seckill_stock_view AS
-- SELECT 
--     p.id as activity_id,
--     p.promo_name,
--     p.total_stock,
--     p.seckill_price,
--     p.start_time,
--     p.end_time,
--     COALESCE(SUM(s.quantity), 0) as sold_count,
--     COALESCE(SUM(s.total_amount), 0) as sold_amount,
--     (p.total_stock - COALESCE(SUM(s.quantity), 0)) as remaining_stock
-- FROM business_promotions p
-- LEFT JOIN business_seckill_orders s ON p.id = s.activity_id AND s.status != 'cancelled'
-- WHERE p.promo_type = 'seckill'
-- GROUP BY p.id;

-- ========== 5. 索引优化 ==========
CREATE INDEX IF NOT EXISTS idx_seckill_orders_user ON business_seckill_orders(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_seckill_orders_activity ON business_seckill_orders(activity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_target ON business_reviews(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_orders_logistics ON business_orders(logistics_no);
