#!/usr/bin/env python3
"""
数据库更新脚本
自动执行SQL更新文件
"""
import pymysql
import os
import sys

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def get_current_version(db):
    """获取当前数据库版本"""
    cursor = db.cursor()
    try:
        cursor.execute("SELECT version FROM db_version ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else '0'
    except:
        return '0'

def check_column_exists(db, table, column):
    """检查列是否存在"""
    cursor = db.cursor()
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = '{DB_CONFIG['database']}' 
        AND TABLE_NAME = '{table}' 
        AND COLUMN_NAME = '{column}'
    """)
    return cursor.fetchone()[0] > 0

def add_creator_field(db):
    """添加creator字段"""
    if not check_column_exists(db, 'visit_records', 'creator'):
        cursor = db.cursor()
        cursor.execute("ALTER TABLE visit_records ADD COLUMN creator VARCHAR(50) COMMENT '创建人ID' AFTER visit_time")
        cursor.execute("ALTER TABLE visit_records ADD INDEX idx_creator (creator)")
        db.commit()
        print("✓ 已添加creator字段")
        return True
    else:
        print("✓ creator字段已存在，跳过")
        return False

def main():
    print("=" * 50)
    print("走访台账系统 - 数据库更新")
    print("=" * 50)
    
    # 检查并创建数据库
    try:
        db = pymysql.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'], password=DB_CONFIG['password'])
        cursor = db.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS visit_system DEFAULT CHARACTER SET utf8mb4")
        db.commit()
        print("✓ 数据库检查完成")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return
    
    # 切换到目标数据库
    db = get_db()
    
    # 检查并创建版本记录表
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS db_version (
            id INT AUTO_INCREMENT PRIMARY KEY,
            version VARCHAR(10) NOT NULL,
            description VARCHAR(500),
            execute_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_version (version)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    db.commit()
    
    # 执行更新
    print("\n执行更新...")
    
    # 更新001: 添加creator字段
    if add_creator_field(db):
        cursor.execute("INSERT INTO db_version (version, description) VALUES ('001', '添加creator字段')")
        db.commit()
    
    print("\n" + "=" * 50)
    print("更新完成!")
    print("=" * 50)
    
    cursor.close()
    db.close()

if __name__ == '__main__':
    main()
