#!/usr/bin/env python3
"""
修复数据库表缺失字段
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business_common import db

def check_and_add_columns():
    """检查并添加缺失的数据库字段"""
    print("=" * 60)
    print("数据库字段修复工具")
    print("=" * 60)
    
    # 1. 修复 business_favorites 表 - 添加 target_name 字段
    print("\n[1/3] 检查 business_favorites 表...")
    try:
        columns = db.get_all("SHOW COLUMNS FROM business_favorites")
        column_names = [col['Field'] for col in columns or []]
        
        if 'target_name' not in column_names:
            print("  添加 target_name 字段...")
            db.execute("""
                ALTER TABLE business_favorites 
                ADD COLUMN target_name VARCHAR(200) DEFAULT '' COMMENT '收藏对象名称（冗余）'
            """)
            print("  ✓ target_name 字段添加成功")
        else:
            print("  ✓ target_name 字段已存在")
    except Exception as e:
        print(f"  ✗ business_favorites 修复失败: {e}")
    
    # 2. 检查 business_user_coupons 表结构
    print("\n[2/3] 检查 business_user_coupons 表...")
    try:
        columns = db.get_all("SHOW COLUMNS FROM business_user_coupons")
        print(f"  表字段数: {len(columns) if columns else 0}")
        
        # 检查需要的字段
        column_names = [col['Field'] for col in columns or []]
        print(f"  字段列表: {column_names}")
    except Exception as e:
        print(f"  ✗ 检查失败: {e}")
    
    # 3. 检查 business_coupons 表结构
    print("\n[3/3] 检查 business_coupons 表...")
    try:
        columns = db.get_all("SHOW COLUMNS FROM business_coupons")
        print(f"  表字段数: {len(columns) if columns else 0}")
        
        column_names = [col['Field'] for col in columns or []]
        print(f"  字段列表: {column_names}")
    except Exception as e:
        print(f"  ✗ 检查失败: {e}")
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)

if __name__ == '__main__':
    check_and_add_columns()
