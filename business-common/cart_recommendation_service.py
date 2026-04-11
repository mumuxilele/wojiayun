"""
购物车智能推荐服务 V40.0
功能:
  - 基于用户加购/购买历史推荐相关商品
  - 搭配购买推荐
  - 猜你喜欢推荐
  - 看了又看推荐
"""
import logging
from typing import Dict, List, Optional, Any
from . import db

logger = logging.getLogger(__name__)


class CartRecommendationService:
    """购物车智能推荐服务"""

    # 推荐数量配置
    RECOMMEND_COUNT = 6  # 默认推荐数量
    MAX_HISTORY_ITEMS = 20  # 历史记录最大条数

    @classmethod
    def get_recommendations(cls, user_id: int, ec_id: int, project_id: int,
                           recommend_type: str = 'cart',
                           exclude_product_ids: List[int] = None) -> List[Dict]:
        """
        获取智能推荐

        Args:
            user_id: 用户ID
            ec_id: 企业ID
            project_id: 项目ID
            recommend_type: 推荐类型
                - 'cart': 购物车推荐（基于购物车商品）
                - 'viewed': 浏览足迹推荐（看了又看）
                - 'purchased': 购买历史推荐
                - 'similar': 相似商品推荐
            exclude_product_ids: 排除的商品ID列表

        Returns:
            List[Dict]: 推荐商品列表
        """
        try:
            if recommend_type == 'cart':
                return cls._recommend_by_cart(user_id, ec_id, project_id, exclude_product_ids)
            elif recommend_type == 'viewed':
                return cls._recommend_by_viewed(user_id, ec_id, project_id, exclude_product_ids)
            elif recommend_type == 'purchased':
                return cls._recommend_by_purchased(user_id, ec_id, project_id, exclude_product_ids)
            elif recommend_type == 'similar':
                return cls._recommend_by_similar(user_id, ec_id, project_id, exclude_product_ids)
            else:
                return cls._recommend_by_cart(user_id, ec_id, project_id, exclude_product_ids)
        except Exception as e:
            logger.error(f"获取推荐失败: user_id={user_id}, type={recommend_type}, error={e}")
            return []

    @classmethod
    def _recommend_by_cart(cls, user_id: int, ec_id: int, project_id: int,
                          exclude_product_ids: List[int] = None) -> List[Dict]:
        """
        基于购物车内容推荐
        策略：
        1. 获取购物车商品分类
        2. 查找同类商品中销量高的
        3. 搭配购买率高的组合商品
        """
        # 获取购物车商品及其分类
        cart_items = db.get_all("""
            SELECT DISTINCT p.category, p.product_name
            FROM business_cart c
            JOIN business_products p ON c.product_id = p.id
            WHERE c.user_id=%s AND c.deleted=0 AND p.deleted=0
            LIMIT 5
        """, [user_id]) or []

        if not cart_items:
            # 购物车为空，返回热销推荐
            return cls._get_hot_products(ec_id, project_id, exclude_product_ids)

        categories = [item['category'] for item in cart_items if item.get('category')]
        if not categories:
            return cls._get_hot_products(ec_id, project_id, exclude_product_ids)

        # 构建排除条件
        exclude_sql = ""
        exclude_params = []
        if exclude_product_ids:
            placeholders = ','.join(['%s'] * len(exclude_product_ids))
            exclude_sql = f" AND p.id NOT IN ({placeholders})"
            exclude_params = exclude_product_ids

        # 查询同类热销商品
        placeholders = ','.join(['%s'] * len(categories))
        sql = f"""
            SELECT p.id, p.product_name, p.price, p.original_price, p.images,
                   p.stock, p.sales_count, p.category,
                   COALESCE(AVG(r.rating), 5.0) as avg_rating
            FROM business_products p
            LEFT JOIN business_reviews r ON p.id = r.target_id AND r.target_type='product' AND r.deleted=0
            WHERE p.ec_id=%s AND p.project_id=%s
              AND p.category IN ({placeholders})
              AND p.status='active' AND p.deleted=0
              {exclude_sql}
            GROUP BY p.id
            ORDER BY p.sales_count DESC, avg_rating DESC
            LIMIT %s
        """
        params = [ec_id, project_id] + categories + exclude_params + [cls.RECOMMEND_COUNT]

        return db.get_all(sql, params) or []

    @classmethod
    def _recommend_by_viewed(cls, user_id: int, ec_id: int, project_id: int,
                            exclude_product_ids: List[int] = None) -> List[Dict]:
        """
        基于浏览足迹推荐（看了又看）
        策略：
        1. 获取用户最近浏览的商品
        2. 查找浏览过同类商品的用户也浏览过的其他商品
        """
        # 获取用户浏览历史
        viewed = db.get_all("""
            SELECT DISTINCT target_id, view_type
            FROM business_recently_viewed
            WHERE user_id=%s AND view_type='product'
            ORDER BY viewed_at DESC
            LIMIT 10
        """, [user_id]) or []

        if not viewed:
            return cls._recommend_by_purchased(user_id, ec_id, project_id, exclude_product_ids)

        viewed_ids = [str(v['target_id']) for v in viewed if v.get('target_id')]

        # 构建排除条件
        exclude_sql = ""
        exclude_params = []
        if exclude_product_ids:
            placeholders = ','.join(['%s'] * len(exclude_product_ids))
            exclude_sql = f" AND p.id NOT IN ({placeholders})"
            exclude_params = exclude_product_ids

        # 查找浏览过同类商品的用户也浏览过的商品
        sql = f"""
            SELECT p.id, p.product_name, p.price, p.original_price, p.images,
                   p.stock, p.sales_count, p.category,
                   COUNT(DISTINCT rv2.user_id) as viewer_count
            FROM business_products p
            JOIN business_recently_viewed rv1 ON p.id = rv1.target_id AND rv1.view_type='product'
            JOIN business_recently_viewed rv2 ON rv1.user_id = rv2.user_id AND rv2.view_type='product'
            WHERE rv1.target_id IN ({','.join(viewed_ids)})
              AND p.ec_id=%s AND p.project_id=%s
              AND p.status='active' AND p.deleted=0
              {exclude_sql}
            GROUP BY p.id
            ORDER BY viewer_count DESC, p.sales_count DESC
            LIMIT %s
        """
        params = [ec_id, project_id] + exclude_params + [cls.RECOMMEND_COUNT]

        return db.get_all(sql, params) or []

    @classmethod
    def _recommend_by_purchased(cls, user_id: int, ec_id: int, project_id: int,
                                exclude_product_ids: List[int] = None) -> List[Dict]:
        """
        基于购买历史推荐
        策略：
        1. 获取用户购买过的商品分类
        2. 推荐同类或关联分类的商品
        """
        # 获取用户购买过的商品分类
        purchased = db.get_all("""
            SELECT DISTINCT p.category
            FROM business_orders o
            JOIN business_order_items oi ON o.id = oi.order_id
            JOIN business_products p ON oi.product_id = p.id
            WHERE o.user_id=%s AND o.pay_status='paid' AND o.deleted=0
            LIMIT 5
        """, [user_id]) or []

        if not purchased:
            return cls._get_hot_products(ec_id, project_id, exclude_product_ids)

        categories = [p['category'] for p in purchased if p.get('category')]
        if not categories:
            return cls._get_hot_products(ec_id, project_id, exclude_product_ids)

        # 构建排除条件
        exclude_sql = ""
        exclude_params = []
        if exclude_product_ids:
            placeholders = ','.join(['%s'] * len(exclude_product_ids))
            exclude_sql = f" AND p.id NOT IN ({placeholders})"
            exclude_params = exclude_product_ids

        # 查询同类热销商品
        placeholders = ','.join(['%s'] * len(categories))
        sql = f"""
            SELECT p.id, p.product_name, p.price, p.original_price, p.images,
                   p.stock, p.sales_count, p.category,
                   COALESCE(AVG(r.rating), 5.0) as avg_rating
            FROM business_products p
            LEFT JOIN business_reviews r ON p.id = r.target_id AND r.target_type='product' AND r.deleted=0
            WHERE p.ec_id=%s AND p.project_id=%s
              AND p.category IN ({placeholders})
              AND p.status='active' AND p.deleted=0
              {exclude_sql}
            GROUP BY p.id
            ORDER BY p.sales_count DESC, avg_rating DESC
            LIMIT %s
        """
        params = [ec_id, project_id] + categories + exclude_params + [cls.RECOMMEND_COUNT]

        return db.get_all(sql, params) or []

    @classmethod
    def _recommend_by_similar(cls, user_id: int, ec_id: int, project_id: int,
                              exclude_product_ids: List[int] = None) -> List[Dict]:
        """
        相似商品推荐
        基于商品名称/描述的关键词匹配
        """
        # 获取用户最近浏览或购买商品的名称关键词
        keywords = db.get_all("""
            SELECT DISTINCT SUBSTRING(p.product_name, 1, 4) as keyword
            FROM (
                SELECT target_id FROM business_recently_viewed WHERE user_id=%s AND view_type='product' ORDER BY viewed_at DESC LIMIT 5
                UNION
                SELECT oi.product_id as target_id
                FROM business_orders o
                JOIN business_order_items oi ON o.id = oi.order_id
                WHERE o.user_id=%s AND o.pay_status='paid' AND o.deleted=0
                ORDER BY o.created_at DESC LIMIT 5
            ) t
            JOIN business_products p ON t.target_id = p.id
            WHERE p.deleted=0 AND p.status='active'
        """, [user_id, user_id]) or []

        if not keywords:
            return cls._get_hot_products(ec_id, project_id, exclude_product_ids)

        keyword_list = [kw['keyword'] for kw in keywords if kw.get('keyword')]

        # 构建排除条件
        exclude_sql = ""
        exclude_params = []
        if exclude_product_ids:
            placeholders = ','.join(['%s'] * len(exclude_product_ids))
            exclude_sql = f" AND p.id NOT IN ({placeholders})"
            exclude_params = exclude_product_ids

        # 使用LIKE匹配相似商品
        conditions = ' OR '.join(['p.product_name LIKE %s' for _ in keyword_list])
        sql = f"""
            SELECT p.id, p.product_name, p.price, p.original_price, p.images,
                   p.stock, p.sales_count, p.category
            FROM business_products p
            WHERE p.ec_id=%s AND p.project_id=%s
              AND ({conditions})
              AND p.status='active' AND p.deleted=0
              {exclude_sql}
            ORDER BY p.sales_count DESC
            LIMIT %s
        """
        params = [ec_id, project_id] + [f"%{kw}%" for kw in keyword_list] + exclude_params + [cls.RECOMMEND_COUNT]

        return db.get_all(sql, params) or []

    @classmethod
    def _get_hot_products(cls, ec_id: int, project_id: int,
                         exclude_product_ids: List[int] = None) -> List[Dict]:
        """
        获取热销商品推荐（兜底策略）
        """
        exclude_sql = ""
        exclude_params = []
        if exclude_product_ids:
            placeholders = ','.join(['%s'] * len(exclude_product_ids))
            exclude_sql = f" AND p.id NOT IN ({placeholders})"
            exclude_params = exclude_product_ids

        sql = f"""
            SELECT p.id, p.product_name, p.price, p.original_price, p.images,
                   p.stock, p.sales_count, p.category,
                   COALESCE(AVG(r.rating), 5.0) as avg_rating
            FROM business_products p
            LEFT JOIN business_reviews r ON p.id = r.target_id AND r.target_type='product' AND r.deleted=0
            WHERE p.ec_id=%s AND p.project_id=%s
              AND p.status='active' AND p.deleted=0
              {exclude_sql}
            GROUP BY p.id
            ORDER BY p.sales_count DESC, avg_rating DESC
            LIMIT %s
        """
        params = [ec_id, project_id] + exclude_params + [cls.RECOMMEND_COUNT]

        return db.get_all(sql, params) or []

    @classmethod
    def get_combo_recommendation(cls, product_ids: List[int], ec_id: int, project_id: int) -> List[Dict]:
        """
        获取搭配购买推荐
        基于用户购买历史，计算经常一起购买的商品组合
        """
        if not product_ids:
            return []

        placeholders = ','.join(['%s'] * len(product_ids))

        # 查找购买过这些商品的用户，也购买过的其他商品
        sql = f"""
            SELECT p.id, p.product_name, p.price, p.original_price, p.images,
                   p.stock, p.sales_count,
                   COUNT(DISTINCT o2.user_id) as combo_count
            FROM business_order_items oi1
            JOIN business_orders o1 ON oi1.order_id = o1.id AND o1.pay_status='paid'
            JOIN business_order_items oi2 ON o1.id = oi2.order_id AND oi2.product_id != oi1.product_id
            JOIN business_products p ON oi2.product_id = p.id
            WHERE oi1.product_id IN ({placeholders})
              AND p.ec_id=%s AND p.project_id=%s
              AND p.status='active' AND p.deleted=0
            GROUP BY p.id
            ORDER BY combo_count DESC
            LIMIT 4
        """
        params = product_ids + [ec_id, project_id]

        return db.get_all(sql, params) or []


# 全局单例
cart_recommendation = CartRecommendationService()
