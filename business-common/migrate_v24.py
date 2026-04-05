#!/usr/bin/env python3
"""
V24.0 数据库迁移脚本
主要变更:
1. 拼团活动表
2. 拼团订单表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db


def migrate():
    """执行迁移"""
    print("开始 V24.0 数据库迁移...")

    # 1. 创建拼团活动表
    create_group_activities_table()
    
    # 2. 创建拼团订单表
    create_group_orders_table()

    print("V24.0 数据库迁移完成!")


def create_group_activities_table():
    """创建拼团活动表"""
    print("创建 business_group_activities 表...")
    
    # 检查表是否存在
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_group_activities'
    """)
    
    if check and check['cnt'] > 0:
        print("  business_group_activities 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_group_activities (
            id INT AUTO_INCREMENT PRIMARY KEY,
            activity_no VARCHAR(30) NOT NULL UNIQUE COMMENT '活动编号',
            name VARCHAR(100) NOT NULL COMMENT '活动名称',
            product_id INT NOT NULL COMMENT '商品ID',
            product_name VARCHAR(100) COMMENT '商品名称',
            product_image VARCHAR(500) COMMENT '商品图片',
            original_price DECIMAL(10,2) DEFAULT 0.00 COMMENT '原价',
            group_price DECIMAL(10,2) NOT NULL COMMENT '拼团价',
            min_people INT DEFAULT 2 COMMENT '最小成团人数',
            max_people INT DEFAULT 100 COMMENT '最大参与人数',
            current_people INT DEFAULT 0 COMMENT '当前参与人数',
            valid_hours INT DEFAULT 24 COMMENT '有效时长(小时)',
            start_time DATETIME COMMENT '开始时间',
            end_time DATETIME COMMENT '结束时间',
            status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/ongoing/success/failed/cancelled',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            created_by VARCHAR(50) COMMENT '创建人',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted TINYINT DEFAULT 0,
            INDEX idx_activity_no (activity_no),
            INDEX idx_status (status),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='拼团活动表'
    """)
    print("  business_group_activities 表创建成功")


def create_group_orders_table():
    """创建拼团订单表"""
    print("创建 business_group_orders 表...")
    
    check = db.get_one("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'business_group_orders'
    """)
    
    if check and check['cnt'] > 0:
        print("  business_group_orders 表已存在，跳过")
        return

    db.execute("""
        CREATE TABLE business_group_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_no VARCHAR(30) NOT NULL UNIQUE COMMENT '订单编号',
            activity_no VARCHAR(30) NOT NULL COMMENT '活动编号',
            activity_name VARCHAR(100) COMMENT '活动名称',
            product_id INT NOT NULL COMMENT '商品ID',
            product_name VARCHAR(100) COMMENT '商品名称',
            product_image VARCHAR(500) COMMENT '商品图片',
            group_price DECIMAL(10,2) NOT NULL COMMENT '拼团价',
            user_id INT NOT NULL COMMENT '用户ID',
            user_name VARCHAR(50) COMMENT '用户名',
            user_phone VARCHAR(20) COMMENT '用户电话',
            address_info TEXT COMMENT '地址信息JSON',
            pay_no VARCHAR(50) COMMENT '支付单号',
            status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/paid/refunded/cancelled',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted TINYINT DEFAULT 0,
            INDEX idx_order_no (order_no),
            INDEX idx_activity_no (activity_no),
            INDEX idx_user_id (user_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='拼团订单表'
    """)
    print("  business_group_orders 表创建成功")


def rollback():
    """回滚迁移"""
    print("开始回滚 V24.0 数据库迁移...")
    
    try:
        db.execute("DROP TABLE IF EXISTS business_group_orders")
        print("  business_group_orders 表已删除")
        
        db.execute("DROP TABLE IF EXISTS business_group_activities")
        print("  business_group_activities 表已删除")
        
        print("V24.0 回滚完成!")
    except Exception as e:
        print(f"回滚失败: {e}")


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        rollback()
    else:
        migrate()