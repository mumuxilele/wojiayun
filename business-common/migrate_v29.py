"""
V29.0 数据库迁移脚本
新增支付日志表，完善物流追踪相关表

2026-04-05
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db


def migrate():
    """执行V29.0数据库迁移"""

    print("=" * 50)
    print("开始 V29.0 数据库迁移...")
    print("=" * 50)

    # 1. 创建支付日志表
    print("\n[1/4] 创建支付日志表 business_payment_logs...")

    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_payment_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                pay_no VARCHAR(50) NOT NULL COMMENT '支付单号',
                action VARCHAR(50) NOT NULL COMMENT '操作类型: create/refund/callback_success/query',
                detail TEXT COMMENT '详细信息JSON',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_pay_no (pay_no),
                INDEX idx_action (action),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付操作日志表'
        """)
        print("  ✓ business_payment_logs 表创建成功")
    except Exception as e:
        print(f"  ✗ business_payment_logs 表创建失败: {e}")

    # 2. 检查business_payments表是否有transaction_id字段
    print("\n[2/4] 检查并添加 transaction_id 字段...")

    try:
        columns = db.get_all("SHOW COLUMNS FROM business_payments LIKE 'transaction_id'")
        if not columns:
            db.execute("""
                ALTER TABLE business_payments
                ADD COLUMN transaction_id VARCHAR(64) DEFAULT NULL COMMENT '第三方交易号' AFTER channel
            """)
            print("  ✓ transaction_id 字段添加成功")
        else:
            print("  - transaction_id 字段已存在，跳过")
    except Exception as e:
        print(f"  ✗ transaction_id 字段添加失败: {e}")

    # 3. 检查business_logistics_traces表是否存在
    print("\n[3/4] 检查物流追踪表...")

    try:
        tables = db.get_all("SHOW TABLES LIKE 'business_logistics_traces'")
        if not tables:
            db.execute("""
                CREATE TABLE IF NOT EXISTS business_logistics_traces (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    order_id BIGINT NOT NULL COMMENT '订单ID',
                    tracking_no VARCHAR(50) NOT NULL COMMENT '快递单号',
                    company_code VARCHAR(20) COMMENT '物流公司编码',
                    status TINYINT DEFAULT 0 COMMENT '物流状态: 0暂无/1揽收/2运输/3派送/4签收',
                    traces_json TEXT COMMENT '轨迹JSON',
                    last_updated DATETIME COMMENT '最后更新时间',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_order_id (order_id),
                    INDEX idx_tracking_no (tracking_no)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='物流轨迹缓存表'
            """)
            print("  ✓ business_logistics_traces 表创建成功")
        else:
            print("  - business_logistics_traces 表已存在，跳过")
    except Exception as e:
        print(f"  ✗ business_logistics_traces 表检查失败: {e}")

    # 4. 创建物流订阅回调表
    print("\n[4/4] 创建物流订阅回调表 business_logistics_subscriptions...")

    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_logistics_subscriptions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                order_id BIGINT NOT NULL COMMENT '订单ID',
                tracking_no VARCHAR(50) NOT NULL COMMENT '快递单号',
                company_code VARCHAR(20) COMMENT '物流公司编码',
                subscribe_url VARCHAR(255) COMMENT '订阅回调URL',
                status TINYINT DEFAULT 0 COMMENT '订阅状态: 0待订阅/1已订阅/2回调中/3已完成',
                callback_count INT DEFAULT 0 COMMENT '回调次数',
                last_callback_at DATETIME COMMENT '最后回调时间',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_order_id (order_id),
                INDEX idx_tracking_no (tracking_no),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='物流订阅记录表'
        """)
        print("  ✓ business_logistics_subscriptions 表创建成功")
    except Exception as e:
        print(f"  ✗ business_logistics_subscriptions 表创建失败: {e}")

    print("\n" + "=" * 50)
    print("V29.0 数据库迁移完成!")
    print("=" * 50)

    # 输出新增表清单
    print("\n新增表清单:")
    print("  - business_payment_logs: 支付操作日志表")
    print("  - business_logistics_traces: 物流轨迹缓存表")
    print("  - business_logistics_subscriptions: 物流订阅记录表")

    print("\n新增字段:")
    print("  - business_payments.transaction_id: 第三方交易号")


def rollback():
    """回滚V29.0迁移"""
    print("=" * 50)
    print("开始回滚 V29.0 数据库迁移...")
    print("=" * 50)

    try:
        db.execute("DROP TABLE IF EXISTS business_payment_logs")
        print("  ✓ business_payment_logs 表已删除")

        db.execute("DROP TABLE IF EXISTS business_logistics_traces")
        print("  ✓ business_logistics_traces 表已删除")

        db.execute("DROP TABLE IF EXISTS business_logistics_subscriptions")
        print("  ✓ business_logistics_subscriptions 表已删除")

        # 回滚字段
        try:
            db.execute("ALTER TABLE business_payments DROP COLUMN transaction_id")
            print("  ✓ transaction_id 字段已删除")
        except:
            pass

        print("\n" + "=" * 50)
        print("V29.0 回滚完成!")
        print("=" * 50)
    except Exception as e:
        print(f"回滚失败: {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rollback', action='store_true', help='回滚迁移')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
