#!/usr/bin/env python3

db_py = '/www/wwwroot/wojiayun/business-common/db.py'

with open(db_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 get_db 函数后添加 get_connection
old_code = '''def get_db():
    """获取数据库连接（优先使用连接池）"""
    pool = _get_pool()
    if pool:
        return pool.connection()
    # fallback: 直接连接
    return pymysql.connect(**DB_CONFIG)'''

new_code = '''def get_db():
    """获取数据库连接（优先使用连接池）"""
    pool = _get_pool()
    if pool:
        return pool.connection()
    # fallback: 直接连接
    return pymysql.connect(**DB_CONFIG)

def get_connection():
    """获取数据库连接（别名，兼容旧代码）"""
    return get_db()'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(db_py, 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ 已添加 get_connection() 到 db.py')
else:
    print('❌ 未找到目标代码，尝试模糊匹配...')
    if 'def get_db():' in content:
        print('找到 get_db()')
        idx = content.find('def get_db():')
        print(content[idx:idx+200])
