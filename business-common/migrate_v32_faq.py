"""
V32.0 迁移脚本 - FAQ知识库系统
- 创建FAQ表
- 创建FAQ反馈表
- 创建用户提交问题表
"""
import logging
from . import db

logger = logging.getLogger(__name__)


def run():
    """执行迁移"""
    logger.info("开始 V32.0 FAQ知识库系统迁移...")

    # 1. 创建FAQ表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_faqs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                faq_no VARCHAR(32) NOT NULL UNIQUE COMMENT 'FAQ编号',
                question VARCHAR(500) NOT NULL COMMENT '问题标题',
                answer TEXT NOT NULL COMMENT '问题答案',
                category VARCHAR(20) NOT NULL DEFAULT 'other' COMMENT '分类: order/payment/refund/delivery/product/account/member/other',
                tags VARCHAR(500) DEFAULT NULL COMMENT '标签(逗号分隔)',
                status VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT '状态: draft/published/offline',
                views INT DEFAULT 0 COMMENT '浏览次数',
                helpful_count INT DEFAULT 0 COMMENT '有帮助次数',
                not_helpful_count INT DEFAULT 0 COMMENT '无帮助次数',
                ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID(Null表示通用)',
                project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                created_by VARCHAR(64) DEFAULT NULL COMMENT '创建人',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                deleted TINYINT(1) DEFAULT 0 COMMENT '删除标记',
                INDEX idx_category (category),
                INDEX idx_status (status),
                INDEX idx_views (views),
                INDEX idx_ec_project (ec_id, project_id),
                FULLTEXT INDEX idx_search (question, answer, tags)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='常见问题表'
        """)
        logger.info("  ✓ 创建表: business_faqs")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_faqs 失败: {e}")

    # 2. 创建FAQ反馈表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_faq_feedback (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                faq_id BIGINT NOT NULL COMMENT 'FAQ ID',
                user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
                is_helpful TINYINT(1) NOT NULL COMMENT '是否有用: 1-有用, 0-无用',
                feedback_content VARCHAR(500) DEFAULT NULL COMMENT '反馈内容(可选)',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_faq (faq_id),
                INDEX idx_user (user_id),
                UNIQUE KEY uk_faq_user (faq_id, user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='FAQ反馈表'
        """)
        logger.info("  ✓ 创建表: business_faq_feedback")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_faq_feedback 失败: {e}")

    # 3. 创建用户提交问题表
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS business_faq_questions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                question_no VARCHAR(32) NOT NULL UNIQUE COMMENT '问题编号',
                question TEXT NOT NULL COMMENT '用户提交的问题',
                user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
                contact_info VARCHAR(100) DEFAULT NULL COMMENT '联系方式',
                status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/processed/rejected',
                reply TEXT DEFAULT NULL COMMENT '管理员回复',
                replied_by VARCHAR(64) DEFAULT NULL COMMENT '回复人',
                replied_at DATETIME DEFAULT NULL COMMENT '回复时间',
                ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
                project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user (user_id),
                INDEX idx_status (status),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户提交问题表'
        """)
        logger.info("  ✓ 创建表: business_faq_questions")
    except Exception as e:
        logger.warning(f"  ! 创建表 business_faq_questions 失败: {e}")

    # 4. 插入示例FAQ
    try:
        existing = db.get_total("SELECT COUNT(*) FROM business_faqs WHERE status='published'")
        if existing == 0:
            sample_faqs = [
                ("如何查看我的订单？", "登录后进入「我的订单」页面即可查看所有订单，包括待付款、待发货、待收货、已完成等状态的订单。", "order", "订单,查看"),
                ("如何申请退款？", "进入「我的订单」，找到需要退款的订单，点击「申请退款」按钮，填写退款原因后提交即可。我们会在1-3个工作日内处理。", "refund", "退款,退货,取消"),
                ("支付方式有哪些？", "我们支持微信支付、支付宝、银联卡支付等多种支付方式。在结算页面选择您方便的支付方式即可。", "payment", "支付,微信,支付宝"),
                ("订单什么时候发货？", "一般情况下，订单付款后24小时内我们会安排发货。实际发货时间可能因商品库存情况有所不同，具体请查看订单详情。", "delivery", "发货,物流,快递"),
                ("如何成为会员？", "注册并完成首次消费后自动成为会员。会员可享受积分返利、专属优惠等权益。消费越多，会员等级越高，权益越丰富。", "member", "会员,积分,等级"),
            ]
            for q, a, c, t in sample_faqs:
                db.execute("""
                    INSERT INTO business_faqs (faq_no, question, answer, category, tags, status)
                    VALUES (%s, %s, %s, %s, %s, 'published')
                """, [f'FAQ{dt.now().strftime("%Y%m%d%H%M%S")}', q, a, c, t])
            logger.info("  ✓ 插入示例FAQ数据")
    except Exception as e:
        logger.warning(f"  ! 插入示例FAQ失败: {e}")

    logger.info("V32.0 FAQ知识库系统迁移完成!")


if __name__ == '__main__':
    run()
