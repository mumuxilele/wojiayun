"""
V42.0 商品问答服务 (Q&A)
功能：
  - 用户对商品发起提问
  - 商家/其他用户回复
  - 问答公开可见
  - 追问机制
  - 问答统计

依赖：
- db: 数据库模块
- notification: 通知服务
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)


class ProductQAService(BaseService):
    """商品问答服务"""

    SERVICE_NAME = 'ProductQAService'

    # 问答案件状态
    STATUS_PENDING = 'pending'    # 待回复
    STATUS_ANSWERED = 'answered'  # 已回复
    STATUS_CLOSED = 'closed'      # 已关闭

    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_product_qa WHERE deleted=0")
            base['qa_count'] = result.get('cnt', 0) if result else 0
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base

    # ============ 提问 ============

    def create_question(self, user_id: int, user_name: str,
                       product_id: int, question: str,
                       ec_id: int = 1, project_id: int = 1) -> Dict[str, Any]:
        """
        用户提交商品提问

        Args:
            user_id: 用户ID
            user_name: 用户昵称
            product_id: 商品ID
            question: 提问内容
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            Dict: 操作结果
        """
        try:
            if len(question.strip()) < 5:
                return {'success': False, 'msg': '问题内容至少5个字'}
            if len(question) > 500:
                return {'success': False, 'msg': '问题内容不能超过500字'}

            product = db.get_one(
                "SELECT id, name FROM business_products WHERE id=%s AND deleted=0",
                [product_id]
            )
            if not product:
                return {'success': False, 'msg': '商品不存在'}

            qa_no = self._generate_qa_no()
            question_id = db.execute("""
                INSERT INTO business_product_qa (
                    qa_no, product_id, product_name,
                    user_id, user_name, question,
                    ec_id, project_id, status,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, [
                qa_no, product_id, product['name'],
                user_id, user_name, question,
                ec_id, project_id, self.STATUS_PENDING
            ])

            db.execute(
                "UPDATE business_products SET qa_count = COALESCE(qa_count, 0) + 1 WHERE id=%s",
                [product_id]
            )

            logger.info(f"[ProductQAService] 提问成功: qa_no={qa_no}, product_id={product_id}")

            return {
                'success': True,
                'qa_id': question_id,
                'qa_no': qa_no,
                'msg': '问题已提交'
            }

        except Exception as e:
            logger.error(f"[ProductQAService] 提问失败: {e}")
            return {'success': False, 'msg': str(e)}

    def answer_question(self, question_id: int, answer: str,
                       replier_id: int = None, replier_name: str = '商家',
                       is_staff: bool = False) -> Dict[str, Any]:
        """回复商品提问"""
        try:
            question = db.get_one(
                "SELECT * FROM business_product_qa WHERE id=%s AND deleted=0",
                [question_id]
            )
            if not question:
                return {'success': False, 'msg': '问题不存在'}

            if question['status'] == self.STATUS_CLOSED:
                return {'success': False, 'msg': '问题已关闭'}

            reply_id = db.execute("""
                INSERT INTO business_product_qa_replies (
                    qa_id, replier_id, replier_name, replier_type,
                    content, created_at
                ) VALUES (%s, %s, %s, %s, %s, NOW())
            """, [
                question_id,
                replier_id or 0,
                replier_name,
                'staff' if is_staff else 'user',
                answer
            ])

            db.execute("""
                UPDATE business_product_qa SET status=%s, updated_at=NOW() WHERE id=%s
            """, [self.STATUS_ANSWERED, question_id])

            try:
                from .notification import send_notification
                send_notification(
                    user_id=question['user_id'],
                    title='您的问题已收到回复',
                    content=f'您关于「{question["product_name"]}」的问题已得到回复，快去看看吧',
                    type='qa_reply',
                    ec_id=question['ec_id'],
                    project_id=question['project_id']
                )
            except Exception as e:
                logger.warning(f"[ProductQAService] 发送通知失败: {e}")

            return {'success': True, 'reply_id': reply_id, 'msg': '回复成功'}

        except Exception as e:
            logger.error(f"[ProductQAService] 回复失败: {e}")
            return {'success': False, 'msg': str(e)}

    def add_followup(self, question_id: int, user_id: int,
                     user_name: str, content: str) -> Dict[str, Any]:
        """追问（追加提问）"""
        try:
            question = db.get_one(
                "SELECT * FROM business_product_qa WHERE id=%s AND deleted=0",
                [question_id]
            )
            if not question:
                return {'success': False, 'msg': '问题不存在'}
            if question['user_id'] != user_id:
                return {'success': False, 'msg': '只能追问自己发布的问题'}
            if question['status'] == self.STATUS_CLOSED:
                return {'success': False, 'msg': '问题已关闭'}

            reply_id = db.execute("""
                INSERT INTO business_product_qa_replies (
                    qa_id, replier_id, replier_name, replier_type,
                    content, is_followup, created_at
                ) VALUES (%s, %s, %s, %s, %s, 1, NOW())
            """, [question_id, user_id, user_name, 'user', content])

            db.execute("""
                UPDATE business_product_qa SET status=%s, updated_at=NOW() WHERE id=%s
            """, [self.STATUS_PENDING, question_id])

            return {'success': True, 'reply_id': reply_id, 'msg': '追问成功'}

        except Exception as e:
            logger.error(f"[ProductQAService] 追问失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ 查询 ============

    def get_product_qa_list(self, product_id: int,
                           page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取商品问答列表"""
        try:
            total = db.get_total(
                "SELECT COUNT(*) FROM business_product_qa WHERE product_id=%s AND deleted=0",
                [product_id]
            )

            offset = (page - 1) * page_size
            questions = db.get_all("""
                SELECT * FROM business_product_qa
                WHERE product_id=%s AND deleted=0
                ORDER BY is_top DESC, created_at DESC
                LIMIT %s OFFSET %s
            """, [product_id, page_size, offset]) or []

            for q in questions:
                reply_count = db.get_total(
                    "SELECT COUNT(*) FROM business_product_qa_replies WHERE qa_id=%s",
                    [q['id']]
                )
                q['reply_count'] = reply_count

                latest_reply = db.get_one("""
                    SELECT * FROM business_product_qa_replies
                    WHERE qa_id=%s ORDER BY created_at DESC LIMIT 1
                """, [q['id']])
                q['latest_reply'] = latest_reply

            return {
                'questions': questions,
                'total': total,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size if total else 0
            }

        except Exception as e:
            logger.error(f"[ProductQAService] 获取问答列表失败: {e}")
            return {'questions': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

    def get_qa_detail(self, qa_id: int, current_user_id: int = None) -> Optional[Dict]:
        """获取问答详情"""
        try:
            question = db.get_one(
                "SELECT * FROM business_product_qa WHERE id=%s AND deleted=0",
                [qa_id]
            )
            if not question:
                return None

            replies = db.get_all("""
                SELECT * FROM business_product_qa_replies
                WHERE qa_id=%s ORDER BY created_at ASC
            """, [qa_id]) or []

            question['replies'] = replies
            question['reply_count'] = len(replies)

            return question

        except Exception as e:
            logger.error(f"[ProductQAService] 获取问答详情失败: {e}")
            return None

    def get_user_questions(self, user_id: int,
                          page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取用户的所有提问"""
        try:
            total = db.get_total(
                "SELECT COUNT(*) FROM business_product_qa WHERE user_id=%s AND deleted=0",
                [user_id]
            )

            offset = (page - 1) * page_size
            questions = db.get_all("""
                SELECT q.*, p.name as product_name, p.images as product_images
                FROM business_product_qa q
                LEFT JOIN business_products p ON q.product_id = p.id
                WHERE q.user_id=%s AND q.deleted=0
                ORDER BY q.created_at DESC
                LIMIT %s OFFSET %s
            """, [user_id, page_size, offset]) or []

            return {
                'questions': questions,
                'total': total,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size if total else 0
            }

        except Exception as e:
            logger.error(f"[ProductQAService] 获取用户提问失败: {e}")
            return {'questions': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

    def close_question(self, qa_id: int, user_id: int) -> Dict[str, Any]:
        """用户关闭问题"""
        try:
            question = db.get_one(
                "SELECT * FROM business_product_qa WHERE id=%s AND deleted=0",
                [qa_id]
            )
            if not question:
                return {'success': False, 'msg': '问题不存在'}
            if question['user_id'] != user_id:
                return {'success': False, 'msg': '只能关闭自己的问题'}

            db.execute("""
                UPDATE business_product_qa SET status=%s, updated_at=NOW() WHERE id=%s
            """, [self.STATUS_CLOSED, qa_id])

            return {'success': True, 'msg': '问题已关闭'}

        except Exception as e:
            logger.error(f"[ProductQAService] 关闭问题失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_product_qa_stats(self, product_id: int) -> Dict[str, int]:
        """获取商品问答统计"""
        try:
            total = db.get_total(
                "SELECT COUNT(*) FROM business_product_qa WHERE product_id=%s AND deleted=0",
                [product_id]
            )
            pending = db.get_total(
                "SELECT COUNT(*) FROM business_product_qa WHERE product_id=%s AND status='pending' AND deleted=0",
                [product_id]
            )
            return {'total': total, 'pending': pending}
        except Exception as e:
            logger.error(f"[ProductQAService] 获取统计失败: {e}")
            return {'total': 0, 'pending': 0}

    def _generate_qa_no(self) -> str:
        """生成问答编号"""
        import time, random
        return f"QA{int(time.time())}{random.randint(1000, 9999)}"


# 单例实例
product_qa = ProductQAService()
