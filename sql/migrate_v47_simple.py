#!/usr/bin/env python3
"""
V47.0 数据库迁移脚本 - 简化版
功能：将所有单据表的主键从自增INT/BIGINT改为VARCHAR(32)的FID
"""
import pymysql
import hashlib
import uuid
import random
import time

# 数据库配置
DB_CONFIG = {
    'host': '47.98.238.209',
    'port': 3306,
    'user': 'root',
    'password': 'Wojiacloud$2023',
    'database': 'visit_system',
    'charset': 'utf8mb4'
}

# 需要修改主键的单据表列表
TABLES_TO_MIGRATE = [
    ('business_applications', '申请主表'),
    ('business_orders', '订单主表'),
    ('business_order_details', '订单明细表'),
    ('business_bookings', '预约表'),
    ('business_refunds', '退款表'),
    ('business_reviews', '评价表'),
    ('business_members', '会员表'),
    ('business_feedback', '反馈表'),
    ('business_products', '商品表'),
    ('business_cart', '购物车表'),
    ('business_favorites', '收藏表'),
    ('business_coupons', '优惠券表'),
    ('business_user_coupons', '用户优惠券表'),
    ('business_invoices', '发票表'),
    ('business_aftersales', '售后表'),
    ('business_seckill_orders', '秒杀订单表'),
    ('business_order_tracking', '订单追踪表'),
    ('business_approve_nodes', '审批节点表'),
    ('business_application_attachments', '申请附件表'),
    ('business_application_reminds', '提醒记录表'),
    ('visit_records', '走访记录表'),
    ('chat_messages', '聊天消息表'),
    ('chat_sessions', '聊天会话表'),
    ('auth_accounts', '认证账户表'),
]


def generate_fid():
    """生成32位MD5随机字符串"""
    uuid_str = str(uuid.uuid4())
    random_str = str(random.randint(1000000000, 9999999999))
    timestamp_str = str(time.time())
    raw_string = f"{uuid_str}{random_str}{timestamp_str}"
    return hashlib.md5(raw_string.encode('utf-8')).hexdigest()


def check_table_exists(cursor, table_name):
    """检查表是否存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = DATABASE() AND table_name = %s
    """, (table_name,))
    return cursor.fetchone()[0] > 0


def check_column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_schema = DATABASE() 
        AND table_name = %s 
        AND column_name = %s
    """, (table_name, column_name))
    return cursor.fetchone()[0] > 0


def migrate_table(conn, cursor, table_name, table_comment):
    """迁移单个表"""
    print(f"\n📦 处理表: {table_name} ({table_comment})")
    
    # 1. 检查表是否存在
    if not check_table_exists(cursor, table_name):
        print(f"  ⚠️ 表 {table_name} 不存在，跳过")
        return True
    
    # 2. 检查是否已迁移（已有fid字段）
    if check_column_exists(cursor, table_name, 'fid'):
        print(f"  ✅ 表 {table_name} 已存在fid字段，跳过")
        return True
    
    try:
        # 3. 添加fid字段
        print(f"  📝 添加fid字段...")
        cursor.execute(f"""
            ALTER TABLE `{table_name}` 
            ADD COLUMN `fid` VARCHAR(32) NULL COMMENT '主键FID' FIRST
        """)
        
        # 4. 为现有数据生成FID
        print(f"  📝 为现有数据生成FID...")
        cursor.execute(f"SELECT `id` FROM `{table_name}`")
        rows = cursor.fetchall()
        
        for row in rows:
            old_id = row[0]
            new_fid = generate_fid()
            cursor.execute(
                f"UPDATE `{table_name}` SET `fid` = %s WHERE `id` = %s",
                (new_fid, old_id)
            )
        
        # 5. 设置fid为NOT NULL
        print(f"  📝 设置fid为NOT NULL...")
        cursor.execute(f"ALTER TABLE `{table_name}` MODIFY `fid` VARCHAR(32) NOT NULL COMMENT '主键FID'")
        
        # 6. 删除原主键，添加fid的主键约束
        print(f"  📝 删除原主键，添加fid主键...")
        cursor.execute(f"ALTER TABLE `{table_name}` DROP PRIMARY KEY")
        cursor.execute(f"ALTER TABLE `{table_name}` ADD PRIMARY KEY (`fid`)")
        
        # 7. 保留原id字段，添加唯一索引
        print(f"  📝 为原id字段添加唯一索引...")
        cursor.execute(f"ALTER TABLE `{table_name}` ADD UNIQUE INDEX `uk_id` (`id`)")
        
        # 8. 添加fid索引
        print(f"  📝 添加fid索引...")
        cursor.execute(f"ALTER TABLE `{table_name}` ADD INDEX `idx_fid` (`fid`)")
        
        conn.commit()
        print(f"  ✅ 表 {table_name} 迁移成功")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"  ❌ 表 {table_name} 迁移失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("V47.0 数据库迁移 - 主键改为FID (简化版)")
    print("=" * 60)
    print("\n开始迁移...")
    
    conn = None
    try:
        # 连接数据库
        print("\n🔗 连接数据库...")
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("  ✅ 数据库连接成功")
        
        # 迁移所有表
        print("\n📦 开始迁移表结构...")
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for table_name, table_comment in TABLES_TO_MIGRATE:
            try:
                if migrate_table(conn, cursor, table_name, table_comment):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"  ❌ 表 {table_name} 异常: {e}")
                error_count += 1
        
        # 输出统计
        print("\n" + "=" * 60)
        print("迁移完成!")
        print("=" * 60)
        print(f"成功: {success_count} 个表")
        print(f"跳过: {skip_count} 个表")
        print(f"失败: {error_count} 个表")
        
        cursor.close()
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    main()
