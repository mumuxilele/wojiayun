#!/usr/bin/env python3

# 在所有 business_common 目录下添加 get_connection
import glob

for db_file in glob.glob('/www/wwwroot/wojiayun/**/business_common/db.py', recursive=True):
    with open(db_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'def get_connection' not in content:
        # 在 get_db 函数后添加
        old = '''def get_db():
    """获取数据库连接（优先使用连接池）"""
    pool = _get_pool()
    if pool:
        return pool.connection()
    # fallback: 直接连接
    return pymysql.connect(**DB_CONFIG)'''
        
        new = '''def get_db():
    """获取数据库连接（优先使用连接池）"""
    pool = _get_pool()
    if pool:
        return pool.connection()
    # fallback: 直接连接
    return pymysql.connect(**DB_CONFIG)

def get_connection():
    """获取数据库连接（别名，兼容旧代码）"""
    return get_db()'''
        
        if old in content:
            content = content.replace(old, new)
            with open(db_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'✅ 已添加 get_connection 到: {db_file}')
        else:
            print(f'⚠️ 未找到 get_db() 模式: {db_file}')
    else:
        print(f'✅ 已存在 get_connection: {db_file}')
