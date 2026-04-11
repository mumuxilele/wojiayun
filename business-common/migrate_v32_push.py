"""
V32.0 迁移脚本 - 消息推送中心
- 创建推送模板表
- 创建推送消息表
- 创建推送任务表
"""
import logging
from . import db

logger = logging.getLogger(__name__)


def run():
    """执行迁移"""
    logger.info("开始 V32.0 消息推送中心迁移...")

    # 1. 创建推送模板表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_push_templates (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                template_code VARCHAR(50) NOT NULL UNIQUE COMMENT '模板代码',
                template_name VARCHAR(100) NOT NULL COMMENT '模板名称',
                title_template VARCHAR(200) NOT NULL COMMENT '标题模板',
                content_template TEXT NOT NULL COMMENT '内容模板(支持{变量})',
                channels JSON DEFAULT NULL COMMENT '推送渠道列表: in_app/sms/wechat/email',
                msg_type VARCHAR(20) NOT NULL DEFAULT 'system' COMMENT '消息类型',
                status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '状态: active/inactive',
                ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID(Null表示通用模板)',
                project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                created_by VARCHAR(64) DEFAULT NULL COMMENT '创建人',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted TINYINT(1) DEFAULT 0 COMMENT '删除标记',
                INDEX idx_code (template_code),
                INDEX idx_type (msg_type),
                INDEX idx_status (status),
                INDEX idx_ec_project (ec_id, project_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推送模板表'
        """)
        logger.info("  ✓ 创建表: business_push_templates")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_push_templates 失败: {e}")

    # 2. 创建推送消息表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_push_messages (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                msg_no VARCHAR(32) NOT NULL UNIQUE COMMENT '消息编号',
                user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
                title VARCHAR(200) NOT NULL COMMENT '消息标题',
                content TEXT NOT NULL COMMENT '消息内容',
                template_code VARCHAR(50) DEFAULT NULL COMMENT '模板代码',
                channels JSON DEFAULT NULL COMMENT '推送渠道',
                msg_type VARCHAR(20) NOT NULL DEFAULT 'system' COMMENT '消息类型',
                priority VARCHAR(10) NOT NULL DEFAULT 'normal' COMMENT '优先级: high/normal/low',
                status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/sent/failed/partial',
                result JSON DEFAULT NULL COMMENT '发送结果',
                is_read TINYINT(1) DEFAULT 0 COMMENT '是否已读',
                read_at DATETIME DEFAULT NULL COMMENT '读取时间',
                sent_at DATETIME DEFAULT NULL COMMENT '发送时间',
                ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
                project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user (user_id),
                INDEX idx_type (msg_type),
                INDEX idx_status (status),
                INDEX idx_created (created_at),
                INDEX idx_user_unread (user_id, is_read)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推送消息表'
        """)
        logger.info("  ✓ 创建表: business_push_messages")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_push_messages 失败: {e}")

    # 3. 创建推送任务表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_push_tasks (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                task_no VARCHAR(32) NOT NULL UNIQUE COMMENT '任务编号',
                template_code VARCHAR(50) NOT NULL COMMENT '模板代码',
                user_ids JSON NOT NULL COMMENT '用户ID列表',
                params JSON NOT NULL COMMENT '模板参数',
                channels JSON DEFAULT NULL COMMENT '推送渠道',
                send_at DATETIME NOT NULL COMMENT '计划发送时间',
                executed_at DATETIME DEFAULT NULL COMMENT '实际执行时间',
                status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/running/completed/failed',
                result JSON DEFAULT NULL COMMENT '执行结果',
                ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
                project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                created_by VARCHAR(64) DEFAULT NULL COMMENT '创建人',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_status (status),
                INDEX idx_send_at (send_at),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推送任务表'
        """)
        logger.info("  ✓ 创建表: business_push_tasks")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_push_tasks 失败: {e}")

    # 4. 插入默认模板
    try:
        existing = db.get_total("SELECT COUNT(*) FROM business_push_templates")
        if existing == 0:
            default_templates = [
                ('order_created', '订单创建通知', '订单已创建', '您的订单 {order_no} 已创建，金额 {amount} 元',
                 '["in_app"]', 'order'),
                ('order_paid', '支付成功通知', '支付成功', '您的订单 {order_no} 已支付成功，金额 {amount} 元',
                 '["in_app", "wechat"]', 'payment'),
                ('order_shipped', '发货通知', '订单已发货', '您的订单 {order_no} 已发货，快递 {express_name}，单号 {tracking_no}',
                 '["in_app", "wechat"]', 'delivery'),
                ('order_delivered', '收货提醒', '订单已送达', '您的订单 {order_no} 已送达，请确认收货',
                 '["in_app"]', 'delivery'),
                ('refund_approved', '退款成功通知', '退款已处理', '您的退款申请已通过，金额 {amount} 元将退还至您的账户',
                 '["in_app", "wechat"]', 'refund'),
                ('reminder', '系统提醒', '待处理提醒', '{content}', '["in_app"]', 'system'),
            ]
            for code, name, title, content, channels, msg_type in default_templates:
                db.execute("""
                    INSERT INTO business_push_templates
                    (template_code, template_name, title_template, content_template, channels, msg_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [code, name, title, content, channels, msg_type])
            logger.info("  ✓ 插入默认推送模板")
    except Exception as e:
        logger.warning(f"  ! 插入默认模板失败: {e}")

    logger.info("V32.0 消息推送中心迁移完成!")


if __name__ == '__main__':
    run()
