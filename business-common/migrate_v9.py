#!/usr/bin/env python3
"""
V9.0 数据库迁移脚本
新增表：
- business_checkin_logs 用户签到记录
修改表：
- business_orders 新增 shipping_address, refund_reason, refunded_at, tracking_no, logistics_company, shipped_at, completed_at 字段
- business_user_coupons 新增 order_id 字段（退款时回退）
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import config, db

def migrate():
    """执行V9.0数据库迁移"""
    print("=" * 60)
    print("V9.0 数据库迁移开始")
    print("=" * 60)
    
    conn = db.get_db()
    cursor = conn.cursor()
    
    try:
        # ========== 1. 创建签到记录表 ==========
        print("\n[1/4] 创建 business_checkin_logs 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_checkin_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
                checkin_date DATE NOT NULL COMMENT '签到日期',
                continuous_days INT DEFAULT 1 COMMENT '连续签到天数',
                reward_points INT DEFAULT 0 COMMENT '获得积分',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE KEY uk_user_date (user_id, checkin_date),
                KEY idx_user_id (user_id),
                KEY idx_checkin_date (checkin_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户签到记录'
        """)
        print("  ✓ business_checkin_logs 表创建成功")
        
        # ========== 2. 订单表增加字段 ==========
        print("\n[2/4] 修改 business_orders 表...")
        
        # 收货地址快照
        try:
            cursor.execute("""
                ALTER TABLE business_orders ADD COLUMN shipping_address VARCHAR(500) DEFAULT '' COMMENT '收货地址快照'
            """)
            print("  ✓ 新增 shipping_address 字段")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("  - shipping_address 字段已存在，跳过")
            else:
                raise
        
        # 退款原因
        try:
            cursor.execute("""
                ALTER TABLE business_orders ADD COLUMN refund_reason VARCHAR(500) DEFAULT '' COMMENT '退款原因'
            """)
            print("  ✓ 新增 refund_reason 字段")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("  - refund_reason 字段已存在，跳过")
            else:
                raise
        
        # 退款时间
        try:
            cursor.execute("""
                ALTER TABLE business_orders ADD COLUMN refunded_at DATETIME DEFAULT NULL COMMENT '退款完成时间'
            """)
            print("  ✓ 新增 refunded_at 字段")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("  - refunded_at 字段已存在，跳过")
            else:
                raise
        
        # 物流单号
        try:
            cursor.execute("""
                ALTER TABLE business_orders ADD COLUMN tracking_no VARCHAR(100) DEFAULT '' COMMENT '物流单号'
            """)
            print("  ✓ 新增 tracking_no 字段")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("  - tracking_no 字段已存在，跳过")
            else:
                raise
        
        # 物流公司
        try:
            cursor.execute("""
                ALTER TABLE business_orders ADD COLUMN logistics_company VARCHAR(100) DEFAULT '' COMMENT '物流公司'
            """)
            print("  ✓ 新增 logistics_company 字段")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("  - logistics_company 字段已存在，跳过")
            else:
                raise
        
        # 发货时间
        try:
            cursor.execute("""
                ALTER TABLE business_orders ADD COLUMN shipped_at DATETIME DEFAULT NULL COMMENT '发货时间'
            """)
            print("  ✓ 新增 shipped_at 字段")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("  - shipped_at 字段已存在，跳过")
            else:
                raise
        
        # 完成时间
        try:
            cursor.execute("""
                ALTER TABLE business_orders ADD COLUMN completed_at DATETIME DEFAULT NULL COMMENT '完成时间'
            """)
            print("  ✓ 新增 completed_at 字段")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("  - completed_at 字段已存在，跳过")
            else:
                raise
        
        # ========== 3. 用户优惠券表增加 order_id ==========
        print("\n[3/4] 修改 business_user_coupons 表...")
        try:
            cursor.execute("""
                ALTER TABLE business_user_coupons ADD COLUMN order_id BIGINT DEFAULT NULL COMMENT '关联订单ID'
            """)
            print("  ✓ 新增 order_id 字段")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("  - order_id 字段已存在，跳过")
            else:
                raise
        
        # ========== 4. 更新订单状态说明 ==========
        print("\n[4/4] 验证数据库状态...")
        
        # 检查表
        cursor.execute("SHOW TABLES LIKE 'business_checkin_logs'")
        if cursor.fetchone():
            print("  ✓ business_checkin_logs 表存在")
        else:
            print("  ✗ business_checkin_logs 表不存在！")
        
        # 检查字段
        cursor.execute("DESCRIBE business_orders")
        columns = [row[0] for row in cursor.fetchall()]
        for col in ['shipping_address', 'refund_reason', 'refunded_at', 'tracking_no', 'logistics_company', 'shipped_at', 'completed_at']:
            if col in columns:
                print(f"  ✓ business_orders.{col} 存在")
            else:
                print(f"  ✗ business_orders.{col} 不存在！")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("V9.0 数据库迁移完成！")
        print("=" * 60)
        print("\n新增功能摘要：")
        print("  1. 用户签到系统（business_checkin_logs）")
        print("  2. 订单退款流程（refund_reason, refunded_at）")
        print("  3. 订单发货/物流（tracking_no, logistics_company, shipped_at）")
        print("  4. 订单收货地址（shipping_address）")
        print("  5. 订单完成时间（completed_at）")
        print("  6. 优惠券关联订单（order_id）")
        
    except Exception as e:
        conn.rollback()
        print(f"\n迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


if __name__ == '__main__':
    migrate()
