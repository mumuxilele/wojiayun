#!/usr/bin/env python3
"""
V5.0 数据库迁移脚本
新增表: business_notifications, business_products, business_feedback, business_payments, business_coupon_usage
新增字段: business_members表增加last_login_at, avatar
"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def migrate():
    """执行V5.0数据库迁移"""
    conn = db.get_db()
    try:
        cursor = conn.cursor()

        # ============ 1. 通知表 ============
        logging.info("创建 business_notifications 表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_notifications (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL COMMENT '接收用户ID',
            title VARCHAR(200) NOT NULL COMMENT '通知标题',
            content TEXT COMMENT '通知内容',
            notify_type VARCHAR(32) NOT NULL DEFAULT 'system' COMMENT '通知类型: system/order/application/booking/promotion',
            ref_id VARCHAR(64) COMMENT '关联业务ID',
            ref_type VARCHAR(32) COMMENT '关联业务类型',
            is_read TINYINT(1) DEFAULT 0 COMMENT '是否已读: 0未读 1已读',
            read_at DATETIME COMMENT '阅读时间',
            ec_id VARCHAR(64) COMMENT '企业ID',
            project_id VARCHAR(64) COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_read (user_id, is_read),
            INDEX idx_user_type (user_id, notify_type),
            INDEX idx_created (created_at),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户通知表'
        """)
        logging.info("✓ business_notifications 表创建完成")

        # ============ 2. 商品表 ============
        logging.info("创建 business_products 表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_products (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            shop_id BIGINT COMMENT '所属门店ID',
            product_name VARCHAR(200) NOT NULL COMMENT '商品名称',
            category VARCHAR(64) COMMENT '商品分类',
            price DECIMAL(10,2) DEFAULT 0.00 COMMENT '价格',
            original_price DECIMAL(10,2) COMMENT '原价(用于划线价)',
            description TEXT COMMENT '商品描述',
            images TEXT COMMENT '图片(JSON数组)',
            status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/inactive',
            stock INT DEFAULT -1 COMMENT '库存: -1不限',
            sales_count INT DEFAULT 0 COMMENT '销量',
            sort_order INT DEFAULT 0 COMMENT '排序',
            ec_id VARCHAR(64) COMMENT '企业ID',
            project_id VARCHAR(64) COMMENT '项目ID',
            deleted TINYINT(1) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_shop (shop_id),
            INDEX idx_category (category),
            INDEX idx_status (status),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表'
        """)
        logging.info("✓ business_products 表创建完成")

        # ============ 3. 意见反馈表 ============
        logging.info("创建 business_feedback 表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_feedback (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
            user_name VARCHAR(100) COMMENT '用户名',
            feedback_type VARCHAR(32) NOT NULL DEFAULT 'suggestion' COMMENT '类型: suggestion/bug/complaint/praise',
            title VARCHAR(200) NOT NULL COMMENT '标题',
            content TEXT NOT NULL COMMENT '内容',
            contact VARCHAR(200) COMMENT '联系方式',
            images TEXT COMMENT '图片(JSON数组)',
            status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/processing/replied/closed',
            reply TEXT COMMENT '回复内容',
            replied_by VARCHAR(100) COMMENT '回复人',
            replied_at DATETIME COMMENT '回复时间',
            ec_id VARCHAR(64) COMMENT '企业ID',
            project_id VARCHAR(64) COMMENT '项目ID',
            deleted TINYINT(1) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_status (status),
            INDEX idx_type (feedback_type),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='意见反馈表'
        """)
        logging.info("✓ business_feedback 表创建完成")

        # ============ 4. 公告表(确保存在) ============
        logging.info("创建 business_notices 表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_notices (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL COMMENT '标题',
            content TEXT COMMENT '内容',
            notice_type VARCHAR(32) DEFAULT 'general' COMMENT '类型: general/urgent/activity',
            importance INT DEFAULT 0 COMMENT '重要程度: 0普通 1重要 2紧急',
            status VARCHAR(20) DEFAULT 'draft' COMMENT '状态: draft/published/archived',
            end_date DATE COMMENT '结束日期',
            ec_id VARCHAR(64) COMMENT '企业ID',
            project_id VARCHAR(64) COMMENT '项目ID',
            deleted TINYINT(1) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_status (status),
            INDEX idx_type (notice_type),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='公告表'
        """)
        logging.info("✓ business_notices 表创建完成")

        # ============ 5. 会员表新增字段 ============
        logging.info("检查并新增 business_members 字段...")
        try:
            cursor.execute("ALTER TABLE business_members ADD COLUMN last_login_at DATETIME COMMENT '最后登录时间'")
            logging.info("✓ business_members 新增 last_login_at 字段")
        except Exception as e:
            if "Duplicate column" in str(e):
                logging.info("  字段已存在，跳过")
            else:
                logging.warning(f"  新增字段失败: {e}")

        try:
            cursor.execute("ALTER TABLE business_members ADD COLUMN avatar VARCHAR(500) COMMENT '头像URL'")
            logging.info("✓ business_members 新增 avatar 字段")
        except Exception as e:
            if "Duplicate column" in str(e):
                logging.info("  字段已存在，跳过")
            else:
                logging.warning(f"  新增字段失败: {e}")

        # ============ 6. 支付单表 ============
        logging.info("创建 business_payments 表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_payments (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            pay_no VARCHAR(64) NOT NULL UNIQUE COMMENT '支付单号',
            order_type VARCHAR(32) NOT NULL COMMENT '订单类型: booking/order',
            order_id BIGINT NOT NULL COMMENT '业务订单ID',
            amount DECIMAL(10,2) NOT NULL COMMENT '支付金额',
            user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
            user_name VARCHAR(100) COMMENT '用户名',
            channel VARCHAR(32) DEFAULT 'mock' COMMENT '支付渠道: mock/wechat/alipay',
            status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/paid/failed/refunding/refunded',
            paid_at DATETIME COMMENT '支付时间',
            refund_reason TEXT COMMENT '退款原因',
            refunded_at DATETIME COMMENT '退款时间',
            ec_id VARCHAR(64) COMMENT '企业ID',
            project_id VARCHAR(64) COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_pay_no (pay_no),
            INDEX idx_order (order_type, order_id),
            INDEX idx_user (user_id),
            INDEX idx_status (status),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付单表'
        """)
        logging.info("✓ business_payments 表创建完成")

        # ============ 7. 优惠券使用记录表 ============
        logging.info("创建 business_coupon_usage 表...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_coupon_usage (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            coupon_id BIGINT NOT NULL COMMENT '优惠券模板ID',
            user_coupon_id BIGINT NOT NULL COMMENT '用户优惠券ID',
            user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
            order_id VARCHAR(64) COMMENT '关联订单ID',
            discount_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT '优惠金额',
            ec_id VARCHAR(64) COMMENT '企业ID',
            project_id VARCHAR(64) COMMENT '项目ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_coupon (coupon_id),
            INDEX idx_order (order_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券使用记录表'
        """)
        logging.info("✓ business_coupon_usage 表创建完成")

        # ============ 7. 新增索引优化 ============
        logging.info("新增性能索引...")
        indexes = [
            "ALTER TABLE business_applications ADD INDEX idx_user_status (user_id, status, deleted)",
            "ALTER TABLE business_orders ADD INDEX idx_user_status (user_id, order_status, deleted)",
            "ALTER TABLE business_venue_bookings ADD INDEX idx_user_date (user_id, book_date)",
            "ALTER TABLE business_points_log ADD INDEX idx_user_type (user_id, log_type)",
        ]
        for idx_sql in indexes:
            try:
                cursor.execute(idx_sql)
                logging.info(f"  ✓ 索引创建成功")
            except Exception as e:
                if "Duplicate key" in str(e):
                    logging.info(f"  索引已存在，跳过")
                else:
                    logging.warning(f"  索引创建失败: {e}")

        conn.commit()
        logging.info("=" * 50)
        logging.info("V5.0 数据库迁移全部完成!")
        logging.info("=" * 50)

    except Exception as e:
        conn.rollback()
        logging.error(f"迁移失败: {e}")
        raise
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

if __name__ == '__main__':
    migrate()
