#!/usr/bin/env python3
"""
创建申请处理记录表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

def migrate():
    sql = """
    CREATE TABLE IF NOT EXISTS business_application_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        application_id INT NOT NULL COMMENT '申请单ID',
        action VARCHAR(50) NOT NULL COMMENT '操作类型: process(受理)/complete(完成)/reject(拒绝)/comment(备注)',
        handler_id VARCHAR(64) COMMENT '处理人ID',
        handler_name VARCHAR(100) COMMENT '处理人姓名',
        remark TEXT COMMENT '处理意见/备注',
        images TEXT COMMENT '处理时上传的图片JSON数组',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_app_id (application_id),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='申请处理记录表'
    """
    try:
        db.execute(sql)
        print("✅ 表 business_application_logs 创建成功")
        return True
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        return False

if __name__ == '__main__':
    migrate()
