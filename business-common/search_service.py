"""
搜索服务模块 V22.0
功能:
  - 商品全文搜索
  - 搜索历史记录
  - 热门搜索词
  - 智能推荐 (基于搜索词)
"""
import re
import logging
from collections import Counter
from datetime import datetime, timedelta
from . import db

logger = logging.getLogger(__name__)

# 搜索配置
MIN_SEARCH_LENGTH = 2  # 最小搜索词长度
MAX_SEARCH_RESULTS = 50  # 最大返回结果数
HOT_SEARCH_LIMIT = 20  # 热门搜索词数量
SEARCH_HISTORY_LIMIT = 10  # 用户搜索历史数量


class SearchService:
    """统一搜索服务"""

    # 停用词 (不计入搜索和统计)
    STOP_WORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '什', '么', '吗', '吧', '呢', '啊', '哦', '嗯', '啦',
        '呀', '哇', '嘛', '嗨', '唉', '喂', '嘿', '哈', '哟'
    }

    # 热门搜索词 (管理员可配置)
    STICKY_HOT_WORDS = ['优惠', '打折', '新品', '热卖', '推荐']

    @staticmethod
    def search_products(keyword, ec_id=None, project_id=None,
                        page=1, page_size=20, category_id=None,
                        min_price=None, max_price=None,
                        sort='relevance', user_id=None):
        """
        商品搜索

        Args:
            keyword: 搜索关键词
            ec_id: 企业ID
            project_id: 项目ID
            page: 页码
            page_size: 每页数量
            category_id: 分类筛选
            min_price/max_price: 价格区间
            sort: 排序方式 (relevance/sales/price_asc/price_desc/new)
            user_id: 用户ID (用于记录搜索历史)

        Returns:
            dict: 搜索结果
        """
        if not keyword or len(keyword.strip()) < MIN_SEARCH_LENGTH:
            return {'success': False, 'msg': f'搜索词至少{MIN_SEARCH_LENGTH}个字符'}

        keyword = keyword.strip()
        result = {
            'keyword': keyword,
            'page': page,
            'page_size': page_size,
            'total': 0,
            'items': [],
            'suggestions': [],
        }

        try:
            # 1. 记录搜索历史
            if user_id:
                SearchService._record_search_history(user_id, keyword, ec_id, project_id)

            # 2. 构建搜索查询
            where_clauses = ["p.deleted=0", "p.status=1"]
            params = []

            if ec_id:
                where_clauses.append("p.ec_id=%s")
                params.append(ec_id)
            if project_id:
                where_clauses.append("p.project_id=%s")
                params.append(project_id)

            # 关键词搜索 (多字段匹配)
            keyword_conditions = []
            keyword_params = []

            # 精确匹配名称 (最高权重)
            keyword_conditions.append("p.name LIKE %s")
            keyword_params.append(f'%{keyword}%')

            # 描述匹配
            keyword_conditions.append("p.description LIKE %s")
            keyword_params.append(f'%{keyword}%')

            # 标签匹配
            keyword_conditions.append("p.tags LIKE %s")
            keyword_params.append(f'%{keyword}%')

            # 如果有中文，使用简单分词后搜索
            chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
            if chinese_pattern.search(keyword):
                # 简单bigram分词
                words = [keyword[i:i+2] for i in range(len(keyword)-1)]
                for word in words:
                    if word not in SearchService.STOP_WORDS:
                        keyword_conditions.append("(p.name LIKE %s OR p.description LIKE %s OR p.tags LIKE %s)")
                        keyword_params.extend([f'%{word}%', f'%{word}%', f'%{word}%'])

            where_clauses.append(f"({' OR '.join(keyword_conditions)})")
            params.extend(keyword_params)

            # 分类筛选
            if category_id:
                where_clauses.append("p.category_id=%s")
                params.append(category_id)

            # 价格区间
            if min_price is not None:
                where_clauses.append("p.price >= %s")
                params.append(float(min_price))
            if max_price is not None:
                where_clauses.append("p.price <= %s")
                params.append(float(max_price))

            where_sql = " AND ".join(where_clauses)

            # 排序
            order_sql = SearchService._build_sort_sql(sort, keyword)

            # 总数查询
            count_sql = f"""
                SELECT COUNT(DISTINCT p.id)
                FROM business_products p
                LEFT JOIN business_product_categories c ON p.category_id = c.id
                WHERE {where_sql}
            """
            total = db.get_total(count_sql, params)
            result['total'] = total

            # 分页查询
            offset = (page - 1) * page_size
            search_sql = f"""
                SELECT p.id, p.name, p.price, p.original_price, p.image,
                       p.category_id, c.name as category_name,
                       p.stock, p.sales_count, p.view_count,
                       p.tags, p.description
                FROM business_products p
                LEFT JOIN business_product_categories c ON p.category_id = c.id
                WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT %s OFFSET %s
            """
            search_params = params + [page_size, offset]

            items = db.get_all(search_sql, search_params)

            # 格式化结果
            for item in (items or []):
                result['items'].append({
                    'id': item['id'],
                    'name': item['name'],
                    'price': float(item['price']),
                    'original_price': float(item['original_price']) if item.get('original_price') else None,
                    'image': item.get('image', ''),
                    'category_id': item.get('category_id'),
                    'category_name': item.get('category_name'),
                    'stock': item.get('stock', 0),
                    'sales_count': item.get('sales_count', 0),
                    'tags': item.get('tags', ''),
                    'description': (item.get('description') or '')[:100] + '...' if len((item.get('description') or '')) > 100 else (item.get('description') or ''),
                })

            # 搜索建议
            result['suggestions'] = SearchService._get_search_suggestions(keyword)

            logger.info(f"商品搜索: keyword={keyword}, total={total}")
            return {'success': True, 'data': result}

        except Exception as e:
            logger.error(f"商品搜索失败: keyword={keyword}, error={e}")
            # 回退到基础搜索
            return SearchService._fallback_search(keyword, ec_id, project_id, page, page_size)

    @staticmethod
    def _fallback_search(keyword, ec_id, project_id, page, page_size):
        """回退搜索 (不使用全文索引)"""
        where_clauses = ["p.deleted=0", "p.status=1"]
        params = []

        if ec_id:
            where_clauses.append("p.ec_id=%s")
            params.append(ec_id)
        if project_id:
            where_clauses.append("p.project_id=%s")
            params.append(project_id)

        # 使用LIKE搜索
        where_clauses.append("(p.name LIKE %s OR p.description LIKE %s OR p.tags LIKE %s)")
        params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

        where_sql = " AND ".join(where_clauses)

        # 总数
        count_sql = f"SELECT COUNT(*) FROM business_products p WHERE {where_sql}"
        total = db.get_total(count_sql, params)

        # 分页
        offset = (page - 1) * page_size
        search_sql = f"""
            SELECT p.id, p.name, p.price, p.original_price, p.image,
                   p.category_id, c.name as category_name,
                   p.stock, p.sales_count, p.view_count, p.tags
            FROM business_products p
            LEFT JOIN business_product_categories c ON p.category_id = c.id
            WHERE {where_sql}
            ORDER BY p.sales_count DESC, p.view_count DESC
            LIMIT %s OFFSET %s
        """
        items = db.get_all(search_sql, params + [page_size, offset])

        result_items = []
        for item in (items or []):
            result_items.append({
                'id': item['id'],
                'name': item['name'],
                'price': float(item['price']),
                'original_price': float(item['original_price']) if item.get('original_price') else None,
                'image': item.get('image', ''),
                'category_name': item.get('category_name'),
                'stock': item.get('stock', 0),
                'sales_count': item.get('sales_count', 0),
                'tags': item.get('tags', ''),
            })

        logger.info(f"回退搜索: keyword={keyword}, total={total}")
        return {
            'success': True,
            'data': {
                'keyword': keyword,
                'page': page,
                'page_size': page_size,
                'total': total,
                'items': result_items,
                'suggestions': [],
                'fallback': True,  # 标记为回退搜索
            }
        }

    @staticmethod
    def _build_sort_sql(sort, keyword):
        """构建排序SQL"""
        sort_map = {
            'relevance': 'p.sales_count DESC, p.view_count DESC',
            'sales': 'p.sales_count DESC',
            'price_asc': 'p.price ASC',
            'price_desc': 'p.price DESC',
            'new': 'p.id DESC',
            'hot': 'p.view_count DESC, p.sales_count DESC',
        }
        return sort_map.get(sort, 'p.sales_count DESC')

    @staticmethod
    def _get_search_suggestions(keyword):
        """获取搜索建议 (自动补全)"""
        if len(keyword) < 1:
            return []

        suggestions = []
        try:
            # 从商品名称中匹配
            matches = db.get_all("""
                SELECT DISTINCT name FROM business_products
                WHERE deleted=0 AND status=1 AND name LIKE %s
                LIMIT 5
            """, [f'{keyword}%'])

            for m in (matches or []):
                if m['name'] not in suggestions:
                    suggestions.append(m['name'])
        except Exception as e:
            logger.warning(f"获取搜索建议失败: {e}")

        return suggestions[:5]

    @staticmethod
    def _record_search_history(user_id, keyword, ec_id, project_id):
        """记录用户搜索历史"""
        try:
            # 去重: 先删除同用户同关键词的旧记录
            db.execute("""
                DELETE FROM business_search_history
                WHERE user_id=%s AND keyword=%s
            """, [user_id, keyword])

            # 插入新记录
            db.execute("""
                INSERT INTO business_search_history
                   (user_id, keyword, ec_id, project_id, searched_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, [user_id, keyword, ec_id, project_id])

            # 清理过旧记录 (保留最近100条)
            db.execute("""
                DELETE FROM business_search_history
                WHERE user_id=%s AND id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM business_search_history
                        WHERE user_id=%s
                        ORDER BY searched_at DESC
                        LIMIT 100
                    ) as t
                )
            """, [user_id, user_id])

        except Exception as e:
            logger.warning(f"记录搜索历史失败: {e}")

    @staticmethod
    def get_user_search_history(user_id, limit=SEARCH_HISTORY_LIMIT):
        """获取用户搜索历史"""
        try:
            history = db.get_all("""
                SELECT DISTINCT keyword, MAX(searched_at) as last_searched
                FROM business_search_history
                WHERE user_id=%s
                GROUP BY keyword
                ORDER BY last_searched DESC
                LIMIT %s
            """, [user_id, limit])
            return [h['keyword'] for h in (history or [])]
        except Exception as e:
            logger.warning(f"获取搜索历史失败: {e}")
            return []

    @staticmethod
    def clear_user_search_history(user_id):
        """清除用户搜索历史"""
        try:
            db.execute("DELETE FROM business_search_history WHERE user_id=%s", [user_id])
            return True
        except Exception as e:
            logger.error(f"清除搜索历史失败: {e}")
            return False

    @staticmethod
    def get_hot_search_words(ec_id=None, project_id=None, limit=HOT_SEARCH_LIMIT):
        """获取热门搜索词"""
        try:
            # 统计搜索次数
            where_clauses = ["1=1"]
            params = []

            if ec_id:
                where_clauses.append("ec_id=%s")
                params.append(ec_id)
            if project_id:
                where_clauses.append("project_id=%s")
                params.append(project_id)

            # 只统计最近7天
            where_clauses.append("searched_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")

            where_sql = " AND ".join(where_clauses)

            hot_words = db.get_all(f"""
                SELECT keyword, COUNT(*) as search_count
                FROM business_search_history
                WHERE {where_sql}
                GROUP BY keyword
                ORDER BY search_count DESC
                LIMIT %s
            """, params + [limit])

            result = []
            for h in (hot_words or []):
                # 过滤停用词
                if h['keyword'] not in SearchService.STOP_WORDS:
                    result.append({
                        'keyword': h['keyword'],
                        'count': h['search_count'],
                    })

            # 添加置顶热词
            for word in SearchService.STICKY_HOT_WORDS:
                if len(result) >= limit:
                    break
                if not any(r['keyword'] == word for r in result):
                    result.insert(0, {'keyword': word, 'count': 0, 'sticky': True})

            return result[:limit]

        except Exception as e:
            logger.warning(f"获取热门搜索词失败: {e}")
            return []

    @staticmethod
    def get_recommended_products(user_id, ec_id=None, project_id=None, limit=10):
        """
        获取推荐商品 (基于用户搜索历史和购买记录)

        简单实现: 推荐同类别商品
        """
        try:
            recommendations = []

            # 方式1: 基于搜索历史推荐
            history = SearchService.get_user_search_history(user_id, limit=5)
            if history:
                for keyword in history[:3]:
                    products = db.get_all("""
                        SELECT id, name, price, image, sales_count
                        FROM business_products
                        WHERE deleted=0 AND status=1
                        AND (name LIKE %s OR tags LIKE %s)
                        ORDER BY sales_count DESC
                        LIMIT 3
                    """, [f'%{keyword}%', f'%{keyword}%'])

                    for p in (products or []):
                        if p not in recommendations:
                            recommendations.append({
                                'id': p['id'],
                                'name': p['name'],
                                'price': float(p['price']),
                                'image': p.get('image', ''),
                                'reason': f'因为您搜索过「{keyword}」',
                            })

            # 方式2: 热卖推荐
            hot_products = db.get_all(f"""
                SELECT id, name, price, image, sales_count
                FROM business_products
                WHERE deleted=0 AND status=1 AND stock > 0
                {'AND ec_id=%s' if ec_id else ''}
                ORDER BY sales_count DESC
                LIMIT %s
            """, ([ec_id] if ec_id else []) + [limit])

            for p in (hot_products or []):
                if len(recommendations) >= limit:
                    break
                if not any(r['id'] == p['id'] for r in recommendations):
                    recommendations.append({
                        'id': p['id'],
                        'name': p['name'],
                        'price': float(p['price']),
                        'image': p.get('image', ''),
                        'reason': '热销推荐',
                    })

            return recommendations[:limit]

        except Exception as e:
            logger.warning(f"获取推荐商品失败: {e}")
            return []


# 便捷实例
search = SearchService()
