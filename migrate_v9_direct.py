#!/usr/bin/env python3
"""V9.0 直接数据库迁移脚本"""

import pymysql
import os

# 数据库配置
db_config = {
    'host': os.environ.get('DB_HOST', '47.98.238.209'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'Wojiacloud$2023'),
    'database': os.environ.get('DB_NAME', 'visit_system'),
    'charset': 'utf8mb4',
}

def migrate():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("V9.0 Migration Start")
    print("=" * 60)
    
    try:
        # 1. Create checkin table
        print("\n[1/4] Creating business_checkin_logs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_checkin_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL COMMENT 'user id',
                checkin_date DATE NOT NULL COMMENT 'checkin date',
                continuous_days INT DEFAULT 1 COMMENT 'continuous days',
                reward_points INT DEFAULT 0 COMMENT 'reward points',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE KEY uk_user_date (user_id, checkin_date),
                KEY idx_user_id (user_id),
                KEY idx_checkin_date (checkin_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='user checkin logs'
        """)
        print("  [OK] business_checkin_logs created")
        
        # 2. Add columns to orders table
        print("\n[2/4] Altering business_orders table...")
        
        fields = [
            ('shipping_address', "VARCHAR(500) DEFAULT '' COMMENT 'shipping address'"),
            ('refund_reason', "VARCHAR(500) DEFAULT '' COMMENT 'refund reason'"),
            ('refunded_at', "DATETIME DEFAULT NULL COMMENT 'refund time'"),
            ('tracking_no', "VARCHAR(100) DEFAULT '' COMMENT 'tracking no'"),
            ('logistics_company', "VARCHAR(100) DEFAULT '' COMMENT 'logistics company'"),
            ('shipped_at', "DATETIME DEFAULT NULL COMMENT 'ship time'"),
            ('completed_at', "DATETIME DEFAULT NULL COMMENT 'complete time'"),
        ]
        
        for col_name, col_def in fields:
            try:
                cursor.execute(f"ALTER TABLE business_orders ADD COLUMN {col_name} {col_def}")
                print(f"  [OK] added {col_name}")
            except Exception as e:
                if 'Duplicate column' in str(e):
                    print(f"  [-] {col_name} exists, skip")
                else:
                    raise
        
        # 3. Add column to user coupons
        print("\n[3/4] Altering business_user_coupons table...")
        try:
            cursor.execute("ALTER TABLE business_user_coupons ADD COLUMN order_id BIGINT DEFAULT NULL COMMENT 'order id'")
            print("  [OK] added order_id")
        except Exception as e:
            if 'Duplicate column' in str(e):
                print("  [-] order_id exists, skip")
            else:
                raise
        
        # 4. Verify
        print("\n[4/4] Verifying...")
        
        cursor.execute("SHOW TABLES LIKE 'business_checkin_logs'")
        if cursor.fetchone():
            print("  [OK] business_checkin_logs exists")
        
        cursor.execute("DESCRIBE business_orders")
        columns = set(row[0] for row in cursor.fetchall())
        for col_name, _ in fields:
            if col_name in columns:
                print(f"  [OK] business_orders.{col_name} exists")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("V9.0 Migration Complete!")
        print("=" * 60)
        
    except Exception as e:
        conn.rollback()
        print(f"\n迁移失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    migrate()
