#!/usr/bin/env python3
import os, shutil

# 需要修复的目录
dirs_to_fix = [
    '/www/wwwroot/wojiayun/business-userH5',
    '/www/wwwroot/wojiayun/business-staffH5',
    '/www/wwwroot/wojiayun/business-admin',
]

for base in dirs_to_fix:
    # 检查带连字符的副本目录
    hyphen_dir = os.path.join(base, 'business_common', 'business-common')
    if os.path.exists(hyphen_dir):
        print(f'⚠️  删除重复目录: {hyphen_dir}')
        try:
            shutil.rmtree(hyphen_dir)
            print(f'✅ 已删除 {hyphen_dir}')
        except Exception as e:
            print(f'❌ 删除失败: {e}')
    else:
        print(f'✅ {base} 没有重复目录')
    
    # 确认正确的 db.py 有 get_connection
    correct_db = os.path.join(base, 'business_common', 'db.py')
    if os.path.exists(correct_db):
        with open(correct_db, 'r', encoding='utf-8') as f:
            has_conn = 'def get_connection' in f.read()
        print(f'  {"✅" if has_conn else "❌"} {correct_db} has get_connection: {has_conn}')
    else:
        print(f'  ❌ {correct_db} 不存在')

print('\n全部完成')
