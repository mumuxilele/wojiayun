#!/usr/bin/env python3
"""检查所有表是否有 ec_id 和 project_id 字段"""
import pymysql

conn = pymysql.connect(
    host='47.98.238.209',
    user='root',
    password='Wojiacloud$2023',
    database='visit_system'
)
cursor = conn.cursor()

# 业务单据表（需要添加 ec_id 和 project_id）
business_tables = [
    'business_applications',
    'business_application_attachments',
    'business_application_logs',
    'business_application_reminds',
    'business_checkin_logs',
    'business_feedback',
    'business_logistics_subscriptions',
    'business_logistics_traces',
    'business_order_items',
    'business_orders',
    'business_payment_logs',
    'business_ratings',
    'business_reviews',
    'business_user_behaviors',
    'business_user_funnel',
    'business_venue_bookings',
    'business_venue_reviews',
]

# 配置/基础数据表（可能只需要 ec_id）
config_tables = [
    'business_application_types',
    'business_coupons',
    'business_members',
    'business_notices',
    'business_points_log',
    'business_products',
    'business_shops',
    'business_system_config',
    'business_user_coupons',
    'business_user_points',
    'business_user_profiles',
    'business_venues',
]

print("=" * 80)
print("业务单据表字段检查")
print("=" * 80)

for table in business_tables:
    try:
        cursor.execute(f"DESCRIBE {table}")
        columns = [col[0] for col in cursor.fetchall()]
        has_ec_id = 'ec_id' in columns
        has_project_id = 'project_id' in columns
        status = "✅" if (has_ec_id and has_project_id) else "❌"
        print(f"{status} {table:40s} ec_id:{has_ec_id!s:5s} project_id:{has_project_id!s:5s}")
    except Exception as e:
        print(f"⚠️  {table:40s} 错误: {e}")

print("\n" + "=" * 80)
print("配置/基础数据表字段检查")
print("=" * 80)

for table in config_tables:
    try:
        cursor.execute(f"DESCRIBE {table}")
        columns = [col[0] for col in cursor.fetchall()]
        has_ec_id = 'ec_id' in columns
        has_project_id = 'project_id' in columns
        status = "✅" if has_ec_id else "❌"
        print(f"{status} {table:40s} ec_id:{has_ec_id!s:5s} project_id:{has_project_id!s:5s}")
    except Exception as e:
        print(f"⚠️  {table:40s} 错误: {e}")

# 检查其他表
print("\n" + "=" * 80)
print("其他表字段检查")
print("=" * 80)

cursor.execute("SHOW TABLES")
all_tables = [t[0] for t in cursor.fetchall()]
other_tables = set(all_tables) - set(business_tables) - set(config_tables)

for table in sorted(other_tables):
    try:
        cursor.execute(f"DESCRIBE {table}")
        columns = [col[0] for col in cursor.fetchall()]
        has_ec_id = 'ec_id' in columns
        has_project_id = 'project_id' in columns
        status = "✅" if (has_ec_id or has_project_id) else "❌"
        print(f"{status} {table:40s} ec_id:{has_ec_id!s:5s} project_id:{has_project_id!s:5s}")
    except Exception as e:
        print(f"⚠️  {table:40s} 错误: {e}")

cursor.close()
conn.close()
