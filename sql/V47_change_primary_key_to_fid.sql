-- V47.0 数据库迁移脚本
-- 功能：将所有单据表的主键从自增INT/BIGINT改为VARCHAR(32)的FID
-- 执行前请务必备份数据库！
-- 执行方式: python sql/migrate_v47.py

-- ============================================
-- 第一部分：创建FID生成函数
-- ============================================

-- 删除已存在的函数
DROP FUNCTION IF EXISTS generate_fid;

-- 创建FID生成函数（32位MD5随机字符串）
DELIMITER //
CREATE FUNCTION generate_fid() RETURNS VARCHAR(32)
DETERMINISTIC
BEGIN
    RETURN LOWER(MD5(CONCAT(UUID(), RAND(), UNIX_TIMESTAMP())));
END//
DELIMITER ;

-- ============================================
-- 第二部分：单据表主键修改
-- 以下表需要修改主键结构
-- ============================================

-- 1. 申请主表 business_applications
-- 步骤1：添加新FID列
ALTER TABLE business_applications 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;

-- 步骤2：为现有数据生成FID
UPDATE business_applications SET fid = generate_fid() WHERE fid IS NULL;

-- 步骤3：删除原有主键约束（先删除外键约束）
-- 注意：需要先删除关联表的外键约束

-- 步骤4：修改FID列为非空并设为主键
ALTER TABLE business_applications 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);  -- 保留原id为唯一索引用于兼容

-- 2. 订单主表 business_orders
ALTER TABLE business_orders 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_orders SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_orders 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 3. 预约表 business_bookings
ALTER TABLE business_bookings 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_bookings SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_bookings 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 4. 退款表 business_refunds
ALTER TABLE business_refunds 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_refunds SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_refunds 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 5. 评价表 business_reviews
ALTER TABLE business_reviews 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_reviews SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_reviews 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 6. 会员表 business_members
ALTER TABLE business_members 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_members SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_members 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 7. 反馈表 business_feedback
ALTER TABLE business_feedback 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_feedback SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_feedback 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 8. 商品表 business_products
ALTER TABLE business_products 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_products SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_products 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 9. 购物车表 business_cart
ALTER TABLE business_cart 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_cart SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_cart 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 10. 收藏表 business_favorites
ALTER TABLE business_favorites 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_favorites SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_favorites 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 11. 优惠券表 business_coupons
ALTER TABLE business_coupons 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_coupons SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_coupons 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 12. 用户优惠券表 business_user_coupons
ALTER TABLE business_user_coupons 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_user_coupons SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_user_coupons 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 13. 发票表 business_invoices
ALTER TABLE business_invoices 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_invoices SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_invoices 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 14. 售后表 business_aftersales
ALTER TABLE business_aftersales 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_aftersales SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_aftersales 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 15. 秒杀订单表 business_seckill_orders
ALTER TABLE business_seckill_orders 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_seckill_orders SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_seckill_orders 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 16. 订单追踪表 business_order_tracking
ALTER TABLE business_order_tracking 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_order_tracking SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_order_tracking 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 17. 审批节点表 business_approve_nodes
ALTER TABLE business_approve_nodes 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_approve_nodes SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_approve_nodes 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 18. 申请附件表 business_application_attachments
ALTER TABLE business_application_attachments 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_application_attachments SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_application_attachments 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 19. 提醒记录表 business_application_reminds
ALTER TABLE business_application_reminds 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE business_application_reminds SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE business_application_reminds 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 20. 走访记录表 visit_records
ALTER TABLE visit_records 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE visit_records SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE visit_records 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 21. 聊天消息表 chat_messages
ALTER TABLE chat_messages 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE chat_messages SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE chat_messages 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 22. 聊天会话表 chat_sessions
ALTER TABLE chat_sessions 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE chat_sessions SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE chat_sessions 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- 23. 认证账户表 auth_accounts
ALTER TABLE auth_accounts 
ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST;
UPDATE auth_accounts SET fid = generate_fid() WHERE fid IS NULL;
ALTER TABLE auth_accounts 
MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
DROP PRIMARY KEY,
ADD PRIMARY KEY (fid),
ADD UNIQUE KEY uk_id (id);

-- ============================================
-- 第三部分：配置表修改（可选）
-- 配置类表通常不需要修改，保持自增ID即可
-- ============================================

-- 以下配置表保持原有结构：
-- business_application_types - 申请类型配置
-- business_system_config - 系统配置
-- business_user_points - 用户积分（统计表）
-- t_bdc_application - 企业应用配置
-- t_pc_employee - 员工表（已有FID字段）
-- t_csc_wotype - 工单类型配置

-- ============================================
-- 第四部分：索引优化
-- ============================================

-- 为所有表的fid字段添加索引（主键已自动添加）
-- 确保外键关联字段也有索引

-- ============================================
-- 第五部分：清理
-- ============================================

-- 删除辅助函数（可选）
-- DROP FUNCTION IF EXISTS generate_fid;
