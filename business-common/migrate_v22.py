"""
V22.0 数据库迁移脚本
新增:
  - business_logistics_traces 表 (物流轨迹缓存)
  - business_orders.full_text_index (商品搜索)

author: AI
date: 2026-04-04
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db


def migrate_v22():
    """V22.0 数据迁移"""
    print("=" * 50)
    print("开始 V22.0 数据库迁移...")
    print("=" * 50)

    conn = db.get_db()
    cursor = conn.cursor()
    migrated = []

    try:
        # 1. 创建物流轨迹缓存表
        print("\n[1/2] 创建物流轨迹缓存表...")

        # 检查表是否存在
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name = 'business_logistics_traces'
        """)
        table_exists = cursor.fetchone()[0] > 0

        if not table_exists:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS business_logistics_traces (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL COMMENT '订单ID',
                    tracking_no VARCHAR(50) NOT NULL COMMENT '快递单号',
                    company_code VARCHAR(32) COMMENT '物流公司编码',
                    status TINYINT DEFAULT 0 COMMENT '物流状态: 0暂无/1揽收/2运输/3派送/4签收/5拒收/6退回',
                    traces_json TEXT COMMENT '物流轨迹JSON',
                    last_updated DATETIME COMMENT '最后更新时间',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_order_id (order_id),
                    INDEX idx_tracking_no (tracking_no),
                    INDEX idx_status (status),
                    INDEX idx_last_updated (last_updated)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='物流轨迹缓存表'
            """)
            print("  ✓ business_logistics_traces 表创建成功")
            migrated.append("business_logistics_traces")
        else:
            print("  ○ business_logistics_traces 表已存在，跳过")

        # 2. 创建搜索历史表
        print("\n[2/3] 创建搜索历史表...")

        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name = 'business_search_history'
        """)
        history_exists = cursor.fetchone()[0] > 0

        if not history_exists:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS business_search_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL COMMENT '用户ID',
                    keyword VARCHAR(100) NOT NULL COMMENT '搜索关键词',
                    ec_id INT COMMENT '企业ID',
                    project_id INT COMMENT '项目ID',
                    searched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_keyword (keyword),
                    INDEX idx_searched_at (searched_at),
                    INDEX idx_user_keyword (user_id, keyword)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户搜索历史'
            """)
            print("  ✓ business_search_history 表创建成功")
            migrated.append("business_search_history")
        else:
            print("  ○ business_search_history 表已存在，跳过")

        # 3. 为 business_products 添加 FULLTEXT 索引 (搜索增强)
        print("\n[3/3] 添加商品全文索引...")

        # 检查是否已有FULLTEXT索引
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
            AND table_name = 'business_products'
            AND index_name = 'ft_product_search'
        """)
        ft_exists = cursor.fetchone()[0] > 0

        if not ft_exists:
            try:
                # MySQL 5.6+ 支持InnoDB全文索引
                cursor.execute("""
                    CREATE FULLTEXT INDEX ft_product_search
                    ON business_products(name, description, tags)
                """)
                print("  ✓ 全文索引 ft_product_search 创建成功")
                migrated.append("ft_product_search")
            except Exception as e:
                if 'doesn\'t support FULLTEXT' in str(e):
                    print("  ⚠ InnoDB不支持FULLTEXT，尝试MyISAM...")
                    # 备选方案: 创建辅助搜索表
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS business_product_search (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            product_id INT NOT NULL,
                            search_text TEXT,
                            FULLTEXT INDEX ft_search (search_text),
                            FOREIGN KEY (product_id) REFERENCES business_products(id) ON DELETE CASCADE
                        ) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4
                    """)
                    print("  ✓ 搜索辅助表 business_product_search 创建成功")
                    migrated.append("business_product_search")
                else:
                    raise
        else:
            print("  ○ 全文索引已存在，跳过")

        conn.commit()
        print("\n" + "=" * 50)
        print(f"V22.0 迁移完成! 新增: {', '.join(migrated) if migrated else '无'}")
        print("=" * 50)

    except Exception as e:
        conn.rollback()
        print(f"\n✗ 迁移失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def rollback_v22():
    """V22.0 回滚"""
    print("回滚 V22.0 变更...")

    conn = db.get_db()
    cursor = conn.cursor()

    try:
        # 删除物流轨迹表
        cursor.execute("DROP TABLE IF EXISTS business_logistics_traces")
        print("  ✓ business_logistics_traces 已删除")

        # 删除搜索历史表
        cursor.execute("DROP TABLE IF EXISTS business_search_history")
        print("  ✓ business_search_history 已删除")

        # 删除全文索引
        try:
            cursor.execute("DROP INDEX ft_product_search ON business_products")
            print("  ✓ ft_product_search 已删除")
        except:
            pass

        # 删除搜索辅助表
        cursor.execute("DROP TABLE IF EXISTS business_product_search")
        print("  ✓ business_product_search 已删除")

        conn.commit()
        print("回滚完成!")

    except Exception as e:
        conn.rollback()
        print(f"回滚失败: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rollback', action='store_true', help='回滚迁移')
    args = parser.parse_args()

    if args.rollback:
        rollback_v22()
    else:
        migrate_v22()
