"""
V32.0 数据库迁移脚本

迁移内容:
1. 库存预警表 business_inventory_alerts
2. 商品库存阈值字段 stock_threshold
3. 订单明细表增强
4. FAQ表 business_faqs

运行方式:
    python business-common/migrate_v32.py
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def run_migration():
    """执行V32.0迁移"""

    logger.info("=" * 50)
    logger.info("开始 V32.0 数据库迁移")
    logger.info("=" * 50)

    # 检查是否已执行过迁移
    check_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'business_inventory_alerts'
    """
    result = db.get_one(check_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("business_inventory_alerts 表已存在，跳过创建")
    else:
        logger.info("创建 business_inventory_alerts 表...")

        create_inventory_alerts_sql = """
        CREATE TABLE IF NOT EXISTS business_inventory_alerts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL COMMENT '商品ID',
            alert_type VARCHAR(32) NOT NULL COMMENT '预警类型: low_stock/critical/out_of_stock',
            stock_before INT NOT NULL DEFAULT 0 COMMENT '预警前库存',
            stock_after INT NOT NULL DEFAULT 0 COMMENT '预警后库存',
            ec_id INT NOT NULL COMMENT '企业ID',
            project_id INT DEFAULT NULL COMMENT '项目ID',
            is_handled TINYINT(1) DEFAULT 0 COMMENT '是否已处理',
            handled_by INT DEFAULT NULL COMMENT '处理人ID',
            handled_at DATETIME DEFAULT NULL COMMENT '处理时间',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            INDEX idx_ec_project (ec_id, project_id),
            INDEX idx_product (product_id),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存预警记录表';
        """
        db.execute(create_inventory_alerts_sql)
        logger.info("✓ business_inventory_alerts 表创建完成")

    # 添加商品库存阈值字段
    logger.info("检查 stock_threshold 字段...")
    check_field_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.columns
        WHERE table_schema = DATABASE()
        AND table_name = 'business_products'
        AND column_name = 'stock_threshold'
    """
    result = db.get_one(check_field_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("stock_threshold 字段已存在，跳过")
    else:
        alter_sql = """
        ALTER TABLE business_products
        ADD COLUMN stock_threshold INT DEFAULT 10 COMMENT '库存预警阈值'
        AFTER stock;
        """
        db.execute(alter_sql)
        logger.info("✓ stock_threshold 字段添加完成")

    # 创建FAQ表
    logger.info("检查 business_faqs 表...")
    check_faqs_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'business_faqs'
    """
    result = db.get_one(check_faqs_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("business_faqs 表已存在，跳过创建")
    else:
        logger.info("创建 business_faqs 表...")

        create_faqs_sql = """
        CREATE TABLE IF NOT EXISTS business_faqs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            category VARCHAR(64) NOT NULL COMMENT '分类: order/payment/delivery/member/other',
            question VARCHAR(255) NOT NULL COMMENT '问题',
            answer TEXT NOT NULL COMMENT '回答',
            keywords VARCHAR(255) DEFAULT '' COMMENT '关键词(逗号分隔)',
            sort_order INT DEFAULT 0 COMMENT '排序',
            view_count INT DEFAULT 0 COMMENT '浏览次数',
            is_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
            ec_id INT NOT NULL COMMENT '企业ID',
            project_id INT DEFAULT NULL COMMENT '项目ID',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_category (category),
            INDEX idx_ec (ec_id),
            INDEX idx_keywords (keywords(255))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='常见问题表';
        """
        db.execute(create_faqs_sql)
        logger.info("✓ business_faqs 表创建完成")

        # 插入默认FAQ数据
        logger.info("插入默认FAQ数据...")
        insert_faqs_sql = """
        INSERT INTO business_faqs (category, question, answer, keywords, sort_order, ec_id) VALUES
        ('order', '如何查看我的订单？', '登录后点击"我的-订单"即可查看所有订单，包括待支付、待发货、待收货、已完成等状态的订单。', '订单,查询,查看', 1, 1),
        ('order', '订单取消后如何退款？', '订单取消后，支付金额将自动退回您的支付账户，退款会在1-7个工作日内到账。', '退款,取消,订单', 2, 1),
        ('payment', '支持哪些支付方式？', '我们支持微信支付、支付宝支付以及会员余额支付。', '支付,微信,支付宝', 1, 1),
        ('payment', '支付失败怎么办？', '支付失败可能是网络原因或余额不足，请检查后重新支付。如有问题可联系客服。', '支付,失败,问题', 2, 1),
        ('delivery', '多久能收到货？', '同城配送通常1-2小时送达，跨城配送1-3天，具体以商家承诺和物流信息为准。', '物流,快递,送达', 1, 1),
        ('delivery', '如何查看物流信息？', '在"我的订单-待收货"中点击"查看物流"即可实时跟踪包裹状态。', '物流,追踪,快递', 2, 1),
        ('member', '如何获得积分？', '积分可通过购物消费、签到打卡、参与活动等方式获得。消费1元=1积分，签到5积分/天。', '积分,获得,怎么', 1, 1),
        ('member', '积分有什么用途？', '积分可在积分商城兑换商品，或在结算时抵扣现金（100积分=1元）。', '积分,用途,兑换', 2, 1),
        ('member', '会员等级如何升级？', '会员等级根据成长值自动提升，成长值通过消费、评价、签到等方式获得，达到对应阈值自动升级。', '等级,升级,成长', 3, 1),
        ('other', '如何联系客服？', '您可以通过在线客服、电话热线或在"意见反馈"中提交问题，我们会尽快为您解答。', '客服,联系,帮助', 1, 1);
        """
        try:
            db.execute(insert_faqs_sql)
            logger.info("✓ 默认FAQ数据插入完成")
        except Exception as e:
            logger.warning(f"FAQ数据插入失败(可能已存在): {e}")

    # 创建订单状态日志表(如果不存在)
    logger.info("检查 business_order_status_logs 表...")
    check_logs_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'business_order_status_logs'
    """
    result = db.get_one(check_logs_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("business_order_status_logs 表已存在，跳过创建")
    else:
        logger.info("创建 business_order_status_logs 表...")

        create_logs_sql = """
        CREATE TABLE IF NOT EXISTS business_order_status_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL COMMENT '订单ID',
            old_status VARCHAR(32) DEFAULT NULL COMMENT '原状态',
            new_status VARCHAR(32) NOT NULL COMMENT '新状态',
            operator_id INT DEFAULT NULL COMMENT '操作人ID',
            remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_order (order_id),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单状态变更日志表';
        """
        db.execute(create_logs_sql)
        logger.info("✓ business_order_status_logs 表创建完成")

    # 创建浏览历史表(如果不存在)
    logger.info("检查 business_view_history 表...")
    check_history_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'business_view_history'
    """
    result = db.get_one(check_history_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("business_view_history 表已存在，跳过创建")
    else:
        logger.info("创建 business_view_history 表...")

        create_history_sql = """
        CREATE TABLE IF NOT EXISTS business_view_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL COMMENT '用户ID',
            product_id INT NOT NULL COMMENT '商品ID',
            ec_id INT NOT NULL COMMENT '企业ID',
            project_id INT DEFAULT NULL COMMENT '项目ID',
            viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '浏览时间',
            INDEX idx_user (user_id),
            INDEX idx_product (product_id),
            INDEX idx_user_viewed (user_id, viewed_at),
            UNIQUE KEY uk_user_product (user_id, product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品浏览历史表';
        """
        db.execute(create_history_sql)
        logger.info("✓ business_view_history 表创建完成")

    logger.info("=" * 50)
    logger.info("V32.0 数据库迁移完成!")
    logger.info("=" * 50)

    return True


if __name__ == '__main__':
    try:
        run_migration()
        print("\n迁移成功完成！")
    except Exception as e:
        print(f"\n迁移失败: {e}")
        sys.exit(1)
