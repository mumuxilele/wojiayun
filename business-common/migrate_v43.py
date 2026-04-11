"""
V43.0 数据库迁移脚本

新增表：
- business_order_tracking: 订单追踪表
- business_fulfillment_logs: 履约事件日志表
- business_aftersales: 售后申请表
- business_aftersales_items: 售后商品明细表
- business_aftersales_logs: 售后进度日志表
- business_seckill_activities: 秒杀活动表
- business_seckill_reminders: 秒杀提醒订阅表
- business_seckill_queue: 秒杀排队表

优化：
- business_orders: 增加履约相关字段
- business_reviews: 增加追评、图片等字段
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def migrate():
    """执行V43.0迁移"""
    logger.info("开始 V43.0 数据库迁移...")
    
    try:
        # 1. 订单追踪表
        _create_order_tracking_table()
        
        # 2. 履约事件日志表
        _create_fulfillment_logs_table()
        
        # 3. 售后申请表
        _create_aftersales_tables()
        
        # 4. 秒杀增强表
        _create_seckill_tables()
        
        # 5. 评价表增强
        _enhance_reviews_table()
        
        # 6. 订单表增强
        _enhance_orders_table()
        
        logger.info("V43.0 数据库迁移完成!")
        return True
        
    except Exception as e:
        logger.error(f"V43.0 迁移失败: {e}")
        return False


def _create_order_tracking_table():
    """创建订单追踪表"""
    logger.info("创建订单追踪表...")
    
    # 检查表是否存在
    result = db.get_one("SHOW TABLES LIKE 'business_order_tracking'")
    if result:
        logger.info("  订单追踪表已存在，跳过")
        return
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS business_order_tracking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL COMMENT '订单ID',
            order_no VARCHAR(50) NOT NULL COMMENT '订单编号',
            tracking_no VARCHAR(50) COMMENT '物流单号',
            carrier_code VARCHAR(20) COMMENT '快递公司代码',
            carrier_name VARCHAR(50) COMMENT '快递公司名称',
            current_status VARCHAR(20) DEFAULT 'pending' COMMENT '当前状态',
            tracking_nodes TEXT COMMENT '物流节点JSON',
            estimated_delivery DATE COMMENT '预计送达日期',
            shipped_at DATETIME COMMENT '发货时间',
            delivered_at DATETIME COMMENT '送达时间',
            signed_at DATETIME COMMENT '签收时间',
            confirmed_at DATETIME COMMENT '确认收货时间',
            exception_type VARCHAR(20) COMMENT '异常类型',
            exception_desc VARCHAR(200) COMMENT '异常描述',
            last_check_at DATETIME COMMENT '最后查询时间',
            check_count INT DEFAULT 0 COMMENT '查询次数',
            auto_confirm_scheduled_at DATETIME COMMENT '自动确认时间',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_order (order_id),
            INDEX idx_tracking_no (tracking_no),
            INDEX idx_status (current_status),
            INDEX idx_exception (exception_type),
            INDEX idx_auto_confirm (auto_confirm_scheduled_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单追踪表';
    """)
    logger.info("  订单追踪表创建成功")


def _create_fulfillment_logs_table():
    """创建履约事件日志表"""
    logger.info("创建履约事件日志表...")
    
    result = db.get_one("SHOW TABLES LIKE 'business_fulfillment_logs'")
    if result:
        logger.info("  履约事件日志表已存在，跳过")
        return
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS business_fulfillment_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL COMMENT '订单ID',
            event_type VARCHAR(30) NOT NULL COMMENT '事件类型',
            event_data TEXT COMMENT '事件数据JSON',
            operator_type VARCHAR(20) COMMENT '操作者类型:user/system',
            operator_id INT COMMENT '操作者ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_order (order_id),
            INDEX idx_event (event_type),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='履约事件日志表';
    """)
    logger.info("  履约事件日志表创建成功")


def _create_aftersales_tables():
    """创建售后相关表"""
    logger.info("创建售后相关表...")
    
    # 售后申请表
    result = db.get_one("SHOW TABLES LIKE 'business_aftersales'")
    if not result:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_aftersales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                aftersales_no VARCHAR(50) NOT NULL COMMENT '售后单号',
                order_id INT NOT NULL COMMENT '订单ID',
                order_no VARCHAR(50) NOT NULL COMMENT '订单编号',
                user_id INT NOT NULL COMMENT '用户ID',
                type VARCHAR(20) NOT NULL COMMENT '类型:refund/return_refund/exchange/repair',
                status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
                reason_code VARCHAR(30) COMMENT '原因代码',
                reason_desc VARCHAR(200) COMMENT '原因描述',
                refund_amount DECIMAL(10,2) COMMENT '退款金额',
                apply_images TEXT COMMENT '申请图片JSON',
                apply_desc VARCHAR(500) COMMENT '申请说明',
                tracking_no VARCHAR(50) COMMENT '退货运单号',
                carrier_name VARCHAR(50) COMMENT '退货快递公司',
                return_address TEXT COMMENT '退货地址',
                handler_id INT COMMENT '处理人ID',
                handler_name VARCHAR(50) COMMENT '处理人姓名',
                handle_remark VARCHAR(500) COMMENT '处理备注',
                handle_time DATETIME COMMENT '处理时间',
                completed_time DATETIME COMMENT '完成时间',
                close_time DATETIME COMMENT '关闭时间',
                auto_close_at DATETIME COMMENT '自动关闭时间',
                ec_id INT COMMENT '企业ID',
                project_id INT COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_aftersales_no (aftersales_no),
                INDEX idx_order (order_id),
                INDEX idx_user (user_id),
                INDEX idx_status (status),
                INDEX idx_type (type),
                INDEX idx_auto_close (auto_close_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='售后申请表';
        """)
        logger.info("  售后申请表创建成功")
    
    # 售后商品明细表
    result = db.get_one("SHOW TABLES LIKE 'business_aftersales_items'")
    if not result:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_aftersales_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                aftersales_id INT NOT NULL COMMENT '售后单ID',
                order_item_id INT COMMENT '订单明细ID',
                product_id INT NOT NULL COMMENT '商品ID',
                product_name VARCHAR(200) COMMENT '商品名称',
                sku_id INT COMMENT 'SKU ID',
                sku_name VARCHAR(200) COMMENT 'SKU名称',
                quantity INT NOT NULL COMMENT '数量',
                price DECIMAL(10,2) COMMENT '单价',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_aftersales (aftersales_id),
                INDEX idx_product (product_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='售后商品明细表';
        """)
        logger.info("  售后商品明细表创建成功")
    
    # 售后进度日志表
    result = db.get_one("SHOW TABLES LIKE 'business_aftersales_logs'")
    if not result:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_aftersales_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                aftersales_id INT NOT NULL COMMENT '售后单ID',
                from_status VARCHAR(20) COMMENT '原状态',
                to_status VARCHAR(20) NOT NULL COMMENT '新状态',
                operator_type VARCHAR(20) COMMENT '操作者类型:user/staff/system',
                operator_id INT COMMENT '操作者ID',
                operator_name VARCHAR(50) COMMENT '操作者姓名',
                remark VARCHAR(500) COMMENT '备注',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_aftersales (aftersales_id),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='售后进度日志表';
        """)
        logger.info("  售后进度日志表创建成功")


def _create_seckill_tables():
    """创建秒杀增强表"""
    logger.info("创建秒杀增强表...")
    
    # 秒杀活动表
    result = db.get_one("SHOW TABLES LIKE 'business_seckill_activities'")
    if not result:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_seckill_activities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                activity_name VARCHAR(100) NOT NULL COMMENT '活动名称',
                product_id INT NOT NULL COMMENT '商品ID',
                seckill_price DECIMAL(10,2) NOT NULL COMMENT '秒杀价',
                original_stock INT NOT NULL COMMENT '原始库存',
                remaining_stock INT NOT NULL COMMENT '剩余库存',
                per_limit INT DEFAULT 1 COMMENT '每人限购',
                start_time DATETIME NOT NULL COMMENT '开始时间',
                end_time DATETIME NOT NULL COMMENT '结束时间',
                status VARCHAR(20) DEFAULT 'preview' COMMENT '状态:preview/ongoing/ended/soldout',
                warmup_time DATETIME COMMENT '预热时间',
                priority INT DEFAULT 100 COMMENT '优先级',
                ec_id INT COMMENT '企业ID',
                project_id INT COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_product (product_id),
                INDEX idx_time (start_time, end_time),
                INDEX idx_status (status),
                INDEX idx_ec_project (ec_id, project_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='秒杀活动表';
        """)
        logger.info("  秒杀活动表创建成功")
    
    # 秒杀提醒订阅表
    result = db.get_one("SHOW TABLES LIKE 'business_seckill_reminders'")
    if not result:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_seckill_reminders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                activity_id INT NOT NULL COMMENT '活动ID',
                user_id INT NOT NULL COMMENT '用户ID',
                remind_type VARCHAR(20) DEFAULT 'sms' COMMENT '提醒类型:sms/push/wechat',
                remind_at DATETIME COMMENT '提醒时间',
                reminded TINYINT DEFAULT 0 COMMENT '是否已提醒',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_user_activity (user_id, activity_id),
                INDEX idx_activity (activity_id),
                INDEX idx_remind (reminded, remind_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='秒杀提醒订阅表';
        """)
        logger.info("  秒杀提醒订阅表创建成功")


def _enhance_reviews_table():
    """增强评价表"""
    logger.info("增强评价表...")
    
    # 检查字段是否存在
    columns = db.get_all("SHOW COLUMNS FROM business_reviews")
    column_names = [c['Field'] for c in columns] if columns else []
    
    # 添加追评相关字段
    if 'is_append' not in column_names:
        db.execute("ALTER TABLE business_reviews ADD COLUMN is_append TINYINT DEFAULT 0 COMMENT '是否追评'")
        logger.info("  添加 is_append 字段")
    
    if 'parent_id' not in column_names:
        db.execute("ALTER TABLE business_reviews ADD COLUMN parent_id INT DEFAULT NULL COMMENT '父评价ID'")
        db.execute("ALTER TABLE business_reviews ADD INDEX idx_parent (parent_id)")
        logger.info("  添加 parent_id 字段")
    
    if 'images' not in column_names:
        db.execute("ALTER TABLE business_reviews ADD COLUMN images TEXT COMMENT '评价图片JSON'")
        logger.info("  添加 images 字段")
    
    if 'tags' not in column_names:
        db.execute("ALTER TABLE business_reviews ADD COLUMN tags VARCHAR(200) COMMENT '评价标签'")
        logger.info("  添加 tags 字段")
    
    if 'helpful_count' not in column_names:
        db.execute("ALTER TABLE business_reviews ADD COLUMN helpful_count INT DEFAULT 0 COMMENT '有用数'")
        logger.info("  添加 helpful_count 字段")


def _enhance_orders_table():
    """增强订单表"""
    logger.info("增强订单表...")
    
    columns = db.get_all("SHOW COLUMNS FROM business_orders")
    column_names = [c['Field'] for c in columns] if columns else []
    
    # 添加履约相关字段
    if 'tracking_no' not in column_names:
        db.execute("ALTER TABLE business_orders ADD COLUMN tracking_no VARCHAR(50) COMMENT '物流单号'")
        logger.info("  添加 tracking_no 字段")
    
    if 'carrier_name' not in column_names:
        db.execute("ALTER TABLE business_orders ADD COLUMN carrier_name VARCHAR(50) COMMENT '快递公司'")
        logger.info("  添加 carrier_name 字段")
    
    if 'shipped_at' not in column_names:
        db.execute("ALTER TABLE business_orders ADD COLUMN shipped_at DATETIME COMMENT '发货时间'")
        logger.info("  添加 shipped_at 字段")
    
    if 'auto_confirm_at' not in column_names:
        db.execute("ALTER TABLE business_orders ADD COLUMN auto_confirm_at DATETIME COMMENT '自动确认时间'")
        logger.info("  添加 auto_confirm_at 字段")


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
