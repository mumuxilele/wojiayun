#!/usr/bin/env python3
"""
数据库迁移脚本：为所有 business_ 表添加 ec_id 和 project_id 字段
"""
import pymysql

DB_CONFIG = {
    'host': '47.98.238.209',
    'port': 3306,
    'user': 'root',
    'password': 'Wojiacloud$2023',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

# 需要添加字段的表
TABLES_TO_MIGRATE = [
    'business_venues',
    'business_shops',
    'business_products',
    'business_coupons',
    'business_notices',
]

def migrate():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    for table in TABLES_TO_MIGRATE:
        try:
            # 检查表是否存在
            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            if not cursor.fetchone():
                print(f"表 {table} 不存在，跳过")
                continue
            
            # 检查字段是否已存在
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'ec_id'")
            has_ec = cursor.fetchone() is not None
            
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'project_id'")
            has_project = cursor.fetchone() is not None
            
            # 添加 ec_id 字段（在表末尾）
            if not has_ec:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID'")
                print(f"✓ {table} 添加 ec_id 字段")
            else:
                print(f"- {table} 已有 ec_id 字段")
            
            # 添加 project_id 字段（在表末尾）
            if not has_project:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID'")
                print(f"✓ {table} 添加 project_id 字段")
            else:
                print(f"- {table} 已有 project_id 字段")
            
            # 添加索引
            try:
                if not has_ec:
                    cursor.execute(f"ALTER TABLE {table} ADD INDEX idx_ec_id (ec_id)")
                if not has_project:
                    cursor.execute(f"ALTER TABLE {table} ADD INDEX idx_project_id (project_id)")
            except Exception as e:
                pass  # 索引可能已存在
            
            conn.commit()
            
        except Exception as e:
            print(f"✗ {table} 迁移失败: {e}")
            conn.rollback()
    
    cursor.close()
    conn.close()
    print("\n迁移完成！")

if __name__ == '__main__':
    migrate()
