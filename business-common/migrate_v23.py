"""
V23.0 数据库迁移脚本
新增表:
  - business_points_goods: 积分商品表
  - business_points_exchanges: 积分兑换记录表
修改表:
  - business_reviews: 新增 moderation_status, moderation_result 字段
  - business_reviews: 新增 append_moderation_status, append_moderation_result 字段
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

ROLLBACK = '--rollback' in sys.argv


def migrate():
    """执行迁移"""
    if ROLLBACK:
        print("=== V23.0 回滚迁移 ===")
        _rollback()
        return

    print("=== V23.0 正向迁移 ===")
    conn = db.get_db()
    try:
        cursor = conn.cursor()

        # 1. 积分商品表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_points_goods (
            id INT AUTO_INCREMENT PRIMARY KEY,
            goods_name VARCHAR(100) NOT NULL COMMENT '商品名称',
            goods_image VARCHAR(500) COMMENT '商品图片',
            category VARCHAR(50) DEFAULT '' COMMENT '分类',
            points_price INT NOT NULL DEFAULT 0 COMMENT '积分价格',
            original_price DECIMAL(10,2) DEFAULT 0.00 COMMENT '原价(展示用)',
            stock INT DEFAULT 0 COMMENT '当前库存',
            total_stock INT DEFAULT 0 COMMENT '总库存',
            sold_count INT DEFAULT 0 COMMENT '已兑换数',
            description TEXT COMMENT '商品描述',
            per_limit INT DEFAULT 0 COMMENT '每人限兑(0=不限)',
            status VARCHAR(20) DEFAULT 'active' COMMENT 'active/off_shelf',
            sort_order INT DEFAULT 0 COMMENT '排序',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            created_by VARCHAR(50) COMMENT '创建人',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted TINYINT DEFAULT 0,
            INDEX idx_status (status),
            INDEX idx_ec_project (ec_id, project_id),
            INDEX idx_category (category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='积分商品表'
        """)
        print("  [OK] business_points_goods 表已创建/已存在")

        # 2. 积分兑换记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_points_exchanges (
            id INT AUTO_INCREMENT PRIMARY KEY,
            exchange_no VARCHAR(30) NOT NULL UNIQUE COMMENT '兑换单号',
            user_id INT NOT NULL COMMENT '用户ID',
            user_name VARCHAR(50) COMMENT '用户名',
            goods_id INT NOT NULL COMMENT '商品ID',
            goods_name VARCHAR(100) COMMENT '商品名称',
            goods_image VARCHAR(500) COMMENT '商品图片',
            points_price INT DEFAULT 0 COMMENT '单价积分',
            quantity INT DEFAULT 1 COMMENT '数量',
            total_points INT DEFAULT 0 COMMENT '总积分',
            address_snapshot VARCHAR(500) COMMENT '收货地址快照',
            phone VARCHAR(20) COMMENT '联系电话',
            tracking_no VARCHAR(50) COMMENT '物流单号',
            logistics_company VARCHAR(50) COMMENT '物流公司',
            status VARCHAR(20) DEFAULT 'paid' COMMENT 'paid/shipped/completed/cancelled',
            shipped_by VARCHAR(50) COMMENT '发货人',
            shipped_at DATETIME COMMENT '发货时间',
            completed_at DATETIME COMMENT '完成时间',
            ec_id INT COMMENT '企业ID',
            project_id INT COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted TINYINT DEFAULT 0,
            INDEX idx_user_id (user_id),
            INDEX idx_exchange_no (exchange_no),
            INDEX idx_status (status),
            INDEX idx_goods_id (goods_id),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='积分兑换记录表'
        """)
        print("  [OK] business_points_exchanges 表已创建/已存在")

        # 3. 评价表新增审核字段
        _add_column_if_missing(cursor, 'business_reviews', 'moderation_status',
                               "VARCHAR(20) DEFAULT NULL COMMENT '审核状态: approved/pending_review/rejected'")
        print("  [OK] business_reviews.moderation_status 已添加/已存在")

        _add_column_if_missing(cursor, 'business_reviews', 'moderation_result',
                               "TEXT COMMENT '审核结果JSON'")
        print("  [OK] business_reviews.moderation_result 已添加/已存在")

        _add_column_if_missing(cursor, 'business_reviews', 'moderated_at',
                               "DATETIME COMMENT '审核时间'")
        print("  [OK] business_reviews.moderated_at 已添加/已存在")

        # 4. 追评审核字段
        _add_column_if_missing(cursor, 'business_reviews', 'append_moderation_status',
                               "VARCHAR(20) DEFAULT NULL COMMENT '追评审核状态'")
        print("  [OK] business_reviews.append_moderation_status 已添加/已存在")

        _add_column_if_missing(cursor, 'business_reviews', 'append_moderation_result',
                               "TEXT COMMENT '追评审核结果JSON'")
        print("  [OK] business_reviews.append_moderation_result 已添加/已存在")

        conn.commit()
        print("\n=== V23.0 迁移完成 ===\n")

    except Exception as e:
        conn.rollback()
        print(f"\n=== V23.0 迁移失败: {e} ===\n")
        raise
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


def _add_column_if_missing(cursor, table, column, column_def):
    """安全添加列（如果不存在）"""
    cursor.execute(f"""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s
    """, [table, column])
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")


def _rollback():
    """回滚迁移"""
    conn = db.get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS business_points_exchanges")
        print("  [OK] business_points_exchanges 已删除")
        cursor.execute("DROP TABLE IF EXISTS business_points_goods")
        print("  [OK] business_points_goods 已删除")
        conn.commit()
        print("\n=== V23.0 回滚完成 ===\n")
    except Exception as e:
        conn.rollback()
        print(f"\n=== V23.0 回滚失败: {e} ===\n")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    migrate()
