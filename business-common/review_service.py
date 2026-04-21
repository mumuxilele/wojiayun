"""
Review Service - 评价业务逻辑层
V48.0: MVC架构改造
职责：封装评价相关业务逻辑
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ReviewService:
    """评价服务类"""
    
    def __init__(self):
        from business_common import db
        self.db = db
    
    # ============ 统计更新 ============
    
    def update_target_rating(self, target_type: str, target_id: int) -> bool:
        """
        更新目标实体的评分统计
        
        Args:
            target_type: 目标类型 (shop/product/venue)
            target_id: 目标ID
            
        Returns:
            True-成功, False-失败
        """
        try:
            # 查询评分统计
            stats = self.db.get_one("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
                FROM business_reviews 
                WHERE target_type=%s AND target_id=%s AND deleted=0
            """, [target_type, target_id])
            
            if not stats:
                return True
            
            avg_rating = round(float(stats['avg_rating'] or 0), 1)
            review_count = stats['review_count'] or 0
            
            # 根据类型更新对应表
            if target_type == 'shop':
                table = 'business_shops'
            elif target_type == 'product':
                table = 'business_products'
            elif target_type == 'venue':
                table = 'business_venues'
            else:
                return False
            
            self.db.execute(f"""
                UPDATE {table} SET rating=%s, review_count=%s, updated_at=NOW() WHERE id=%s
            """, [avg_rating, review_count, target_id])
            
            return True
            
        except Exception as e:
            logger.warning(f"更新评价统计失败: {e}")
            return False
    
    def update_order_review_stats(self, order_id: int) -> bool:
        """更新订单的评价统计"""
        return self.update_target_rating('order', order_id)
    
    # ============ 评价列表 ============
    
    def get_user_reviews(self, 
                        user_id: str,
                        page: int = 1,
                        page_size: int = 20) -> Dict[str, Any]:
        """
        获取用户的评价列表
        
        Returns:
            {
                'items': [...],
                'total': int,
                'page': int,
                'page_size': int
            }
        """
        offset = (page - 1) * page_size
        
        # 查询总数
        total = self.db.get_total(
            "SELECT COUNT(*) FROM business_reviews WHERE user_id=%s AND deleted=0",
            [user_id]
        )
        
        # 查询列表
        items = self.db.get_all("""
            SELECT r.*, 
                   CASE r.target_type
                       WHEN 'order' THEN (SELECT order_no FROM business_orders WHERE id=r.target_id)
                       WHEN 'shop' THEN (SELECT shop_name FROM business_shops WHERE id=r.target_id)
                       WHEN 'product' THEN (SELECT product_name FROM business_products WHERE id=r.target_id)
                       ELSE ''
                   END as target_name
            FROM business_reviews r
            WHERE r.user_id=%s AND r.deleted=0
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """, [user_id, page_size, offset]) or []
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    def get_product_reviews(self,
                            product_id: int,
                            page: int = 1,
                            page_size: int = 10) -> Dict[str, Any]:
        """获取商品的评价列表"""
        offset = (page - 1) * page_size
        
        total = self.db.get_total(
            "SELECT COUNT(*) FROM business_reviews WHERE target_type='product' AND target_id=%s AND deleted=0",
            [product_id]
        )
        
        items = self.db.get_all("""
            SELECT r.*, u.user_name, u.avatar
            FROM business_reviews r
            LEFT JOIN business_users u ON r.user_id=u.user_id
            WHERE r.target_type='product' AND r.target_id=%s AND r.deleted=0
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """, [product_id, page_size, offset]) or []
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    # ============ 评价统计 ============
    
    def get_review_stats(self, target_type: str, target_id: int) -> Dict[str, Any]:
        """获取评价统计"""
        stats = self.db.get_one("""
            SELECT 
                COUNT(*) as total,
                AVG(rating) as avg_rating,
                SUM(CASE WHEN rating=5 THEN 1 ELSE 0 END) as five_star,
                SUM(CASE WHEN rating=4 THEN 1 ELSE 0 END) as four_star,
                SUM(CASE WHEN rating=3 THEN 1 ELSE 0 END) as three_star,
                SUM(CASE WHEN rating=2 THEN 1 ELSE 0 END) as two_star,
                SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END) as one_star
            FROM business_reviews
            WHERE target_type=%s AND target_id=%s AND deleted=0
        """, [target_type, target_id])
        
        if stats:
            stats['avg_rating'] = round(float(stats['avg_rating'] or 0), 1)
        
        return stats or {
            'total': 0, 'avg_rating': 0,
            'five_star': 0, 'four_star': 0, 'three_star': 0,
            'two_star': 0, 'one_star': 0
        }


# 单例
_review_service = None

def get_review_service() -> ReviewService:
    """获取 ReviewService 单例"""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service
