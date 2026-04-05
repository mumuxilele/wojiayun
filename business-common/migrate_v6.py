#!/usr/bin/env python3
"""
V6.0 评价系统增强 - 数据库迁移
新增功能：
1. 追评功能（追加评价）
2. 评价统计（平均分、评分分布）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

# 1. 评价表增强 - 添加追评字段
ALTER_REVIEWS_SQL = """
ALTER TABLE business_reviews 
ADD COLUMN IF NOT EXISTS append_content TEXT COMMENT '追评内容' AFTER content,
ADD COLUMN IF NOT EXISTS append_images TEXT COMMENT '追评图片JSON数组' AFTER append_content,
ADD COLUMN IF NOT EXISTS append_created_at DATETIME COMMENT '追评时间' AFTER append_images,
ADD COLUMN IF NOT EXISTS is_anonymous TINYINT DEFAULT 0 COMMENT '是否匿名 0-否 1-是' AFTER append_created_at,
ADD INDEX IF NOT EXISTS idx_rating (rating)
"""

# 2. 优惠券表增强 - 添加满减条件和有效期
ALTER_COUPONS_SQL = """
ALTER TABLE business_coupons
ADD COLUMN IF NOT EXISTS min_amount DECIMAL(10,2) DEFAULT 0 COMMENT '最低消费金额(满减条件)' AFTER discount_value,
ADD COLUMN IF NOT EXISTS valid_days INT COMMENT '领取后有效天数' AFTER valid_until,
ADD COLUMN IF NOT EXISTS total_limit INT DEFAULT 0 COMMENT '发行总量 0-不限' AFTER receive_limit,
ADD COLUMN IF NOT EXISTS received_count INT DEFAULT 0 COMMENT '已领取数量' AFTER total_limit,
ADD COLUMN IF NOT EXISTS used_count INT DEFAULT 0 COMMENT '已使用数量' AFTER received_count,
ADD COLUMN IF NOT EXISTS distribution_type VARCHAR(20) DEFAULT 'manual' COMMENT '发放方式: manual-手动/admin-管理员发放' AFTER used_count
"""

# 3. 搜索历史表（新增）
CREATE_SEARCH_HISTORY_SQL = """
CREATE TABLE IF NOT EXISTS business_search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    keyword VARCHAR(100) NOT NULL COMMENT '搜索关键词',
    search_type VARCHAR(20) COMMENT '搜索类型: venue/shop/product',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_keyword (keyword),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='搜索历史表'
"""

def migrate():
    """执行迁移"""
    results = []
    
    # 1. 增强评价表
    try:
        db.execute(ALTER_REVIEWS_SQL)
        print("✅ 评价表增强成功（追评、匿名评价）")
        results.append("评价表增强")
    except Exception as e:
        print(f"⚠️ 评价表增强: {e}")
    
    # 2. 增强优惠券表
    try:
        db.execute(ALTER_COUPONS_SQL)
        print("✅ 优惠券表增强成功（满减条件、有效期、发放策略）")
        results.append("优惠券表增强")
    except Exception as e:
        print(f"⚠️ 优惠券表增强: {e}")
    
    # 3. 创建搜索历史表
    try:
        db.execute(CREATE_SEARCH_HISTORY_SQL)
        print("✅ 搜索历史表创建成功")
        results.append("搜索历史表")
    except Exception as e:
        print(f"⚠️ 搜索历史表: {e}")
    
    print(f"\n🎉 迁移完成! 共完成 {len(results)} 项: {', '.join(results)}")
    return results

if __name__ == '__main__':
    migrate()
