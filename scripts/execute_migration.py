#!/usr/bin/env python3
"""执行数据库迁移脚本"""
import pymysql
import sys

conn = pymysql.connect(
    host='47.98.238.209',
    user='root',
    password='Wojiacloud$2023',
    database='visit_system'
)
cursor = conn.cursor()

# 读取并执行SQL文件
def execute_sql_file(filepath):
    print(f"\n执行: {filepath}")
    print("=" * 60)
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # 分割SQL语句
    statements = []
    current = []
    for line in sql.split('\n'):
        line = line.strip()
        if not line or line.startswith('--'):
            continue
        current.append(line)
        if line.endswith(';'):
            statements.append(' '.join(current))
            current = []
    
    success = 0
    failed = 0
    for stmt in statements:
        if not stmt.strip():
            continue
        try:
            # 提取表名
            if 'ALTER TABLE' in stmt:
                table_name = stmt.split('ALTER TABLE')[1].split()[0].strip()
                print(f"  修改表: {table_name} ...", end=' ')
            cursor.execute(stmt)
            conn.commit()
            print("✅")
            success += 1
        except Exception as e:
            print(f"❌ 错误: {e}")
            failed += 1
            conn.rollback()
    
    print(f"\n完成: 成功 {success} 条, 失败 {failed} 条")
    return success, failed

total_success = 0
total_failed = 0

# 执行第一部分
s, f = execute_sql_file('/www/wwwroot/wojiayun/sql/V46_add_ecid_projectid_part1.sql')
total_success += s
total_failed += f

# 执行第二部分
s, f = execute_sql_file('/www/wwwroot/wojiayun/sql/V46_add_ecid_projectid_part2.sql')
total_success += s
total_failed += f

cursor.close()
conn.close()

print("\n" + "=" * 60)
print(f"迁移完成: 总计成功 {total_success} 条, 失败 {total_failed} 条")
print("=" * 60)

if total_failed > 0:
    sys.exit(1)
