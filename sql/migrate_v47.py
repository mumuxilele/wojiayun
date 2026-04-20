#!/usr/bin/env python3
"""
V47.0 数据库迁移脚本
功能：将所有单据表的主键从自增INT/BIGINT改为VARCHAR(32)的FID

执行方式：
    python sql/migrate_v47.py

注意：此操作不可逆
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量（测试环境）
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PASSWORD'] = 'cmCC@2025!AbcD'

from business_common import db


# 需要修改主键的单据表列表
# 格式: (表名, 表注释)
TABLES_TO_MIGRATE = [
    ('business_applications', '申请主表'),
    ('business_orders', '订单主表'),
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


def get_table_count(cursor, table_name):
    """获取表数据量"""
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    return cursor.fetchone()[0]


def generate_fid():
    """生成32位MD5随机字符串"""
    import hashlib
    import uuid
    import random
    import time
    
    uuid_str = str(uuid.uuid4())
    random_str = str(random.randint(1000000000, 9999999999))
    timestamp_str = str(time.time())
    
    raw_string = f"{uuid_str}{random_str}{timestamp_str}"
    return hashlib.md5(raw_string.encode('utf-8')).hexdigest()


def migrate_table(cursor, table_name, table_comment):
    """迁移单个表"""
    print(f"\n正在处理表: {table_name} ({table_comment})")
    
    # 1. 检查表是否存在
    if not check_table_exists(cursor, table_name):
        print(f"  ⚠️ 表 {table_name} 不存在，跳过")
        return True
    
    # 2. 检查是否已存在fid列
    if check_column_exists(cursor, table_name, 'fid'):
        print(f"  ⚠️ 表 {table_name} 已存在fid列，跳过")
        return True
    
    # 3. 获取数据量
    count = get_table_count(cursor, table_name)
    print(f"  📊 表数据量: {count}")
    
    if count == 0:
        # 空表直接添加fid列并设为主键
        print(f"  📝 空表，直接修改结构...")
        cursor.execute(f"""
            ALTER TABLE `{table_name}` 
            ADD COLUMN fid VARCHAR(32) NOT NULL COMMENT '主键FID' FIRST,
            DROP PRIMARY KEY,
            ADD PRIMARY KEY (fid),
            ADD UNIQUE KEY uk_id (id)
        """)
    else:
        # 有数据的表，分步骤修改
        print(f"  📝 步骤1: 添加fid列...")
        cursor.execute(f"""
            ALTER TABLE `{table_name}` 
            ADD COLUMN fid VARCHAR(32) NULL COMMENT '主键FID' FIRST
        """)
        
        print(f"  📝 步骤2: 为现有数据生成FID...")
        # 分批处理，避免内存溢出
        batch_size = 1000
        offset = 0
        while offset < count:
            cursor.execute(f"""
                SELECT id FROM `{table_name}` 
                WHERE fid IS NULL 
                LIMIT {batch_size}
            """)
            rows = cursor.fetchall()
            
            if not rows:
                break
                
            for row in rows:
                record_id = row[0]
                new_fid = generate_fid()
                cursor.execute(f"""
                    UPDATE `{table_name}` 
                    SET fid = %s 
                    WHERE id = %s
                """, (new_fid, record_id))
            
            offset += len(rows)
            print(f"    已处理: {min(offset, count)}/{count}")
        
        print(f"  📝 步骤3: 修改主键...")
        cursor.execute(f"""
            ALTER TABLE `{table_name}` 
            MODIFY fid VARCHAR(32) NOT NULL COMMENT '主键FID',
            DROP PRIMARY KEY,
            ADD PRIMARY KEY (fid),
            ADD UNIQUE KEY uk_id (id)
        """)
    
    print(f"  ✅ 表 {table_name} 迁移完成")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("V47.0 数据库迁移 - 主键改为FID")
    print("=" * 60)
    print("\n开始迁移...")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 1. 创建FID生成函数
        print("\n📦 步骤1: 创建FID生成函数...")
        try:
            cursor.execute("DROP FUNCTION IF EXISTS generate_fid")
            cursor.execute("""
                CREATE FUNCTION generate_fid() RETURNS VARCHAR(32)
                DETERMINISTIC
                BEGIN
                    RETURN LOWER(MD5(CONCAT(UUID(), RAND(), UNIX_TIMESTAMP())));
                END
            """)
            print("  ✅ FID生成函数创建成功")
        except Exception as e:
            print(f"  ⚠️ FID生成函数创建失败（可能已存在）: {e}")
        
        # 2. 迁移所有表
        print("\n📦 步骤2: 迁移表结构...")
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for table_name, table_comment in TABLES_TO_MIGRATE:
            try:
                if migrate_table(cursor, table_name, table_comment):
                    success_count += 1
                else:
                    skip_count += 1
                conn.commit()
            except Exception as e:
                error_count += 1
                print(f"  ❌ 表 {table_name} 迁移失败: {e}")
                conn.rollback()
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("迁移完成!")
        print(f"✅ 成功: {success_count}")
        print(f"⚠️  跳过: {skip_count}")
        print(f"❌ 失败: {error_count}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
