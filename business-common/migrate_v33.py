"""
V33.0 数据库迁移脚本

迁移内容:
1. 发票抬头表 business_invoice_titles
2. 发票申请表 business_invoices
3. 任务队列表 business_tasks
4. 备份记录表 business_backups

运行方式:
    python business-common/migrate_v33.py
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def run_migration():
    """执行V33.0迁移"""

    logger.info("=" * 50)
    logger.info("开始 V33.0 数据库迁移")
    logger.info("=" * 50)

    # 1. 创建发票抬头表
    logger.info("创建 business_invoice_titles 表...")
    check_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'business_invoice_titles'
    """
    result = db.get_one(check_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("business_invoice_titles 表已存在，跳过创建")
    else:
        create_sql = """
        CREATE TABLE IF NOT EXISTS business_invoice_titles (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
            title_type ENUM('personal', 'enterprise') DEFAULT 'personal' COMMENT '抬头类型',
            title_name VARCHAR(200) NOT NULL COMMENT '发票抬头名称',
            tax_no VARCHAR(50) COMMENT '税号',
            bank_name VARCHAR(100) COMMENT '开户银行',
            bank_account VARCHAR(50) COMMENT '银行账号',
            address VARCHAR(200) COMMENT '注册地址',
            phone VARCHAR(20) COMMENT '联系电话',
            is_default TINYINT(1) DEFAULT 0 COMMENT '是否默认',
            ec_id INT DEFAULT NULL,
            project_id INT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted TINYINT(1) DEFAULT 0,
            INDEX idx_user (user_id),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发票抬头表';
        """
        db.execute(create_sql)
        logger.info("✓ business_invoice_titles 表创建完成")

    # 2. 创建发票申请表
    logger.info("创建 business_invoices 表...")
    check_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'business_invoices'
    """
    result = db.get_one(check_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("business_invoices 表已存在，跳过创建")
    else:
        create_sql = """
        CREATE TABLE IF NOT EXISTS business_invoices (
            id INT PRIMARY KEY AUTO_INCREMENT,
            invoice_no VARCHAR(64) UNIQUE COMMENT '发票号',
            order_id INT NOT NULL COMMENT '订单ID',
            order_no VARCHAR(64) NOT NULL COMMENT '订单编号',
            user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
            title_id INT NOT NULL COMMENT '抬头ID',
            title_type VARCHAR(20) NOT NULL COMMENT '抬头类型',
            title_name VARCHAR(200) NOT NULL COMMENT '发票抬头',
            tax_no VARCHAR(50) COMMENT '税号',
            invoice_type ENUM('electronic', 'paper') DEFAULT 'electronic' COMMENT '发票类型',
            invoice_status ENUM('pending', 'approved', 'issued', 'rejected', 'cancelled') DEFAULT 'pending' COMMENT '状态',
            amount DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '开票金额',
            tax_amount DECIMAL(10,2) DEFAULT 0 COMMENT '税额',
            tax_rate DECIMAL(5,4) DEFAULT 0.0600 COMMENT '税率',
            content VARCHAR(100) DEFAULT '商品明细' COMMENT '发票内容',
            remark VARCHAR(500) COMMENT '备注',
            issued_at DATETIME COMMENT '开具时间',
            issued_by VARCHAR(64) COMMENT '开具人',
            pdf_url VARCHAR(500) COMMENT '电子发票PDF地址',
            ec_id INT DEFAULT NULL,
            project_id INT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted TINYINT(1) DEFAULT 0,
            INDEX idx_order (order_id),
            INDEX idx_user (user_id),
            INDEX idx_status (invoice_status),
            INDEX idx_ec_project (ec_id, project_id),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发票申请表';
        """
        db.execute(create_sql)
        logger.info("✓ business_invoices 表创建完成")

    # 3. 创建任务队列表
    logger.info("创建 business_tasks 表...")
    check_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'business_tasks'
    """
    result = db.get_one(check_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("business_tasks 表已存在，跳过创建")
    else:
        create_sql = """
        CREATE TABLE IF NOT EXISTS business_tasks (
            id INT PRIMARY KEY AUTO_INCREMENT,
            task_id VARCHAR(64) UNIQUE NOT NULL COMMENT '任务ID',
            task_type VARCHAR(50) NOT NULL COMMENT '任务类型',
            task_data TEXT COMMENT '任务数据JSON',
            priority INT DEFAULT 5 COMMENT '优先级 1-20',
            status ENUM('pending', 'running', 'completed', 'failed', 'cancelled', 'retrying', 'scheduled') DEFAULT 'pending' COMMENT '状态',
            scheduled_at DATETIME COMMENT '定时执行时间',
            started_at DATETIME COMMENT '开始执行时间',
            completed_at DATETIME COMMENT '完成时间',
            duration DECIMAL(10,2) DEFAULT 0 COMMENT '执行时长(秒)',
            worker_id VARCHAR(64) COMMENT '执行工作进程ID',
            callback_url VARCHAR(500) COMMENT '回调URL',
            max_retries INT DEFAULT 3 COMMENT '最大重试次数',
            retry_count INT DEFAULT 0 COMMENT '已重试次数',
            error_message TEXT COMMENT '错误信息',
            result TEXT COMMENT '执行结果JSON',
            ec_id INT DEFAULT NULL,
            project_id INT DEFAULT NULL,
            created_by VARCHAR(64) COMMENT '创建人',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted TINYINT(1) DEFAULT 0,
            INDEX idx_task_id (task_id),
            INDEX idx_task_type (task_type),
            INDEX idx_status (status),
            INDEX idx_scheduled (scheduled_at),
            INDEX idx_worker (worker_id),
            INDEX idx_priority (priority),
            INDEX idx_ec_project (ec_id, project_id),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='异步任务队列表';
        """
        db.execute(create_sql)
        logger.info("✓ business_tasks 表创建完成")

    # 4. 创建备份记录表
    logger.info("创建 business_backups 表...")
    check_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'business_backups'
    """
    result = db.get_one(check_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("business_backups 表已存在，跳过创建")
    else:
        create_sql = """
        CREATE TABLE IF NOT EXISTS business_backups (
            id INT PRIMARY KEY AUTO_INCREMENT,
            backup_id VARCHAR(64) UNIQUE NOT NULL COMMENT '备份ID',
            backup_type ENUM('full', 'incremental') NOT NULL COMMENT '备份类型',
            status ENUM('pending', 'running', 'completed', 'failed', 'cancelled') DEFAULT 'pending' COMMENT '状态',
            backup_path VARCHAR(500) COMMENT '备份文件路径',
            file_size BIGINT DEFAULT 0 COMMENT '文件大小(字节)',
            checksum VARCHAR(64) COMMENT '文件校验和',
            details TEXT COMMENT '详细信息',
            started_at DATETIME COMMENT '开始时间',
            completed_at DATETIME COMMENT '完成时间',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            deleted TINYINT(1) DEFAULT 0,
            INDEX idx_backup_id (backup_id),
            INDEX idx_backup_type (backup_type),
            INDEX idx_status (status),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='备份记录表';
        """
        db.execute(create_sql)
        logger.info("✓ business_backups 表创建完成")

    # 5. 添加订单发票状态字段
    logger.info("检查 business_orders 表的 invoice_status 字段...")
    check_field_sql = """
        SELECT COUNT(*) as cnt FROM information_schema.columns
        WHERE table_schema = DATABASE()
        AND table_name = 'business_orders'
        AND column_name = 'invoice_status'
    """
    result = db.get_one(check_field_sql)
    if result and result.get('cnt', 0) > 0:
        logger.info("invoice_status 字段已存在，跳过添加")
    else:
        alter_sql = """
        ALTER TABLE business_orders
        ADD COLUMN invoice_status VARCHAR(20) DEFAULT NULL COMMENT '发票状态'
        AFTER refund_status;
        """
        db.execute(alter_sql)
        logger.info("✓ invoice_status 字段添加完成")

    logger.info("=" * 50)
    logger.info("V33.0 数据库迁移完成")
    logger.info("=" * 50)


if __name__ == '__main__':
    run_migration()
