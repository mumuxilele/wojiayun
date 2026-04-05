#!/usr/bin/env python3
"""
V19.0 数据库迁移脚本
- 订单表添加退款相关字段（幂等执行）
- 申请单表添加超时提醒相关索引
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db


def migrate():
    """执行V19.0迁移"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        print("开始执行 V19.0 数据库迁移...")
        
        # 1. 检查并添加订单表退款字段
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'business_orders'
            AND COLUMN_NAME = 'refund_status'
        """)
        if not cursor.fetchone():
            print("添加 refund_status 字段到 business_orders...")
            cursor.execute("""
                ALTER TABLE business_orders 
                ADD COLUMN refund_status VARCHAR(20) DEFAULT NULL COMMENT '退款状态:pending/processing/approved/rejected'
                AFTER pay_status
            """)
            print("✓ refund_status 添加成功")
        else:
            print("✓ refund_status 已存在，跳过")
        
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'business_orders'
            AND COLUMN_NAME = 'refund_requested_at'
        """)
        if not cursor.fetchone():
            print("添加 refund_requested_at 字段到 business_orders...")
            cursor.execute("""
                ALTER TABLE business_orders 
                ADD COLUMN refund_requested_at DATETIME DEFAULT NULL COMMENT '退款申请时间'
                AFTER refund_reason
            """)
            print("✓ refund_requested_at 添加成功")
        else:
            print("✓ refund_requested_at 已存在，跳过")
        
        # 2. 添加申请单超时查询索引
        print("检查并创建申请单索引...")
        
        # 用于快速查询超时申请
        cursor.execute("""
            SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'business_applications'
            AND INDEX_NAME = 'idx_apps_status_created'
        """)
        if not cursor.fetchone():
            print("创建 idx_apps_status_created 索引...")
            cursor.execute("""
                ALTER TABLE business_applications 
                ADD INDEX idx_apps_status_created (status, created_at)
            """)
            print("✓ 索引创建成功")
        else:
            print("✓ idx_apps_status_created 已存在，跳过")
        
        # 3. 添加订单退款状态索引
        cursor.execute("""
            SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'business_orders'
            AND INDEX_NAME = 'idx_orders_refund_status'
        """)
        if not cursor.fetchone():
            print("创建 idx_orders_refund_status 索引...")
            cursor.execute("""
                ALTER TABLE business_orders 
                ADD INDEX idx_orders_refund_status (refund_status, order_status)
            """)
            print("✓ 索引创建成功")
        else:
            print("✓ idx_orders_refund_status 已存在，跳过")
        
        conn.commit()
        print("\n✅ V19.0 迁移完成！")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    migrate()
