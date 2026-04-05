#!/usr/bin/env python3
"""
V11.0 数据库迁移脚本
本次迭代新增/修改：
1. business_orders 补全退款分析相关字段
2. business_shops 补全 avg_rating / review_count 字段（门店评分支持）
3. business_products 补全 view_count / favorite_count 字段（商品热度）
4. 补全 business_checkin_logs 表（签到日志，若未创建）
5. business_members 补全 last_checkin_date / checkin_streak 签到字段
6. 新增退款分析、会员增长趋势、库存预警所需的性能索引
7. 员工端操作日志表 business_staff_operation_logs（幂等）
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from business_common import config, db


def safe_alter(cursor, conn, table, column, definition, desc):
    """安全地添加字段（如果不存在）"""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        conn.commit()
        print(f"  [OK] {desc} 添加成功")
    except Exception as e:
        err = str(e)
        if '1060' in err or 'Duplicate column' in err or 'already exists' in err.lower():
            print(f"  [-] {desc} 已存在，跳过")
        else:
            print(f"  [WARN] {desc} 添加失败: {e}")


def safe_create_index(cursor, conn, table, index_name, columns, desc):
    """安全地创建索引（如果不存在）"""
    try:
        cursor.execute(f"CREATE INDEX {index_name} ON {table} ({columns})")
        conn.commit()
        print(f"  [OK] {desc} 索引创建成功")
    except Exception as e:
        err = str(e)
        if '1061' in err or 'Duplicate key name' in err:
            print(f"  [-] {desc} 索引已存在，跳过")
        else:
            print(f"  [WARN] {desc} 索引失败: {e}")


def safe_create_table(cursor, conn, ddl, table_name):
    """安全地创建表（幂等，IF NOT EXISTS）"""
    try:
        cursor.execute(ddl)
        conn.commit()
        print(f"  [OK] {table_name} 表确认存在")
    except Exception as e:
        print(f"  [WARN] {table_name}: {e}")


def migrate():
    print("=" * 60)
    print("V11.0 数据库迁移开始")
    print("=" * 60)

    conn = db.get_db()
    cursor = conn.cursor()

    # ========== 1. business_orders 退款字段补全 ==========
    print("\n[1/7] 检查 business_orders 退款字段...")
    safe_alter(cursor, conn, 'business_orders', 'refund_reason',
               "VARCHAR(500) DEFAULT NULL COMMENT '退款原因'",
               'business_orders.refund_reason')
    safe_alter(cursor, conn, 'business_orders', 'refunded_at',
               "DATETIME DEFAULT NULL COMMENT '退款完成时间'",
               'business_orders.refunded_at')
    safe_alter(cursor, conn, 'business_orders', 'refund_amount',
               "DECIMAL(10,2) DEFAULT NULL COMMENT '实际退款金额'",
               'business_orders.refund_amount')
    safe_alter(cursor, conn, 'business_orders', 'tracking_no',
               "VARCHAR(100) DEFAULT NULL COMMENT '物流单号'",
               'business_orders.tracking_no')
    safe_alter(cursor, conn, 'business_orders', 'logistics_company',
               "VARCHAR(50) DEFAULT NULL COMMENT '物流公司'",
               'business_orders.logistics_company')
    safe_alter(cursor, conn, 'business_orders', 'shipped_at',
               "DATETIME DEFAULT NULL COMMENT '发货时间'",
               'business_orders.shipped_at')
    safe_alter(cursor, conn, 'business_orders', 'completed_at',
               "DATETIME DEFAULT NULL COMMENT '完成时间'",
               'business_orders.completed_at')
    safe_alter(cursor, conn, 'business_orders', 'shipping_address',
               "TEXT DEFAULT NULL COMMENT '收货地址快照(JSON)'",
               'business_orders.shipping_address')

    # ========== 2. business_shops 评分字段 ==========
    print("\n[2/7] 检查 business_shops 评分字段...")
    safe_alter(cursor, conn, 'business_shops', 'avg_rating',
               "DECIMAL(3,2) DEFAULT 0.00 COMMENT '平均评分'",
               'business_shops.avg_rating')
    safe_alter(cursor, conn, 'business_shops', 'review_count',
               "INT DEFAULT 0 COMMENT '评价数量'",
               'business_shops.review_count')
    safe_alter(cursor, conn, 'business_shops', 'deleted',
               "TINYINT(1) DEFAULT 0 COMMENT '软删除标志'",
               'business_shops.deleted')

    # ========== 3. business_products 热度字段 ==========
    print("\n[3/7] 检查 business_products 热度字段...")
    safe_alter(cursor, conn, 'business_products', 'view_count',
               "INT DEFAULT 0 COMMENT '浏览次数'",
               'business_products.view_count')
    safe_alter(cursor, conn, 'business_products', 'favorite_count',
               "INT DEFAULT 0 COMMENT '收藏次数'",
               'business_products.favorite_count')
    safe_alter(cursor, conn, 'business_products', 'sales_count',
               "INT DEFAULT 0 COMMENT '销售数量'",
               'business_products.sales_count')

    # ========== 4. business_members 签到字段 ==========
    print("\n[4/7] 检查 business_members 签到字段...")
    safe_alter(cursor, conn, 'business_members', 'last_checkin_date',
               "DATE DEFAULT NULL COMMENT '最后签到日期'",
               'business_members.last_checkin_date')
    safe_alter(cursor, conn, 'business_members', 'checkin_streak',
               "INT DEFAULT 0 COMMENT '连续签到天数'",
               'business_members.checkin_streak')
    safe_alter(cursor, conn, 'business_members', 'total_checkin',
               "INT DEFAULT 0 COMMENT '累计签到天数'",
               'business_members.total_checkin')

    # ========== 5. 确保 business_checkin_logs 表存在 ==========
    print("\n[5/7] 确保 business_checkin_logs 表存在...")
    safe_create_table(cursor, conn, """
        CREATE TABLE IF NOT EXISTS business_checkin_logs (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
            checkin_date DATE NOT NULL COMMENT '签到日期',
            streak_day INT DEFAULT 1 COMMENT '当前连续天数',
            points_earned INT DEFAULT 1 COMMENT '本次获得积分',
            bonus_points INT DEFAULT 0 COMMENT '连续奖励积分',
            ec_id VARCHAR(64) DEFAULT NULL,
            project_id VARCHAR(64) DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_date (user_id, checkin_date),
            KEY idx_checkin_date (checkin_date),
            KEY idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户签到记录'
    """, 'business_checkin_logs')

    # ========== 6. 确保 business_staff_operation_logs 表存在 ==========
    print("\n[6/7] 确保 business_staff_operation_logs 表存在...")
    safe_create_table(cursor, conn, """
        CREATE TABLE IF NOT EXISTS business_staff_operation_logs (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            staff_id VARCHAR(64) NOT NULL COMMENT '员工ID',
            staff_name VARCHAR(100) DEFAULT NULL COMMENT '员工姓名',
            action VARCHAR(50) NOT NULL COMMENT '操作类型(ship/refund_approve/refund_reject/complete)',
            resource_type VARCHAR(50) DEFAULT NULL COMMENT '资源类型(order/booking)',
            resource_id VARCHAR(100) DEFAULT NULL COMMENT '资源ID',
            detail TEXT DEFAULT NULL COMMENT '操作详情(JSON)',
            ip_address VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
            ec_id VARCHAR(64) DEFAULT NULL,
            project_id VARCHAR(64) DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            KEY idx_staff_id (staff_id),
            KEY idx_action (action),
            KEY idx_created_at (created_at),
            KEY idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='员工操作日志'
    """, 'business_staff_operation_logs')

    # ========== 7. 退款分析 / 统计接口所需索引 ==========
    print("\n[7/7] 添加 V11.0 性能索引...")

    # 退款分析接口索引
    safe_create_index(cursor, conn, 'business_orders',
                      'idx_orders_refund_status', 'order_status, refunded_at',
                      'business_orders(order_status, refunded_at) — 退款趋势分析')
    safe_create_index(cursor, conn, 'business_orders',
                      'idx_orders_shipped_at', 'shipped_at',
                      'business_orders(shipped_at) — 发货统计')
    safe_create_index(cursor, conn, 'business_orders',
                      'idx_orders_completed_at', 'completed_at',
                      'business_orders(completed_at) — 完成统计')

    # 会员增长索引
    safe_create_index(cursor, conn, 'business_members',
                      'idx_members_created_at', 'created_at',
                      'business_members(created_at) — 会员增长趋势')
    safe_create_index(cursor, conn, 'business_members',
                      'idx_members_level', 'member_level',
                      'business_members(member_level) — 等级分布')

    # 签到统计索引
    safe_create_index(cursor, conn, 'business_checkin_logs',
                      'idx_checkin_ec_date', 'ec_id, project_id, checkin_date',
                      'business_checkin_logs(ec_id, project_id, checkin_date) — 多租户签到统计')

    # 商品库存预警索引
    safe_create_index(cursor, conn, 'business_products',
                      'idx_products_stock', 'stock, status',
                      'business_products(stock, status) — 库存预警查询')

    # 评价统计索引
    safe_create_index(cursor, conn, 'business_reviews',
                      'idx_reviews_target', 'target_type, target_id, rating',
                      'business_reviews(target_type, target_id, rating) — 评价聚合')
    safe_create_index(cursor, conn, 'business_reviews',
                      'idx_reviews_created', 'created_at, deleted',
                      'business_reviews(created_at, deleted) — 评价趋势')

    # 门店搜索索引
    safe_create_index(cursor, conn, 'business_shops',
                      'idx_shops_type_status', 'shop_type, status',
                      'business_shops(shop_type, status) — 门店筛选')

    print("\n" + "=" * 60)
    print("V11.0 数据库迁移完成！")
    print("=" * 60)
    print("""
迁移摘要:
  - business_orders: +8个退款/物流字段
  - business_shops:  +3个评分/软删除字段
  - business_products: +3个热度字段
  - business_members: +3个签到字段
  - business_checkin_logs: 表确认存在（UNIQUE key user+date）
  - business_staff_operation_logs: 新表（员工操作日志）
  - 新增性能索引: 10个
""")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    migrate()
