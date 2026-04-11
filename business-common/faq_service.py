"""
FAQ知识库服务 V32.0
功能:
  - 常见问题分类管理
  - FAQ内容管理
  - 智能检索（关键词匹配）
  - 用户反馈与满意度评价
"""
import logging
import re
from datetime import datetime
from . import db

logger = logging.getLogger(__name__)


class FAQService:
    """FAQ知识库服务"""

    # FAQ状态
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_OFFLINE = 'offline'

    # 问题类型
    CATEGORIES = {
        'order': '订单问题',
        'payment': '支付问题',
        'refund': '退款问题',
        'delivery': '配送问题',
        'product': '商品问题',
        'account': '账户问题',
        'member': '会员问题',
        'other': '其他问题'
    }

    @classmethod
    def get_categories(cls, ec_id=None, project_id=None):
        """获取问题分类列表"""
        categories = []
        for key, name in cls.CATEGORIES.items():
            # 统计各分类下的FAQ数量
            count = db.get_total("""
                SELECT COUNT(*) FROM business_faqs
                WHERE category=%s AND status='published' AND deleted=0
                AND (ec_id=%s OR ec_id IS NULL)
                AND (project_id=%s OR project_id IS NULL)
            """, [key, ec_id, project_id]) if ec_id else db.get_total("""
                SELECT COUNT(*) FROM business_faqs
                WHERE category=%s AND status='published' AND deleted=0
            """, [key])

            categories.append({
                'key': key,
                'name': name,
                'count': count
            })

        return categories

    @classmethod
    def get_faqs(cls, category=None, keyword=None, ec_id=None, project_id=None,
                 page=1, page_size=10):
        """
        获取FAQ列表

        Args:
            category: 分类
            keyword: 搜索关键词
            ec_id: 企业ID
            project_id: 项目ID
            page: 页码
            page_size: 每页数量

        Returns:
            dict: {'items': [...], 'total': int, 'page': int, 'page_size': int}
        """
        try:
            where = "f.status='published' AND f.deleted=0"
            params = []

            if category:
                where += " AND f.category=%s"
                params.append(category)

            if keyword:
                where += " AND (f.question LIKE %s OR f.answer LIKE %s OR f.tags LIKE %s)"
                kw = f'%{keyword}%'
                params.extend([kw, kw, kw])

            if ec_id:
                where += " AND (f.ec_id=%s OR f.ec_id IS NULL)"
                params.append(ec_id)
            if project_id:
                where += " AND (f.project_id=%s OR f.project_id IS NULL)"
                params.append(project_id)

            # 统计总数
            total = db.get_total(f"SELECT COUNT(*) FROM business_faqs f WHERE {where}", params)

            # 分页查询
            offset = (page - 1) * page_size
            faqs = db.get_all(f"""
                SELECT f.id, f.question, f.answer, f.category, f.views, f.helpful_count,
                       f.not_helpful_count, f.tags, f.created_at, f.updated_at
                FROM business_faqs f
                WHERE {where}
                ORDER BY f.views DESC, f.helpful_count DESC
                LIMIT %s OFFSET %s
            """, params + [page_size, offset])

            return {
                'items': faqs or [],
                'total': total,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size if total else 0
            }

        except Exception as e:
            logger.error(f"获取FAQ列表失败: {e}")
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

    @classmethod
    def get_faq_detail(cls, faq_id, ec_id=None, project_id=None):
        """
        获取FAQ详情

        Returns:
            dict: FAQ详情
        """
        try:
            # 增加浏览数
            db.execute("""
                UPDATE business_faqs SET views=views+1 WHERE id=%s
            """, [faq_id])

            sql = """
                SELECT * FROM business_faqs
                WHERE id=%s AND status='published' AND deleted=0
            """
            params = [faq_id]

            if ec_id:
                sql += " AND (ec_id=%s OR ec_id IS NULL)"
                params.append(ec_id)
            if project_id:
                sql += " AND (project_id=%s OR project_id IS NULL)"
                params.append(project_id)

            faq = db.get_one(sql, params)

            if faq:
                # 获取相关FAQ
                related = db.get_all("""
                    SELECT id, question FROM business_faqs
                    WHERE category=%s AND id!=%s AND status='published' AND deleted=0
                    ORDER BY views DESC LIMIT 5
                """, [faq['category'], faq_id])
                faq['related'] = related or []

                # 获取反馈统计
                stats = db.get_one("""
                    SELECT helpful_count, not_helpful_count FROM business_faqs WHERE id=%s
                """, [faq_id])
                faq['feedback_stats'] = {
                    'helpful': stats.get('helpful_count', 0) if stats else 0,
                    'not_helpful': stats.get('not_helpful_count', 0) if stats else 0,
                    'total': (stats.get('helpful_count', 0) + stats.get('not_helpful_count', 0)) if stats else 0
                }

            return faq

        except Exception as e:
            logger.error(f"获取FAQ详情失败: faq_id={faq_id}, error={e}")
            return None

    @classmethod
    def search_faqs(cls, query, ec_id=None, project_id=None, limit=10):
        """
        智能搜索FAQ

        Args:
            query: 搜索词
            ec_id: 企业ID
            project_id: 项目ID
            limit: 返回数量

        Returns:
            list: 匹配的FAQ列表
        """
        try:
            if not query or len(query.strip()) < 2:
                return []

            # 分词
            keywords = cls._extract_keywords(query)

            if not keywords:
                return []

            # 构建搜索条件
            conditions = []
            params = []
            for kw in keywords:
                conditions.append("(f.question LIKE %s OR f.answer LIKE %s OR f.tags LIKE %s)")
                params.extend([f'%{kw}%', f'%{kw}%', f'%{kw}%'])

            where = f"({' OR '.join(conditions)}) AND f.status='published' AND f.deleted=0"

            if ec_id:
                where += " AND (f.ec_id=%s OR f.ec_id IS NULL)"
                params.append(ec_id)
            if project_id:
                where += " AND (f.project_id=%s OR f.project_id IS NULL)"
                params.append(project_id)

            # 匹配度计算：优先匹配问题标题
            order_by = """
                CASE WHEN f.question LIKE %s THEN 1
                     WHEN f.question LIKE %s THEN 2
                     ELSE 3
                END,
                f.views DESC,
                f.helpful_count DESC
            """
            params.extend([f'{query}', f'%{query}%'])

            faqs = db.get_all(f"""
                SELECT f.id, f.question, f.answer, f.category,
                       f.views, f.helpful_count,
                       CASE WHEN f.question LIKE %s THEN 1 ELSE 0 END as match_level
                FROM business_faqs f
                WHERE {where}
                ORDER BY {order_by}
                LIMIT %s
            """, params + [f'{query}%', limit])

            return faqs or []

        except Exception as e:
            logger.error(f"搜索FAQ失败: query={query}, error={e}")
            return []

    @classmethod
    def _extract_keywords(cls, text):
        """提取关键词"""
        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)
        # 分词（简单按空格分）
        words = text.split()
        # 过滤停用词和太短的词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '怎', '么', '吗', '呢'}
        keywords = [w for w in words if len(w) >= 2 and w not in stop_words]
        return keywords[:5]  # 最多返回5个关键词

    @classmethod
    def create_faq(cls, question, answer, category, tags='',
                   ec_id=None, project_id=None, created_by=None):
        """
        创建FAQ

        Returns:
            dict: {'success': bool, 'msg': str, 'faq_id': int}
        """
        if not question or not answer:
            return {'success': False, 'msg': '问题和答案不能为空'}

        try:
            faq_no = f'FAQ{datetime.now().strftime("%Y%m%d%H%M%S")}'
            faq_id = db.execute("""
                INSERT INTO business_faqs
                (faq_no, question, answer, category, tags, status, ec_id, project_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [faq_no, question, answer, category, tags,
                  cls.STATUS_DRAFT, ec_id, project_id, created_by])

            return {'success': True, 'msg': 'FAQ创建成功', 'faq_id': faq_id}

        except Exception as e:
            logger.error(f"创建FAQ失败: {e}")
            return {'success': False, 'msg': '创建失败'}

    @classmethod
    def submit_feedback(cls, faq_id, user_id, is_helpful):
        """
        提交FAQ有帮助/无帮助反馈

        Returns:
            dict: {'success': bool, 'msg': str}
        """
        try:
            # 检查是否已反馈
            existing = db.get_one("""
                SELECT id FROM business_faq_feedback
                WHERE faq_id=%s AND user_id=%s
            """, [faq_id, user_id])

            if existing:
                return {'success': False, 'msg': '您已反馈过此问题'}

            # 记录反馈
            db.execute("""
                INSERT INTO business_faq_feedback (faq_id, user_id, is_helpful)
                VALUES (%s, %s, %s)
            """, [faq_id, user_id, 1 if is_helpful else 0])

            # 更新FAQ统计
            if is_helpful:
                db.execute("UPDATE business_faqs SET helpful_count=helpful_count+1 WHERE id=%s", [faq_id])
            else:
                db.execute("UPDATE business_faqs SET not_helpful_count=not_helpful_count+1 WHERE id=%s", [faq_id])

            return {'success': True, 'msg': '感谢您的反馈'}

        except Exception as e:
            logger.error(f"提交FAQ反馈失败: faq_id={faq_id}, error={e}")
            return {'success': False, 'msg': '反馈失败'}

    @classmethod
    def submit_question(cls, question, user_id, contact_info='',
                       ec_id=None, project_id=None):
        """
        用户提交新问题（知识库未收录时）

        Returns:
            dict: {'success': bool, 'msg': str}
        """
        if not question or len(question.strip()) < 5:
            return {'success': False, 'msg': '请详细描述您的问题（至少5个字）'}

        try:
            question_no = f'Q{datetime.now().strftime("%Y%m%d%H%M%S")}'
            db.execute("""
                INSERT INTO business_faq_questions
                (question_no, question, user_id, contact_info, status, ec_id, project_id)
                VALUES (%s, %s, %s, %s, 'pending', %s, %s)
            """, [question_no, question.strip(), user_id, contact_info, ec_id, project_id])

            # 发送通知给管理员
            try:
                from .notification import send_notification
                send_notification(
                    user_id='admin',
                    title='用户提交新问题',
                    content=f'用户提交了新问题：「{question[:50]}...」',
                    notify_type='faq_question',
                    ec_id=ec_id,
                    project_id=project_id
                )
            except:
                pass

            return {'success': True, 'msg': '您的问题已提交，我们会尽快回复'}

        except Exception as e:
            logger.error(f"提交问题失败: {e}")
            return {'success': False, 'msg': '提交失败'}

    @classmethod
    def get_hot_faqs(cls, ec_id=None, project_id=None, limit=10):
        """获取热门FAQ（按浏览量和满意度排序）"""
        try:
            where = "f.status='published' AND f.deleted=0"
            params = []

            if ec_id:
                where += " AND (f.ec_id=%s OR f.ec_id IS NULL)"
                params.append(ec_id)
            if project_id:
                where += " AND (f.project_id=%s OR f.project_id IS NULL)"
                params.append(project_id)

            faqs = db.get_all(f"""
                SELECT f.id, f.question, f.answer, f.category, f.views, f.helpful_count,
                       ROUND(f.helpful_count / NULLIF(f.helpful_count + f.not_helpful_count, 0) * 100, 0) as satisfaction
                FROM business_faqs f
                WHERE {where}
                ORDER BY f.views DESC, f.helpful_count DESC
                LIMIT %s
            """, params + [limit])

            return faqs or []

        except Exception as e:
            logger.error(f"获取热门FAQ失败: {e}")
            return []


# 便捷实例
faq_service = FAQService()
