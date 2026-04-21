"""
Favorite Service - 收藏业务逻辑层
V48.0: MVC架构改造
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class FavoriteService:
    """收藏服务类"""
    
    def __init__(self):
        from business_common import db
        self.db = db
    
    def get_user_favorites(self,
                           user_id: str,
                           target_type: str = None,
                           page: int = 1,
                           page_size: int = 20) -> Dict[str, Any]:
        """
        获取用户收藏列表
        
        Args:
            user_id: 用户ID
            target_type: 收藏类型 (product/shop/venue/order)
            page: 页码
            page_size: 每页数量
        """
        offset = (page - 1) * page_size
        
        # 构建查询
        conditions = ["f.user_id=%s", "f.deleted=0"]
        params = [user_id]
        
        if target_type:
            conditions.append("f.target_type=%s")
            params.append(target_type)
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        total = self.db.get_total(
            f"SELECT COUNT(*) FROM business_favorites f WHERE {where_clause}",
            params
        )
        
        # 查询列表
        items = self.db.get_all(f"""
            SELECT f.*,
                   CASE f.target_type
                       WHEN 'product' THEN (SELECT product_name FROM business_products WHERE id=f.target_id)
                       WHEN 'shop' THEN (SELECT shop_name FROM business_shops WHERE id=f.target_id)
                       WHEN 'venue' THEN (SELECT venue_name FROM business_venues WHERE id=f.target_id)
                       ELSE ''
                   END as target_name,
                   CASE f.target_type
                       WHEN 'product' THEN (SELECT main_image FROM business_products WHERE id=f.target_id)
                       WHEN 'shop' THEN (SELECT cover_image FROM business_shops WHERE id=f.target_id)
                       WHEN 'venue' THEN (SELECT cover_image FROM business_venues WHERE id=f.target_id)
                       ELSE ''
                   END as target_image,
                   CASE f.target_type
                       WHEN 'product' THEN (SELECT price FROM business_products WHERE id=f.target_id)
                       WHEN 'shop' THEN (SELECT rating FROM business_shops WHERE id=f.target_id)
                       ELSE 0
                   END as target_price
            FROM business_favorites f
            WHERE {where_clause}
            ORDER BY f.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset]) or []
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    def add_favorite(self, 
                     user_id: str,
                     target_type: str,
                     target_id: int) -> Dict[str, Any]:
        """
        添加收藏
        
        Returns:
            {'success': True, 'msg': '收藏成功'}
            或 {'success': False, 'msg': '已收藏'}
        """
        try:
            # 检查是否已收藏
            existing = self.db.get_one(
                "SELECT id FROM business_favorites WHERE user_id=%s AND target_type=%s AND target_id=%s AND deleted=0",
                [user_id, target_type, target_id]
            )
            
            if existing:
                return {'success': False, 'msg': '已收藏'}
            
            # 添加收藏
            self.db.execute("""
                INSERT INTO business_favorites (user_id, target_type, target_id, created_at, deleted)
                VALUES (%s, %s, %s, NOW(), 0)
            """, [user_id, target_type, target_id])
            
            # 更新目标收藏数
            self._update_favorite_count(target_type, target_id, 1)
            
            return {'success': True, 'msg': '收藏成功'}
            
        except Exception as e:
            logger.error(f"添加收藏失败: {e}")
            return {'success': False, 'msg': f'系统错误: {str(e)}'}
    
    def remove_favorite(self,
                        user_id: str,
                        target_type: str,
                        target_id: int) -> Dict[str, Any]:
        """
        取消收藏（软删除）
        """
        try:
            affected = self.db.execute("""
                UPDATE business_favorites 
                SET deleted=1, updated_at=NOW()
                WHERE user_id=%s AND target_type=%s AND target_id=%s AND deleted=0
            """, [user_id, target_type, target_id])
            
            if affected > 0:
                self._update_favorite_count(target_type, target_id, -1)
                return {'success': True, 'msg': '已取消收藏'}
            else:
                return {'success': False, 'msg': '未找到收藏记录'}
                
        except Exception as e:
            logger.error(f"取消收藏失败: {e}")
            return {'success': False, 'msg': f'系统错误: {str(e)}'}
    
    def check_favorite(self,
                       user_id: str,
                       target_type: str,
                       target_id: int) -> bool:
        """检查是否已收藏"""
        existing = self.db.get_one(
            "SELECT id FROM business_favorites WHERE user_id=%s AND target_type=%s AND target_id=%s AND deleted=0",
            [user_id, target_type, target_id]
        )
        return existing is not None
    
    def get_favorite_count(self, user_id: str, target_type: str = None) -> int:
        """获取用户收藏数量"""
        if target_type:
            return self.db.get_total(
                "SELECT COUNT(*) FROM business_favorites WHERE user_id=%s AND target_type=%s AND deleted=0",
                [user_id, target_type]
            )
        else:
            return self.db.get_total(
                "SELECT COUNT(*) FROM business_favorites WHERE user_id=%s AND deleted=0",
                [user_id]
            )
    
    def _update_favorite_count(self, target_type: str, target_id: int, delta: int):
        """更新目标收藏数"""
        try:
            if target_type == 'product':
                table = 'business_products'
                field = 'favorite_count'
            elif target_type == 'shop':
                table = 'business_shops'
                field = 'favorite_count'
            elif target_type == 'venue':
                table = 'business_venues'
                field = 'favorite_count'
            else:
                return
            
            self.db.execute(f"""
                UPDATE {table} 
                SET {field}=GREATEST(COALESCE({field}, 0) + %s, 0), updated_at=NOW()
                WHERE id=%s
            """, [delta, target_id])
            
        except Exception as e:
            logger.warning(f"更新收藏数失败: {e}")


# 单例
_favorite_service = None

def get_favorite_service() -> FavoriteService:
    global _favorite_service
    if _favorite_service is None:
        _favorite_service = FavoriteService()
    return _favorite_service
