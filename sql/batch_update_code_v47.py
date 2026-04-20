#!/usr/bin/env python3
"""
V47.0 批量代码修改脚本
自动为所有服务文件的INSERT语句添加FID生成

执行方式：
    python sql/batch_update_code_v47.py

注意：
    1. 执行前请备份代码
    2. 修改后需要人工检查
"""
import os
import re
import sys

# 需要修改的文件列表
FILES_TO_UPDATE = [
    # 核心单据服务
    'business-common/order_service.py',
    'business-common/application_service.py',
    'business-common/booking_service.py',
    'business-common/refund_service.py',
    'business-common/member_service.py',
    'business-common/review_service.py',
    'business-common/visit_service.py',
    
    # 辅助服务
    'business-common/cart_service.py',
    'business-common/coupon_service.py',
    'business-common/invoice_service.py',
    'business-common/aftersales_service.py',
    'business-common/payment_service.py',
    'business-common/notification_service.py',
    'business-common/log_service.py',
    
    # API接口层
    'business-userH5/app.py',
    'business-staffH5/app.py',
    'business-admin/app.py',
]

# 表名到业务类型的映射
TABLE_TO_BUSINESS_TYPE = {
    'business_orders': 'order',
    'business_applications': 'application',
    'business_bookings': 'booking',
    'business_refunds': 'refund',
    'business_reviews': 'review',
    'business_members': 'member',
    'business_feedback': 'feedback',
    'business_products': 'product',
    'business_cart': 'cart',
    'business_favorites': 'favorite',
    'business_coupons': 'coupon',
    'business_user_coupons': 'user_coupon',
    'business_invoices': 'invoice',
    'business_aftersales': 'aftersale',
    'business_seckill_orders': 'seckill_order',
    'business_order_tracking': 'order_tracking',
    'business_approve_nodes': 'approve_node',
    'business_application_attachments': 'app_attachment',
    'business_application_reminds': 'app_remind',
    'visit_records': 'visit',
    'chat_messages': 'chat_message',
    'chat_sessions': 'chat_session',
    'auth_accounts': 'auth_account',
}


def add_fid_import(content):
    """添加fid_utils导入"""
    if 'from business_common.fid_utils import' in content:
        return content
    if 'from .fid_utils import' in content:
        return content
    
    import_stmt = 'from .fid_utils import generate_fid, generate_business_fid  # V47.0: FID主键生成\n'
    
    # 找到最后一个import语句后添加
    lines = content.split('\n')
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i
    
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, import_stmt)
    else:
        lines.insert(0, import_stmt)
    
    return '\n'.join(lines)


def update_order_service(content):
    """特殊处理order_service.py（已手动修改）"""
    return content


def update_insert_statements(content, filepath):
    """修改INSERT语句添加FID"""
    
    # 匹配 INSERT INTO table_name (columns) VALUES
    pattern = r'INSERT INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES'
    
    def replace_insert(match):
        table_name = match.group(1)
        columns = match.group(2).strip()
        
        # 只处理业务表
        if not table_name.startswith('business_') and not table_name.startswith('visit_') and not table_name.startswith('chat_') and not table_name.startswith('auth_'):
            return match.group(0)
        
        # 如果已经有fid字段，跳过
        if 'fid' in columns:
            return match.group(0)
        
        # 添加fid列
        new_columns = f'fid, {columns}'
        return f'INSERT INTO {table_name} ({new_columns}) VALUES'
    
    return re.sub(pattern, replace_insert, content, flags=re.IGNORECASE)


def update_last_insert_id(content):
    """修改LAST_INSERT_ID()的使用"""
    # 将获取自增ID的代码改为使用fid变量
    # 注意：这是一个简单的替换，实际可能需要更复杂的逻辑
    
    pattern = r"cursor\.lastrowid|db\.get_one\(\"SELECT LAST_INSERT_ID\(\) as id\"\)"
    
    def replace_last_id(match):
        return "# V47.0: 使用fid变量替代自增ID\n            # fid已在前面生成"
    
    return re.sub(pattern, replace_last_id, content)


def process_file(filepath):
    """处理单个文件"""
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filepath)
    
    if not os.path.exists(full_path):
        print(f"⚠️  文件不存在: {filepath}")
        return False
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"❌ 读取失败 {filepath}: {e}")
        return False
    
    content = original_content
    
    # 1. 添加导入
    content = add_fid_import(content)
    
    # 2. 修改INSERT语句
    content = update_insert_statements(content, filepath)
    
    # 3. 特殊处理：order_service.py 已手动修改
    if 'order_service.py' in filepath:
        print(f"ℹ️  跳过已修改文件: {filepath}")
        return True
    
    if content != original_content:
        # 创建备份
        backup_path = full_path + '.v47.bak'
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
        except Exception as e:
            print(f"⚠️  备份失败 {filepath}: {e}")
        
        # 写入修改后的内容
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已更新: {filepath}")
            return True
        except Exception as e:
            print(f"❌ 写入失败 {filepath}: {e}")
            return False
    else:
        print(f"ℹ️  无需修改: {filepath}")
        return True


def main():
    """主函数"""
    print("=" * 60)
    print("V47.0 批量代码修改 - 添加FID主键生成")
    print("=" * 60)
    print()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for filepath in FILES_TO_UPDATE:
        if process_file(filepath):
            success_count += 1
        else:
            error_count += 1
    
    print()
    print("=" * 60)
    print("处理完成!")
    print(f"✅ 成功/跳过: {success_count}")
    print(f"❌ 失败: {error_count}")
    print("=" * 60)
    print()
    print("⚠️  注意：")
    print("   1. 请检查修改后的代码")
    print("   2. 需要手动验证INSERT语句参数是否正确")
    print("   3. 需要修改外键关联字段（如order_id -> order_fid）")
    print("   4. 备份文件保存在 .v47.bak")


if __name__ == '__main__':
    main()
