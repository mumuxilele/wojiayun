"""
V42.0 数据库迁移脚本
新增表：
  - business_product_specs: 商品规格组（颜色、尺码等分组）
  - business_product_spec_values: 规格值（各分组下的具体选项）
  - business_product_qa: 商品问答主表
  - business_product_qa_replies: 商品问答回复表
  - business_order_append_reviews: 订单追加评价表
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db


def up():
    """执行迁移"""
    print("[V42.0] 开始数据库迁移...")

    # 1. 商品规格组表
    db.execute("""
        CREATE TABLE IF NOT EXISTS business_product_specs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL COMMENT '商品ID',
            spec_name VARCHAR(50) NOT NULL COMMENT '规格组名称，如颜色/尺码/版本',
            sort_order INT DEFAULT 0 COMMENT '排序',
            deleted TINYINT DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME,
            INDEX idx_product_id (product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品规格组表'
    """)
    print("  ✓ business_product_specs 表就绪")

    # 2. 规格值表
    db.execute("""
        CREATE TABLE IF NOT EXISTS business_product_spec_values (
            id INT AUTO_INCREMENT PRIMARY KEY,
            spec_id INT NOT NULL COMMENT '规格组ID',
            spec_value VARCHAR(100) NOT NULL COMMENT '规格值，如红色/XL/128G',
            extra_price DECIMAL(10,2) DEFAULT 0 COMMENT '相对主价格的附加金额',
            sort_order INT DEFAULT 0,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME,
            INDEX idx_spec_id (spec_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品规格值表'
    """)
    print("  ✓ business_product_spec_values 表就绪")

    # 3. 商品问答主表
    db.execute("""
        CREATE TABLE IF NOT EXISTS business_product_qa (
            id INT AUTO_INCREMENT PRIMARY KEY,
            qa_no VARCHAR(32) NOT NULL UNIQUE COMMENT '问答编号',
            product_id INT NOT NULL COMMENT '商品ID',
            product_name VARCHAR(200) COMMENT '商品名称快照',
            user_id INT NOT NULL COMMENT '提问用户ID',
            user_name VARCHAR(100) COMMENT '提问用户昵称',
            question TEXT NOT NULL COMMENT '提问内容',
            status ENUM('pending','answered','closed') DEFAULT 'pending' COMMENT '状态',
            is_top TINYINT DEFAULT 0 COMMENT '是否置顶',
            ec_id INT DEFAULT 1,
            project_id INT DEFAULT 1,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME,
            INDEX idx_product_id (product_id),
            INDEX idx_user_id (user_id),
            INDEX idx_status (status),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品问答表'
    """)
    print("  ✓ business_product_qa 表就绪")

    # 4. 问答回复表
    db.execute("""
        CREATE TABLE IF NOT EXISTS business_product_qa_replies (
            id INT AUTO_INCREMENT PRIMARY KEY,
            qa_id INT NOT NULL COMMENT '问答ID',
            replier_id INT DEFAULT 0 COMMENT '回复人ID',
            replier_name VARCHAR(100) COMMENT '回复人昵称',
            replier_type ENUM('user','staff') DEFAULT 'user' COMMENT '回复人类型',
            content TEXT NOT NULL COMMENT '回复内容',
            is_followup TINYINT DEFAULT 0 COMMENT '是否追问',
            created_at DATETIME,
            INDEX idx_qa_id (qa_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品问答回复表'
    """)
    print("  ✓ business_product_qa_replies 表就绪")

    # 5. 订单追加评价表
    db.execute("""
        CREATE TABLE IF NOT EXISTS business_order_append_reviews (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL COMMENT '订单ID',
            order_no VARCHAR(32) NOT NULL COMMENT '订单编号',
            user_id INT NOT NULL COMMENT '用户ID',
            product_id INT COMMENT '商品ID（可选）',
            rating TINYINT DEFAULT 5 COMMENT '评分1-5',
            content TEXT COMMENT '追加评价内容',
            images JSON COMMENT '评价图片列表',
            status ENUM('pending','approved','rejected') DEFAULT 'approved' COMMENT '审核状态',
            created_at DATETIME,
            INDEX idx_order_id (order_id),
            INDEX idx_user_id (user_id),
            INDEX idx_product_id (product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单追加评价表'
    """)
    print("  ✓ business_order_append_reviews 表就绪")

    # 6. 为 business_products 表添加 qa_count 字段（如不存在）
    try:
        db.execute("""
            ALTER TABLE business_products
            ADD COLUMN IF NOT EXISTS qa_count INT DEFAULT 0 COMMENT '问答数量'
        """)
        print("  ✓ business_products.qa_count 字段就绪")
    except Exception:
        # MySQL不支持 ADD COLUMN IF NOT EXISTS，降级处理
        try:
            db.execute("SELECT qa_count FROM business_products LIMIT 1")
            print("  ✓ business_products.qa_count 字段已存在")
        except Exception:
            db.execute("ALTER TABLE business_products ADD COLUMN qa_count INT DEFAULT 0 COMMENT '问答数量'")
            print("  ✓ business_products.qa_count 字段已添加")

    print("[V42.0] 数据库迁移完成！")
    print("\n新增功能：")
    print("  1. 商品多规格属性体系（颜色/尺码/版本）")
    print("  2. 商品问答系统（Q&A）")
    print("  3. 订单追加评价功能")


def down():
    """回滚迁移（谨慎使用）"""
    print("[V42.0] 回滚数据库迁移...")

    try:
        db.execute("DROP TABLE IF EXISTS business_product_spec_values")
        print("  ✓ business_product_spec_values 已删除")
    except Exception as e:
        print(f"  ✗ 删除 business_product_spec_values 失败: {e}")

    try:
        db.execute("DROP TABLE IF EXISTS business_product_specs")
        print("  ✓ business_product_specs 已删除")
    except Exception as e:
        print(f"  ✗ 删除 business_product_specs 失败: {e}")

    try:
        db.execute("DROP TABLE IF EXISTS business_product_qa_replies")
        print("  ✓ business_product_qa_replies 已删除")
    except Exception as e:
        print(f"  ✗ 删除 business_product_qa_replies 失败: {e}")

    try:
        db.execute("DROP TABLE IF EXISTS business_product_qa")
        print("  ✓ business_product_qa 已删除")
    except Exception as e:
        print(f"  ✗ 删除 business_product_qa 失败: {e}")

    try:
        db.execute("DROP TABLE IF EXISTS business_order_append_reviews")
        print("  ✓ business_order_append_reviews 已删除")
    except Exception as e:
        print(f"  ✗ 删除 business_order_append_reviews 失败: {e}")

    print("[V42.0] 回滚完成！")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'down':
        down()
    else:
        up()
