-- ============================================
-- 数据库索引优化脚本
-- 创建时间: 2026-03-30
-- 说明: 为高频查询添加复合索引，提升查询性能
-- ============================================

USE visit_system;

-- ============================================
-- business_applications 表索引
-- ============================================
-- 用户申请列表查询优化（user_id + status + deleted）
CREATE INDEX idx_app_user_status ON business_applications(user_id, status, deleted) COMMENT '用户申请查询';

-- 管理端列表查询优化（ec_id + project_id + status + deleted）
CREATE INDEX idx_app_ec_project_status ON business_applications(ec_id, project_id, status, deleted) COMMENT '管理端申请查询';

-- 时间范围查询优化（created_at）
CREATE INDEX idx_app_created_at ON business_applications(created_at) COMMENT '申请时间索引';

-- ============================================
-- business_orders 表索引
-- ============================================
-- 用户订单列表查询优化（user_id + order_status + deleted）
CREATE INDEX idx_order_user_status ON business_orders(user_id, order_status, deleted) COMMENT '用户订单查询';

-- 管理端订单查询优化（ec_id + project_id + order_status + deleted）
CREATE INDEX idx_order_ec_project_status ON business_orders(ec_id, project_id, order_status, deleted) COMMENT '管理端订单查询';

-- 支付状态查询优化（pay_status + deleted）
CREATE INDEX idx_order_pay_status ON business_orders(pay_status, deleted) COMMENT '支付状态索引';

-- ============================================
-- business_venue_bookings 表索引
-- ============================================
-- 场地预约查询优化（venue_id + book_date + status）
CREATE INDEX idx_booking_venue_date_status ON business_venue_bookings(venue_id, book_date, status, deleted) COMMENT '场地预约查询';

-- 用户预约查询优化（user_id + deleted）
CREATE INDEX idx_booking_user ON business_venue_bookings(user_id, deleted) COMMENT '用户预约查询';

-- 管理端预约查询优化（ec_id + project_id + status）
CREATE INDEX idx_booking_ec_project_status ON business_venue_bookings(ec_id, project_id, status, deleted) COMMENT '管理端预约查询';

-- 时段冲突检测优化（venue_id + book_date + start_time + end_time）
CREATE INDEX idx_booking_time_range ON business_venue_bookings(venue_id, book_date, start_time, end_time) COMMENT '时段范围索引';

-- ============================================
-- business_members 表索引
-- ============================================
-- 会员查询优化（user_id）
CREATE INDEX idx_member_user ON business_members(user_id) COMMENT '用户索引';

-- 手机号查询优化（phone）
CREATE INDEX idx_member_phone ON business_members(phone) COMMENT '手机号索引';

-- 管理端会员查询优化（ec_id + project_id + member_level）
CREATE INDEX idx_member_ec_project_level ON business_members(ec_id, project_id, member_level) COMMENT '管理端会员查询';

-- ============================================
-- business_points_log 表索引
-- ============================================
-- 用户积分记录查询优化（user_id + created_at）
CREATE INDEX idx_points_user_date ON business_points_log(user_id, created_at) COMMENT '用户积分记录查询';

-- 管理端积分记录查询优化（ec_id + project_id + log_type）
CREATE INDEX idx_points_ec_project_type ON business_points_log(ec_id, project_id, log_type, created_at) COMMENT '管理端积分记录查询';

-- ============================================
-- business_shops 表索引
-- ============================================
-- 门店查询优化（shop_type + status + deleted）
CREATE INDEX idx_shop_type_status ON business_shops(shop_type, status, deleted) COMMENT '门店类型查询';

-- 管理端门店查询优化（ec_id + project_id + status）
CREATE INDEX idx_shop_ec_project_status ON business_shops(ec_id, project_id, status, deleted) COMMENT '管理端门店查询';

-- ============================================
-- business_venues 表索引
-- ============================================
-- 场地查询优化（venue_type + status + deleted）
CREATE INDEX idx_venue_type_status ON business_venues(venue_type, status, deleted) COMMENT '场地类型查询';

-- 管理端场地查询优化（ec_id + project_id + status）
CREATE INDEX idx_venue_ec_project_status ON business_venues(ec_id, project_id, status, deleted) COMMENT '管理端场地查询';

-- ============================================
-- business_application_logs 表索引
-- ============================================
-- 申请处理记录查询优化（application_id + created_at）
CREATE INDEX idx_applog_app_created ON business_application_logs(application_id, created_at) COMMENT '申请处理记录查询';

-- ============================================
-- 执行完成提示
-- ============================================
SELECT '索引创建完成' AS message;
