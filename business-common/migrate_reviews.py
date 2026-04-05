#!/usr/bin/env python3
"""
创建评价表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

SQL = """
CREATE TABLE IF NOT EXISTS business_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '评价ID',
    user_id VARCHAR(64) NOT NULL COMMENT '评价用户ID',
    user_name VARCHAR(100) COMMENT '评价用户姓名',
    target_type VARCHAR(20) NOT NULL COMMENT '评价对象类型: venue(场地)/order(订单)/service(服务)',
    target_id INT NOT NULL COMMENT '评价对象ID',
    target_name VARCHAR(200) COMMENT '评价对象名称',
    rating TINYINT NOT NULL COMMENT '评分 1-5',
    content TEXT COMMENT '评价内容',
    images TEXT COMMENT '评价图片JSON数组',
    reply TEXT COMMENT '商家回复',
    replied_at DATETIME COMMENT '回复时间',
    ec_id VARCHAR(64) COMMENT '企业ID',
    project_id VARCHAR(64) COMMENT '项目ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    
    INDEX idx_user (user_id),
    INDEX idx_target (target_type, target_id),
    INDEX idx_ec_project (ec_id, project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评价表'
"""

def migrate():
    try:
        db.execute(SQL)
        print("✅ 评价表 business_reviews 创建成功")
        return True
    except Exception as e:
        print(f"❌ 创建评价表失败: {e}")
        return False

if __name__ == '__main__':
    migrate()
