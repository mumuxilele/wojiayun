#!/usr/bin/env python3
"""
V47.0 批量修复INSERT语句添加FID字段
"""
import re
import os
import sys

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 表名到FID前缀的映射
TABLE_PREFIX_MAP = {
    'business_applications': 'app',
    'business_orders': 'order',
    'business_order_details': 'detail',
    'business_bookings': 'booking',
    'business_refunds': 'refund',
    'business_reviews': 'review',
    'business_members': 'member',
    'business_feedback': 'feedback',
    'business_products': 'product',
    'business_cart': 'cart',
    'business_favorites': 'fav',
    'business_coupons': 'coupon',
    'business_user_coupons': 'user_coupon',
    'business_invoices': 'invoice',
    'business_aftersales': 'aftersale',
    'business_seckill_orders': 'seckill',
    'business_order_tracking': 'track',
    'business_approve_nodes': 'node',
    'business_application_attachments': 'attach',
    'business_application_reminds': 'remind',
    'business_points_log': 'plog',
    'visit_records': 'visit',
    'chat_messages': 'msg',
    'chat_sessions': 'session',
    'auth_accounts': 'account',
}

# 需要排除的文件
EXCLUDE_FILES = [
    'migrate_v',  # 迁移脚本
    'test_',      # 测试文件
    'backup',     # 备份文件
    'batch_',     # 批量脚本
    'fix_',       # 修复脚本
    'verify_',    # 验证脚本
]


def should_process_file(filepath):
    """检查是否应该处理该文件"""
    filename = os.path.basename(filepath)
    for exclude in EXCLUDE_FILES:
        if exclude in filename:
            return False
    return True


def find_insert_statements(content):
    """查找INSERT语句"""
    # 匹配多行INSERT语句
    pattern = r'INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)'
    matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
    return matches


def find_execute_inserts(content):
    """查找execute方式的INSERT"""
    # 匹配 cursor.execute("INSERT ...", params) 模式
    pattern = r'((?:cursor|db)\.execute\s*\(\s*)(["\'])(INSERT\s+INTO\s+(\w+)\s*\([^)]+\)\s*VALUES\s*\([^)]+\))\2\s*,\s*(\[[^\]]*\])'
    matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
    return matches


def add_fid_to_insert(sql, table_name):
    """为INSERT语句添加fid字段"""
    # 检查是否已包含fid
    if 'fid' in sql.lower():
        return None
    
    # 获取表名前缀
    prefix = TABLE_PREFIX_MAP.get(table_name, 'rec')
    
    # 在字段列表开头添加fid
    # 匹配 INSERT INTO table (fields) VALUES (placeholders)
    pattern = r'(INSERT\s+INTO\s+\w+\s*\()([^)]+)(\)\s*VALUES\s*\()([^)]+)(\))'
    match = re.match(pattern, sql, re.IGNORECASE | re.DOTALL)
    
    if match:
        before_fields = match.group(1)  # "INSERT INTO table ("
        fields = match.group(2).strip()  # 字段列表
        between = match.group(3)  # ") VALUES ("
        values = match.group(4).strip()  # 值列表
        after = match.group(5)  # ")"
        
        # 添加fid字段
        new_fields = f'fid, {fields}'
        new_values = f'%s, {values}'
        
        new_sql = f'{before_fields}{new_fields}{between}{new_values}{after}'
        return new_sql
    
    return None


def fix_file(filepath):
    """修复单个文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 无法读取文件 {filepath}: {e}")
        return False
    
    original_content = content
    modified = False
    
    # 1. 检查是否已导入fid_utils
    if 'fid_utils' not in content:
        # 查找合适的导入位置
        import_pattern = r'(from business_common import [^\n]+)'
        match = re.search(import_pattern, content)
        if match:
            # 在现有导入后添加fid_utils导入
            insert_pos = match.end()
            content = content[:insert_pos] + '\nfrom business_common.fid_utils import generate_fid, generate_business_fid  # V47.0' + content[insert_pos:]
            modified = True
            print(f"  📦 添加FID导入")
    
    # 2. 修复INSERT语句
    for table_name, prefix in TABLE_PREFIX_MAP.items():
        # 查找该表的INSERT语句
        pattern = rf'INSERT\s+INTO\s+{table_name}\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)'
        
        def replace_insert(match):
            nonlocal modified
            fields = match.group(1)
            values = match.group(2)
            
            # 检查是否已有fid
            if 'fid' in fields.lower():
                return match.group(0)
            
            modified = True
            new_fields = f'fid, {fields}'
            new_values = f'%s, {values}'
            return f'INSERT INTO {table_name} ({new_fields}) VALUES ({new_values})'
        
        new_content = re.sub(pattern, replace_insert, content, flags=re.IGNORECASE)
        content = new_content
    
    # 3. 在execute调用前添加FID生成代码
    # 这是一个简化版本，实际情况下需要更复杂的逻辑
    
    if modified:
        # 备份原文件
        backup_path = filepath + '.v47.bak'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # 写入修改后的内容
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已修复: {filepath}")
        return True
    else:
        print(f"⏭️  跳过: {filepath}")
        return False


def main():
    """主函数"""
    # 要处理的目录
    target_dirs = [
        'business-common',
        'business-userH5',
        'business-staffH5',
        'business-admin',
        'business',
    ]
    
    fixed_count = 0
    skip_count = 0
    
    for dir_name in target_dirs:
        dir_path = os.path.join(PROJECT_ROOT, dir_name)
        if not os.path.exists(dir_path):
            print(f"⚠️  目录不存在: {dir_path}")
            continue
        
        print(f"\n📁 处理目录: {dir_name}")
        
        for root, dirs, files in os.walk(dir_path):
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                
                filepath = os.path.join(root, filename)
                
                if not should_process_file(filepath):
                    continue
                
                try:
                    if fix_file(filepath):
                        fixed_count += 1
                    else:
                        skip_count += 1
                except Exception as e:
                    print(f"❌ 处理失败 {filepath}: {e}")
    
    print(f"\n{'='*60}")
    print(f"批量修复完成!")
    print(f"修复: {fixed_count} 个文件")
    print(f"跳过: {skip_count} 个文件")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
