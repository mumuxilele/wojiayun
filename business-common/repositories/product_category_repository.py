"""
ProductCategory Repository
商品分类数据访问层
"""
import logging
from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ProductCategoryRepository(BaseRepository):
    """商品分类仓储类"""
    
    TABLE_NAME = 'business_product_categories'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'sort_order ASC, id ASC'
    
    def find_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """根据ID查询分类"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE id = %s AND deleted = 0 LIMIT 1"
        return self.db.get_one(sql, [category_id])
    
    def find_all(self, status: int = None) -> List[Dict[str, Any]]:
        """查询所有分类"""
        conditions = ["deleted = 0"]
        params = []
        
        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where_clause} ORDER BY sort_order ASC, id ASC"
        return self.db.get_all(sql, params) or []
    
    def find_by_parent(self, parent_id: int, status: int = None) -> List[Dict[str, Any]]:
        """根据父级ID查询子分类"""
        conditions = ["parent_id = %s", "deleted = 0"]
        params = [parent_id]
        
        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where_clause} ORDER BY sort_order ASC, id ASC"
        return self.db.get_all(sql, params) or []
    
    def find_by_level(self, level: int, status: int = None) -> List[Dict[str, Any]]:
        """根据层级查询分类"""
        conditions = ["level = %s", "deleted = 0"]
        params = [level]
        
        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where_clause} ORDER BY sort_order ASC, id ASC"
        return self.db.get_all(sql, params) or []
    
    def insert(self, data: Dict[str, Any]) -> int:
        """新增分类，返回新记录ID"""
        sql = f"""
            INSERT INTO {self.TABLE_NAME}
            (name, parent_id, level, sort_order, icon, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        params = [
            data.get('name', ''),
            data.get('parent_id', 0),
            data.get('level', 1),
            data.get('sort_order', 0),
            data.get('icon'),
            data.get('status', 1)
        ]
        self.db.execute(sql, params)
        result = self.db.get_one("SELECT LAST_INSERT_ID() as id")
        return result['id'] if result else 0
    
    def update(self, category_id: int, data: Dict[str, Any]) -> int:
        """更新分类，返回影响行数"""
        fields = []
        params = []
        for field in ['name', 'parent_id', 'level', 'sort_order', 'icon', 'status']:
            if field in data:
                fields.append(f"{field} = %s")
                params.append(data[field])
        if not fields:
            return 0
        fields.append("updated_at = NOW()")
        params.append(category_id)
        sql = f"UPDATE {self.TABLE_NAME} SET {', '.join(fields)} WHERE id = %s AND deleted = 0"
        return self.db.execute(sql, params)
    
    def soft_delete(self, category_id: int) -> int:
        """软删除分类"""
        sql = f"UPDATE {self.TABLE_NAME} SET deleted = 1, updated_at = NOW() WHERE id = %s AND deleted = 0"
        return self.db.execute(sql, [category_id])
    
    def has_children(self, category_id: int) -> bool:
        """判断是否有子分类"""
        sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE parent_id = %s AND deleted = 0"
        result = self.db.get_one(sql, [category_id])
        return (result.get('cnt', 0) if result else 0) > 0
    
    def has_products(self, category_id: int) -> bool:
        """判断分类下是否有商品"""
        sql = "SELECT COUNT(*) as cnt FROM business_products WHERE category_id = %s AND deleted = 0"
        result = self.db.get_one(sql, [category_id])
        return (result.get('cnt', 0) if result else 0) > 0
    
    def get_tree(self, status: int = None) -> List[Dict[str, Any]]:
        """获取分类树（带层级关系）"""
        all_cats = self.find_all(status)
        
        # 构建树形结构
        def build_tree(parent_id=0):
            children = [c for c in all_cats if c['parent_id'] == parent_id]
            for cat in children:
                cat['children'] = build_tree(cat['id'])
            return children
        
        return build_tree()
