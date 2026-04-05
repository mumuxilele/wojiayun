"""
内容审核服务模块 V22.0
功能:
  - 敏感词过滤
  - 广告识别
  - 恶意网址检测
  - 评价安全审核
"""
import re
import logging
from . import db

logger = logging.getLogger(__name__)


class ContentModeration:
    """内容审核服务"""

    # 敏感词分类
    SENSITIVE_WORDS = {
        # 政治敏感 (简化示例)
        'political': [],
        # 色情低俗
        'porn': ['色情', '裸', '成人', '约炮', '一夜情'],
        # 暴力恐怖
        'violence': ['杀人', '打架', '砍死', '揍死'],
        # 违禁品
        'illegal': ['毒品', '枪支', '假币'],
        # 广告推销
        'ad': ['加V', '微信', 'QQ', '官网', '秒杀群', '优惠券领取'],
        # 政治敏感词 (实际需要更完整的词库)
        'political': ['游行', '抗议'],
    }

    # 违禁网址正则
    URL_PATTERNS = [
        r'https?://[^\s]+',  # HTTP/HTTPS URL
        r'www\.[^\s]+',
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9._%+-]+\.[a-zA-Z]{2,}',  # Email
    ]

    # 联系方式正则
    CONTACT_PATTERNS = [
        (r'微信\s*[：:]?\s*[a-zA-Z0-9_]{6,20}', '微信'),
        (r'QQ\s*[：:]?\s*[0-9]{5,12}', 'QQ'),
        (r'手机\s*[：:]?\s*1[3-9][0-9]{9}', '手机号'),
        (r'电话\s*[：:]?\s*1[3-9][0-9]{9}', '电话'),
    ]

    @staticmethod
    def moderate_text(text, category='all'):
        """
        审核文本内容

        Args:
            text: 待审核文本
            category: 审核类别 (all/porn/violence/ad)

        Returns:
            dict: 审核结果
                - passed: bool, 是否通过
                - risk_level: int, 风险等级 (0安全/1低风险/2中风险/3高风险)
                - reasons: list, 违规原因
                - suggestions: list, 建议
        """
        if not text:
            return {
                'passed': True,
                'risk_level': 0,
                'reasons': [],
                'suggestions': [],
            }

        text_lower = text.lower()
        reasons = []
        suggestions = []
        risk_score = 0

        # 1. 敏感词检测
        word_result = ContentModeration._check_sensitive_words(text)
        if word_result['found']:
            risk_score += word_result['risk'] * 2
            reasons.extend(word_result['reasons'])

        # 2. 联系方式检测
        contact_result = ContentModeration._check_contacts(text)
        if contact_result['found']:
            risk_score += 1
            reasons.append('包含联系方式')
            suggestions.append('建议删除联系方式以保护隐私')

        # 3. 网址检测
        url_result = ContentModeration._check_urls(text)
        if url_result['found']:
            risk_score += 2
            reasons.append('包含外部链接')
            suggestions.append('建议删除外部链接以防诈骗')

        # 4. 重复字符检测 (刷屏)
        repeat_result = ContentModeration._check_repeat(text)
        if repeat_result['found']:
            risk_score += 1
            reasons.append('疑似刷屏内容')

        # 5. 文本长度检查
        if len(text) < 5:
            risk_score += 1
            reasons.append('内容过短')
        elif len(text) > 2000:
            risk_score += 1
            suggestions.append('内容过长，建议精简')

        # 计算风险等级
        if risk_score >= 6:
            risk_level = 3  # 高风险
        elif risk_score >= 3:
            risk_level = 2  # 中风险
        elif risk_score >= 1:
            risk_level = 1  # 低风险
        else:
            risk_level = 0  # 安全

        passed = risk_level < 2  # 中风险及以下通过

        return {
            'passed': passed,
            'risk_level': risk_level,
            'reasons': list(set(reasons)),  # 去重
            'suggestions': list(set(suggestions)),
            'risk_score': risk_score,
        }

    @staticmethod
    def _check_sensitive_words(text):
        """检测敏感词"""
        found_words = []
        risk_level = 0

        for category, words in ContentModeration.SENSITIVE_WORDS.items():
            for word in words:
                if word in text:
                    found_words.append(f"[{category}] {word}")
                    # 根据类别加权
                    if category in ['political', 'illegal']:
                        risk_level = max(risk_level, 3)
                    elif category in ['porn', 'violence']:
                        risk_level = max(risk_level, 2)
                    elif category == 'ad':
                        risk_level = max(risk_level, 1)

        return {
            'found': len(found_words) > 0,
            'words': found_words,
            'risk': risk_level,
            'reasons': [f'包含敏感词: {w}' for w in found_words[:5]],  # 最多显示5个
        }

    @staticmethod
    def _check_contacts(text):
        """检测联系方式"""
        found = []
        for pattern, name in ContentModeration.CONTACT_PATTERNS:
            if re.search(pattern, text):
                found.append(name)

        return {
            'found': len(found) > 0,
            'contacts': found,
        }

    @staticmethod
    def _check_urls(text):
        """检测外部链接"""
        found_urls = []
        for pattern in ContentModeration.URL_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                found_urls.extend(matches)

        return {
            'found': len(found_urls) > 0,
            'urls': found_urls[:3],  # 最多显示3个
        }

    @staticmethod
    def _check_repeat(text):
        """检测重复刷屏"""
        # 连续重复字符超过5次
        repeat_pattern = r'(.)\1{5,}'
        if re.search(repeat_pattern, text):
            return {'found': True}

        # 检查是否是纯重复词句
        words = text.split()
        if len(words) > 3:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:  # 重复率超过70%
                return {'found': True}

        return {'found': False}

    @staticmethod
    def moderate_review(review_id):
        """
        审核评价 (管理员调用)

        Args:
            review_id: 评价ID

        Returns:
            dict: 审核结果
        """
        try:
            review = db.get_one(
                "SELECT * FROM business_reviews WHERE id=%s",
                [review_id]
            )
            if not review:
                return {'success': False, 'msg': '评价不存在'}

            # 审核文本内容
            text = f"{review.get('content', '')} {review.get('title', '')}"
            mod_result = ContentModeration.moderate_text(text)

            # 更新评价状态
            if mod_result['risk_level'] >= 2:
                # 高风险评价需要人工审核
                new_status = 'pending_review'
            else:
                new_status = 'approved'

            db.execute("""
                UPDATE business_reviews
                SET moderation_status=%s,
                    moderation_result=%s,
                    moderated_at=NOW()
                WHERE id=%s
            """, [new_status, json.dumps(mod_result, ensure_ascii=False), review_id])

            return {
                'success': True,
                'data': {
                    'review_id': review_id,
                    'status': new_status,
                    'moderation': mod_result,
                }
            }

        except Exception as e:
            logger.error(f"审核评价失败: review_id={review_id}, error={e}")
            return {'success': False, 'msg': f'审核失败: {str(e)}'}

    @staticmethod
    def auto_approve_safe_reviews():
        """
        自动审核安全评价 (定时任务调用)
        自动批准低风险评价
        """
        try:
            # 获取待审核评价
            pending = db.get_all("""
                SELECT id, content, title
                FROM business_reviews
                WHERE moderation_status IS NULL OR moderation_status = 'pending'
            """)

            approved_count = 0
            for review in (pending or []):
                text = f"{review.get('content', '')} {review.get('title', '')}"
                result = ContentModeration.moderate_text(text)

                if result['risk_level'] < 2:  # 低风险自动通过
                    db.execute("""
                        UPDATE business_reviews
                        SET moderation_status='approved',
                            moderation_result=%s,
                            moderated_at=NOW()
                        WHERE id=%s
                    """, [json.dumps(result, ensure_ascii=False), review['id']])
                    approved_count += 1

            logger.info(f"自动审核完成: 批准 {approved_count} 条评价")
            return approved_count

        except Exception as e:
            logger.error(f"自动审核失败: {e}")
            return 0

    @staticmethod
    def get_unchecked_reviews(limit=50):
        """获取待人工审核的评价"""
        try:
            reviews = db.get_all("""
                SELECT r.*, u.user_name
                FROM business_reviews r
                LEFT JOIN business_members u ON r.user_id = u.user_id
                WHERE r.moderation_status = 'pending_review'
                ORDER BY r.created_at DESC
                LIMIT %s
            """, [limit])

            # 解析审核结果
            import json
            for review in (reviews or []):
                if review.get('moderation_result'):
                    try:
                        review['moderation_detail'] = json.loads(review['moderation_result'])
                    except:
                        review['moderation_detail'] = {}

            return reviews or []

        except Exception as e:
            logger.error(f"获取待审核评价失败: {e}")
            return []


import json  # 确保json可用
# 便捷实例
moderation = ContentModeration()
