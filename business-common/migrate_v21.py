#!/usr/bin/env python3
"""
V21.0 数据库迁移脚本
功能：
  1. 秒杀订单表 business_seckill_orders
  2. 订单表物流字段
  3. 评价表增强
  4. 索引优化

执行方式: python business-common/migrate_v21.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

def migrate():
    print("=" * 60)
    print("开始 V21.0 数据库迁移...")
    print("=" * 60)
    
    # ========== 1. 秒杀订单表 ==========
    print("\n[1/4] 创建秒杀订单表 business_seckill_orders...")
    try:
        db.execute("""
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='秒杀订单表'
        """)
        print("  ✓ 秒杀订单表创建完成")
    except Exception as e:
        print(f"  ✗ 创建失败: {e}")

    # ========== 2. 订单表增加物流字段 ==========
    print("\n[2/4] 为订单表添加物流字段...")
    try:
        db.execute("""
            ALTER TABLE business_orders 
            ADD COLUMN logistics_no VARCHAR(50) COMMENT '物流单号' AFTER express_company,
            ADD COLUMN shipped_at DATETIME COMMENT '发货时间' AFTER logistics_no,
            ADD COLUMN delivered_at DATETIME COMMENT '收货时间' AFTER shipped_at
        """)
        print("  ✓ 物流字段添加完成")
    except Exception as e:
        if 'Duplicate column' in str(e) or '已存在' in str(e):
            print("  ✓ 字段已存在，跳过")
        else:
            print(f"  ⚠ 警告: {e}")

    # ========== 3. 评价表增强 ==========
    print("\n[3/4] 为评价表添加商家回复字段...")
    try:
        db.execute("""
            ALTER TABLE business_reviews 
            ADD COLUMN reply_content TEXT COMMENT '商家回复' AFTER content,
            ADD COLUMN replied_at DATETIME COMMENT '回复时间' AFTER reply_content,
            ADD COLUMN reply_user_id VARCHAR(50) COMMENT '回复人ID' AFTER replied_at,
            ADD COLUMN reply_user_name VARCHAR(100) COMMENT '回复人名称' AFTER reply_user_id
        """)
        print("  ✓ 评价增强字段添加完成")
    except Exception as e:
        if 'Duplicate column' in str(e) or '已存在' in str(e):
            print("  ✓ 字段已存在，跳过")
        else:
            print(f"  ⚠ 警告: {e}")

    # ========== 4. 索引优化 ==========
    print("\n[4/4] 创建优化索引...")
    indexes = [
        ("idx_seckill_user", "business_seckill_orders", "(user_id, created_at DESC)"),
        ("idx_seckill_activity", "business_seckill_orders", "(activity_id, created_at DESC)"),
        ("idx_reviews_target", "business_reviews", "(target_type, target_id)"),
        ("idx_orders_logistics", "business_orders", "(logistics_no)"),
    ]
    for idx_name, table, cols in indexes:
        try:
            db.execute(f"CREATE INDEX {idx_name} ON {table} {cols}")
            print(f"  ✓ 索引 {idx_name} 创建完成")
        except Exception as e:
            if 'Duplicate key' in str(e) or '已存在' in str(e):
                print(f"  ✓ 索引 {idx_name} 已存在，跳过")
            else:
                print(f"  ⚠ 索引 {idx_name} 警告: {e}")

    print("\n" + "=" * 60)
    print("V21.0 数据库迁移完成!")
    print("=" * 60)
    print("\n新增表:")
    print("  - business_seckill_orders (秒杀订单表)")
    print("\n新增字段:")
    print("  - business_orders: logistics_no, shipped_at, delivered_at")
    print("  - business_reviews: reply_content, replied_at, reply_user_id, reply_user_name")
    print("\n优化索引:")
    print("  - business_seckill_orders: idx_seckill_user, idx_seckill_activity")
    print("  - business_reviews: idx_reviews_target")
    print("  - business_orders: idx_orders_logistics")

if __name__ == '__main__':
    migrate()
