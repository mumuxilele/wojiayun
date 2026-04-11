"""
搜索增强服务 V44.0

功能:
1. 热门搜索词统计与推荐
2. 搜索历史记录（服务端存储）
3. 搜索建议（Suggest）- 实时补全
4. 搜索结果为空时的引导（相关商品/热门商品）
5. 拼音/首字母匹配（简单实现）
"""

import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from . import db
from .cache_service import cache_get, cache_set, cache_delete

logger = logging.getLogger(__name__)


# 拼音首字母映射（简化版，覆盖高频商业词汇）
PINYIN_INITIALS = {
    # 服装类
    '上': 's', '下': 'x', '衣': 'y', '裤': 'k', '裙': 'q', '鞋': 'x',
    # 食品类
    '牛': 'n', '猪': 'z', '鸡': 'j', '鱼': 'y', '米': 'm', '面': 'm',
    # 电子类
    '手': 's', '机': 'j', '电': 'd', '脑': 'n', '平': 'p', '板': 'b',
    # 家居类
    '沙': 's', '发': 'f', '床': 'c', '椅': 'y', '柜': 'g', '桌': 'z',
}


def extract_initials(text: str) -> str:
    """提取中文词的首字母（简化实现）"""
    result = []
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            result.append(PINYIN_INITIALS.get(char, ''))
        elif char.isalpha():
            result.append(char.lower())
    return ''.join(result)


class SearchEnhanceService:
    """搜索增强服务"""

    CACHE_TTL_HOT = 600     # 热词缓存10分钟
    CACHE_TTL_SUGGEST = 60  # 建议缓存1分钟
    MAX_HISTORY = 20        # 每用户最多保存20条历史
    MAX_HOT_WORDS = 10      # 最多展示10个热门词

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """确保搜索相关表存在"""
        try:
            # 搜索热词统计表
            exists = db.get_one("SHOW TABLES LIKE 'business_search_hot_words'")
            if not exists:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_search_hot_words (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        keyword VARCHAR(100) NOT NULL COMMENT '搜索关键词',
                        search_count INT DEFAULT 1 COMMENT '搜索次数',
                        is_manual TINYINT(1) DEFAULT 0 COMMENT '是否手动置顶',
                        manual_rank INT DEFAULT 0 COMMENT '手动排序',
                        ec_id INT DEFAULT 1,
                        project_id INT DEFAULT 1,
                        last_searched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_keyword (keyword, ec_id, project_id),
                        INDEX idx_count (search_count DESC),
                        INDEX idx_scope (ec_id, project_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='搜索热词统计表'
                """)
                logger.info("business_search_hot_words 表已创建")

            # 用户搜索历史表
            exists2 = db.get_one("SHOW TABLES LIKE 'business_search_history'")
            if not exists2:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_search_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL COMMENT '用户ID',
                        keyword VARCHAR(100) NOT NULL COMMENT '搜索关键词',
                        result_count INT DEFAULT 0 COMMENT '结果数量',
                        searched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_user_keyword (user_id, keyword),
                        INDEX idx_user (user_id),
                        INDEX idx_time (searched_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户搜索历史表'
                """)
                logger.info("business_search_history 表已创建")

        except Exception as e:
            logger.warning(f"初始化搜索增强表失败: {e}")

    # ============ 热门搜索 ============

    def get_hot_words(self, ec_id: int = None, project_id: int = None, limit: int = 10) -> List[Dict]:
        """获取热门搜索词"""
        cache_key = f"search_hot_{ec_id}_{project_id}"
        cached = cache_get(cache_key)
        if cached:
            return cached[:limit]

        where = "1=1"
        params = []
        if ec_id:
            where += " AND (ec_id=%s OR ec_id=1)"
            params.append(ec_id)
        if project_id:
            where += " AND (project_id=%s OR project_id=1)"
            params.append(project_id)

        words = db.get_all(f"""
            SELECT keyword, search_count, is_manual
            FROM business_search_hot_words
            WHERE {where}
            ORDER BY is_manual DESC, manual_rank DESC, search_count DESC
            LIMIT %s
        """, params + [self.MAX_HOT_WORDS]) or []

        result = [{'keyword': w['keyword'], 'count': w['search_count']} for w in words]

        # 如果没有数据，返回默认热词
        if not result:
            result = [
                {'keyword': '蔬菜', 'count': 0},
                {'keyword': '水果', 'count': 0},
                {'keyword': '日用品', 'count': 0},
                {'keyword': '牛奶', 'count': 0},
                {'keyword': '零食', 'count': 0},
            ]

        cache_set(cache_key, result, self.CACHE_TTL_HOT)
        return result[:limit]

    def record_search(
        self,
        keyword: str,
        user_id: int = None,
        result_count: int = 0,
        ec_id: int = None,
        project_id: int = None,
    ):
        """记录搜索行为（同步热词统计 + 用户历史）"""
        keyword = keyword.strip()[:100]
        if not keyword:
            return

        # 更新热词统计
        try:
            db.execute("""
                INSERT INTO business_search_hot_words
                    (keyword, search_count, ec_id, project_id, last_searched_at)
                VALUES (%s, 1, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    search_count = search_count + 1,
                    last_searched_at = NOW()
            """, [keyword, ec_id or 1, project_id or 1])
            # 清除缓存
            cache_delete(f"search_hot_{ec_id}_{project_id}")
        except Exception as e:
            logger.warning(f"更新搜索热词失败: {e}")

        # 更新用户搜索历史
        if user_id:
            try:
                db.execute("""
                    INSERT INTO business_search_history (user_id, keyword, result_count, searched_at)
                    VALUES (%s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        result_count = %s,
                        searched_at = NOW()
                """, [user_id, keyword, result_count, result_count])

                # 保持最多MAX_HISTORY条记录
                self._trim_history(user_id)
            except Exception as e:
                logger.warning(f"记录用户搜索历史失败: {e}")

    def _trim_history(self, user_id: int):
        """保持用户搜索历史在限制数量内"""
        try:
            count = db.get_total(
                "SELECT COUNT(*) FROM business_search_history WHERE user_id=%s", [user_id]
            )
            if count > self.MAX_HISTORY:
                # 删除最旧的记录
                db.execute("""
                    DELETE FROM business_search_history
                    WHERE user_id=%s
                    ORDER BY searched_at ASC
                    LIMIT %s
                """, [user_id, count - self.MAX_HISTORY])
        except Exception as e:
            logger.warning(f"清理搜索历史失败: {e}")

    # ============ 搜索历史 ============

    def get_user_history(self, user_id: int, limit: int = 10) -> List[str]:
        """获取用户搜索历史"""
        rows = db.get_all("""
            SELECT keyword FROM business_search_history
            WHERE user_id=%s
            ORDER BY searched_at DESC
            LIMIT %s
        """, [user_id, limit]) or []
        return [r['keyword'] for r in rows]

    def clear_user_history(self, user_id: int) -> Dict:
        """清除用户搜索历史"""
        try:
            db.execute(
                "DELETE FROM business_search_history WHERE user_id=%s", [user_id]
            )
            return {'success': True, 'msg': '搜索历史已清除'}
        except Exception as e:
            return {'success': False, 'msg': str(e)}

    def delete_history_item(self, user_id: int, keyword: str) -> Dict:
        """删除单条搜索历史"""
        try:
            db.execute(
                "DELETE FROM business_search_history WHERE user_id=%s AND keyword=%s",
                [user_id, keyword]
            )
            return {'success': True, 'msg': '已删除'}
        except Exception as e:
            return {'success': False, 'msg': str(e)}

    # ============ 搜索建议（Suggest）============

    def get_suggestions(
        self,
        keyword: str,
        ec_id: int = None,
        project_id: int = None,
        limit: int = 8,
    ) -> List[str]:
        """
        获取搜索建议
        优先从商品名称中找，再补充热词
        """
        keyword = keyword.strip()
        if len(keyword) < 1:
            return []

        cache_key = f"suggest_{ec_id}_{project_id}_{keyword}"
        cached = cache_get(cache_key)
        if cached:
            return cached

        suggestions = set()

        # 1. 从商品名称中模糊匹配
        try:
            products = db.get_all("""
                SELECT DISTINCT name FROM business_products
                WHERE name LIKE %s AND deleted=0 AND status='active'
                LIMIT %s
            """, [f'%{keyword}%', limit * 2]) or []
            for p in products:
                suggestions.add(p['name'])
        except Exception:
            pass

        # 2. 从热词中模糊匹配
        try:
            hot = db.get_all("""
                SELECT keyword FROM business_search_hot_words
                WHERE keyword LIKE %s
                ORDER BY search_count DESC
                LIMIT %s
            """, [f'%{keyword}%', limit]) or []
            for h in hot:
                suggestions.add(h['keyword'])
        except Exception:
            pass

        result = list(suggestions)[:limit]
        cache_set(cache_key, result, self.CACHE_TTL_SUGGEST)
        return result

    # ============ 空结果引导 ============

    def get_empty_result_guide(
        self,
        keyword: str,
        ec_id: int = None,
        project_id: int = None,
    ) -> Dict:
        """
        搜索无结果时返回引导内容
        - 相似关键词建议
        - 热门商品推荐
        """
        # 获取相关热词
        related_keywords = self.get_suggestions(keyword, ec_id, project_id, limit=5)

        # 获取热门商品（作为备选）
        hot_products = []
        try:
            where = "deleted=0 AND status='active'"
            params = []
            if ec_id:
                where += " AND (ec_id=%s OR ec_id IS NULL)"
                params.append(ec_id)
            if project_id:
                where += " AND (project_id=%s OR project_id IS NULL)"
                params.append(project_id)

            hot_products = db.get_all(f"""
                SELECT id, name, price, image_url, sales_count
                FROM business_products
                WHERE {where}
                ORDER BY sales_count DESC, created_at DESC
                LIMIT 6
            """, params) or []
        except Exception as e:
            logger.warning(f"获取热门商品失败: {e}")

        return {
            'keyword': keyword,
            'related_keywords': related_keywords,
            'hot_products': hot_products,
            'tips': [
                '检查输入是否有误',
                '尝试更简短的关键词',
                '试试相关词语',
            ]
        }

    # ============ 管理端：热词管理 ============

    def set_manual_hot_word(
        self, keyword: str, rank: int, ec_id: int, project_id: int
    ) -> Dict:
        """手动设置热门搜索词（管理端）"""
        try:
            db.execute("""
                INSERT INTO business_search_hot_words
                    (keyword, search_count, is_manual, manual_rank, ec_id, project_id)
                VALUES (%s, 0, 1, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    is_manual=1, manual_rank=%s, updated_at=NOW()
            """, [keyword, rank, ec_id, project_id, rank])
            cache_delete(f"search_hot_{ec_id}_{project_id}")
            return {'success': True, 'msg': '热词设置成功'}
        except Exception as e:
            return {'success': False, 'msg': str(e)}

    def remove_manual_hot_word(self, keyword: str, ec_id: int, project_id: int) -> Dict:
        """移除手动热词"""
        try:
            db.execute("""
                UPDATE business_search_hot_words
                SET is_manual=0, manual_rank=0, updated_at=NOW()
                WHERE keyword=%s AND ec_id=%s AND project_id=%s
            """, [keyword, ec_id, project_id])
            cache_delete(f"search_hot_{ec_id}_{project_id}")
            return {'success': True, 'msg': '已移除'}
        except Exception as e:
            return {'success': False, 'msg': str(e)}


# 全局单例
search_enhance = SearchEnhanceService()
