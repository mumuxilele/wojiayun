"""
Product Repository
商品数据访问层
"""
import logging
from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ProductRepository(BaseRepository):
    """商品仓储类"""
    
    TABLE_NAME = 'business_products'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'
    
    # ============ 查询 ============
    
    def find_on_sale(self,
                     ec_id: str = None,
                     project_id: str = None,
                     category_id: int = None,
                     keyword: str = None,
                     page: int = 1,
                     page_size: int = 20) -> Dict[str, Any]:
        """查询在售商品列表"""
        offset = (page - 1) * page_size
        
        conditions = ["status = 'on_sale'", "deleted = 0", "stock > 0"]
        params = []
        
        if ec_id:
            conditions.append("ec_id = %s")
            params.append(ec_id)
        
        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)
        
        if category_id:
            conditions.append("category_id = %s")
            params.append(category_id)
        
        if keyword:
            conditions.append("(product_name LIKE %s OR description LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where_clause}"
        count_result = self.db.get_one(count_sql, params.copy())
        total = count_result.get('cnt', 0) if count_result else 0
        
        # 查询数据
        data_sql = f"""
            SELECT id, fid, product_name, product_code, category_id,
                   price, original_price, stock, status, images,
                   shop_id, ec_id, project_id, view_count, favorite_count,
                   created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        items = self.db.get_all(data_sql, params + [page_size, offset]) or []
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }
    
    def find_detail_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """查询商品详情"""
        sql = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE id = %s AND deleted = 0
            LIMIT 1
        """
        return self.db.get_one(sql, [product_id])
    
    def find_by_ids(self, product_ids: List[int]) -> List[Dict[str, Any]]:
        """根据 ID 列表查询商品"""
        if not product_ids:
            return []
        
        placeholders = ', '.join(['%s'] * len(product_ids))
        sql = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE id IN ({placeholders}) AND deleted = 0
        """
        return self.db.get_all(sql, product_ids) or []
    
    # ============ 库存操作 ============
    
    def decrease_stock(self, product_id: int, quantity: int) -> bool:
        """减少库存，返回是否成功"""
        sql = f"""
            UPDATE {self.TABLE_NAME}
            SET stock = stock - %s, sold_count = sold_count + %s, updated_at = NOW()
            WHERE id = %s AND stock >= %s AND deleted = 0
        """
        affected = self.db.execute(sql, [quantity, quantity, product_id, quantity])
        return affected > 0
    
    def increase_stock(self, product_id: int, quantity: int) -> int:
        """增加库存，返回影响行数"""
        sql = f"""
            UPDATE {self.TABLE_NAME}
            SET stock = stock + %s, sold_count = GREATEST(sold_count - %s, 0), updated_at = NOW()
            WHERE id = %s AND deleted = 0
        """
        return self.db.execute(sql, [quantity, quantity, product_id])
    
    def update_view_count(self, product_id: int) -> int:
        """增加浏览量"""
        sql = f"""
            UPDATE {self.TABLE_NAME}
            SET view_count = view_count + 1
            WHERE id = %s AND deleted = 0
        """
        return self.db.execute(sql, [product_id])
    
    def update_favorite_count(self, product_id: int, delta: int) -> int:
        """更新收藏数"""
        sql = f"""
            UPDATE {self.TABLE_NAME}
            SET favorite_count = GREATEST(favorite_count + %s, 0)
            WHERE id = %s AND deleted = 0
        """
        return self.db.execute(sql, [delta, product_id])
    
    # ============ 管理后台查询 ============
    
    def find_all_with_filters(self,
                              ec_id: str = None,
                              project_id: str = None,
                              status: str = None,
                              category_id: int = None,
                              category_name: str = None,
                              shop_id: int = None,
                              keyword: str = None,
                              page: int = 1,
                              page_size: int = 20) -> Dict[str, Any]:
        """管理后台查询商品列表"""
        offset = (page - 1) * page_size
        
        conditions = ["deleted = 0"]
        params = []
        
        if ec_id:
            conditions.append("ec_id = %s")
            params.append(ec_id)
        
        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        if category_id:
            conditions.append("category_id = %s")
            params.append(category_id)
        
        if category_name:
            conditions.append("category_name = %s")
            params.append(category_name)
        
        if shop_id:
            conditions.append("shop_id = %s")
            params.append(shop_id)
        
        if keyword:
            conditions.append("(product_name LIKE %s OR product_code LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where_clause}"
        count_result = self.db.get_one(count_sql, params.copy())
        total = count_result.get('cnt', 0) if count_result else 0
        
        # 查询数据
        data_sql = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        items = self.db.get_all(data_sql, params + [page_size, offset]) or []
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }
    
    def get_stock_alert_list(self, 
                             ec_id: str = None,
                             min_stock: int = 10) -> List[Dict[str, Any]]:
        """获取库存预警列表"""
        conditions = ["stock <= %s", "deleted = 0", "status = 'on_sale'"]
        params = [min_stock]
        
        if ec_id:
            conditions.append("ec_id = %s")
            params.append(ec_id)
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
            SELECT id, product_name, stock, sold_count, ec_id
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
            ORDER BY stock ASC
            LIMIT 100
        """
        return self.db.get_all(sql, params) or []
    
    # ============ 管理后台 CRUD ============
    
    def insert(self, data: Dict[str, Any]) -> int:
        """新增商品，返回新记录ID"""
        import uuid
        fid = data.get('fid') or str(uuid.uuid4())
        sql = f"""
            INSERT INTO {self.TABLE_NAME}
            (fid, product_name, product_code, price, original_price, stock,
             status, images, shop_id, category_id, category_name, description,
             ec_id, project_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        params = [
            fid,
            data.get('product_name', ''),
            data.get('product_code', ''),
            data.get('price', 0),
            data.get('original_price', 0),
            data.get('stock', 0),
            data.get('status', 'active'),
            data.get('images', ''),
            data.get('shop_id'),
            data.get('category_id'),
            data.get('category_name', ''),
            data.get('description', ''),
            data.get('ec_id'),
            data.get('project_id')
        ]
        self.db.execute(sql, params)
        # 获取最后插入的ID
        result = self.db.get_one("SELECT LAST_INSERT_ID() as id")
        return result['id'] if result else 0
    
    def update(self, product_id: int, data: Dict[str, Any]) -> int:
        """更新商品，返回影响行数"""
        fields = []
        params = []
        for field in ['product_name', 'product_code', 'price', 'original_price',
                     'stock', 'status', 'images', 'shop_id', 'category_id',
                     'category_name', 'description']:
            if field in data:
                fields.append(f"{field} = %s")
                params.append(data[field])
        if not fields:
            return 0
        fields.append("updated_at = NOW()")
        params.append(product_id)
        sql = f"UPDATE {self.TABLE_NAME} SET {', '.join(fields)} WHERE id = %s AND deleted = 0"
        return self.db.execute(sql, params)
    
    def soft_delete(self, product_id: int) -> int:
        """软删除商品"""
        sql = f"UPDATE {self.TABLE_NAME} SET deleted = 1, updated_at = NOW() WHERE id = %s AND deleted = 0"
        return self.db.execute(sql, [product_id])
    
    def find_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """根据ID查询商品（管理后台用）"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE id = %s AND deleted = 0 LIMIT 1"
        return self.db.get_one(sql, [product_id])
    
    def get_distinct_categories(self) -> List[str]:
        """获取所有不重复的商品分类"""
        sql = f"SELECT DISTINCT category_name FROM {self.TABLE_NAME} WHERE deleted = 0 AND category_name IS NOT NULL AND category_name != '' ORDER BY category_name"
        rows = self.db.get_all(sql) or []
        return [row['category_name'] for row in rows if row.get('category_name')]
