-- ============================================
-- 走访台账系统 - 数据库初始化脚本
-- 创建时间: 2026-03-15
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS visit_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE visit_system;

-- ============================================
-- 走访记录表
-- ============================================
DROP TABLE IF EXISTS visit_records;

CREATE TABLE visit_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    region VARCHAR(100) COMMENT '区域地址',
    company_name VARCHAR(200) COMMENT '企业名称',
    visitor VARCHAR(50) COMMENT '走访人账号',
    visitor_name VARCHAR(50) COMMENT '走访人姓名',
    category VARCHAR(20) COMMENT '沟通事项分类:租赁/服务/物业/其他',
    content TEXT COMMENT '沟通事项',
    visit_time DATETIME COMMENT '走访时间',
    creator VARCHAR(50) COMMENT '创建人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '删除标记:0-正常,1-已删除',
    
    INDEX idx_region (region) COMMENT '区域索引',
    INDEX idx_visitor (visitor) COMMENT '走访人索引',
    INDEX idx_visit_time (visit_time) COMMENT '走访时间索引',
    INDEX idx_company_name (company_name) COMMENT '企业名称索引',
    INDEX idx_creator (creator) COMMENT '创建人索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='走访记录表';
