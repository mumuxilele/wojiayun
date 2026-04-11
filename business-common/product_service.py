"""
V32.0 商品服务模块 → V43.0安全修复
提供统一的商品业务逻辑封装

功能清单:
- 商品CRUD
- SKU管理
- 库存操作
- 商品分类
- 商品搜索
- 浏览足迹
- 收藏管理
- 智能推荐

V43.0安全修复:
- order_by参数白名单验证（防止SQL注入）

依赖:
- search_service: 搜索服务
- cache_service: 缓存服务
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from . import db
from .service_base import BaseService
from .repository_base import ProductRepository

logger = logging.getLogger(__name__)

# V43.0新增：ORDER BY白名单验证，防止SQL注入
ALLOWED_PRODUCT_ORDER_FIELDS = {
    'created_at', 'updated_at', 'price', 'sales_count', 'stock', 'id',
    'name', 'views', 'favorites_count'
}
ALLOWED_ORDER_DIRS = {'ASC', 'DESC', 'asc', 'desc'}


def _validate_order_by(order_by: str) -> str:
    """
    V43.0安全修复：验证并规范化order_by参数
    防止SQL注入攻击，只允许预定义的安全字段和方向组合
    """
    if not order_by:
        return 'created_at DESC'
    
    # 移除所有SQL关键字和注释
    dangerous_patterns = [
        r'(?i)\b(union|select|insert|update|delete|drop|exec|execute|script)\b',
        r'--', r'/\*', r'\*/', r';', r'@', r'0x',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, order_by):
            logger.warning(f"SQL注入攻击尝试被拦截: {order_by}")
            return 'created_at DESC'
    
    # 解析字段和方向
    parts = [p.strip() for p in order_by.split()]
    field = parts[0] if parts else 'created_at'
    direction = parts[1].upper() if len(parts) > 1 else 'DESC'
    
    # 白名单验证
    if field not in ALLOWED_PRODUCT_ORDER_FIELDS:
        logger.warning(f"order_by字段不在白名单中: {field}, 使用默认值")
        field = 'created_at'
    
    if direction not in ALLOWED_ORDER_DIRS:
        direction = 'DESC'
    
    return f"{field} {direction}"


class ProductService(BaseService):
    """商品服务"""

    SERVICE_NAME = 'ProductService'

    def __init__(self):
        super().__init__()
        self.repo = ProductRepository()

    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_products LIMIT 1")
            base['db_status'] = 'connected'
            base['product_count'] = result.get('cnt', 0) if result else 0
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base

    # ============ 商品管理 ============

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建商品"""
        try:
            sql = """
                INSERT INTO business_products (
                    name, description, price, original_price,
                    category_id, images, video_url,
                    ec_id, project_id, status, stock,
                    sales_count, view_count, weight,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """

            params = [
                data.get('name'),
                data.get('description', ''),
                data.get('price', 0),
                data.get('original_price', data.get('price', 0)),
                data.get('category_id'),
                ','.join(data.get('images', [])) if isinstance(data.get('images'), list) else data.get('images', ''),
                data.get('video_url', ''),
                data.get('ec_id'),
                data.get('project_id'),
                data.get('status', 'active'),
                data.get('stock', 0),
                0, 0,
                data.get('weight', 0),
            ]

            db.execute(sql, params)

            result = db.get_one("SELECT LAST_INSERT_ID() as id")
            product_id = result['id'] if result else 0

            logger.info(f"[ProductService] 创建商品: id={product_id}, name={data.get('name')}")

            return {
                'success': True,
                'product_id': product_id,
                'msg': '商品创建成功'
            }

        except Exception as e:
            logger.error(f"[ProductService] 创建商品失败: {e}")
            return {'success': False, 'msg': str(e)}

    def update_product(self, product_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新商品"""
        try:
            set_clauses = []
            params = []

            for key in ['name', 'description', 'price', 'original_price',
                       'category_id', 'status', 'stock', 'weight']:
                if key in data:
                    if key == 'images' and isinstance(data[key], list):
                        set_clauses.append(f"{key} = %s")
                        params.append(','.join(data[key]))
                    else:
                        set_clauses.append(f"{key} = %s")
                        params.append(data[key])

            if not set_clauses:
                return {'success': False, 'msg': '没有需要更新的字段'}

            set_clauses.append("updated_at = NOW()")
            params.append(product_id)

            sql = f"UPDATE business_products SET {', '.join(set_clauses)} WHERE id = %s"

            affected = db.execute(sql, params)

            if affected == 0:
                return {'success': False, 'msg': '商品不存在'}

            logger.info(f"[ProductService] 更新商品: id={product_id}")

            return {'success': True, 'msg': '商品更新成功'}

        except Exception as e:
            logger.error(f"[ProductService] 更新商品失败: {e}")
            return {'success': False, 'msg': str(e)}

    def delete_product(self, product_id: int) -> Dict[str, Any]:
        """删除商品(软删除)"""
        try:
            sql = """
                UPDATE business_products
                SET deleted = 1, status = 'offline', updated_at = NOW()
                WHERE id = %s
            """
            affected = db.execute(sql, [product_id])

            if affected == 0:
                return {'success': False, 'msg': '商品不存在'}

            return {'success': True, 'msg': '商品删除成功'}

        except Exception as e:
            logger.error(f"[ProductService] 删除商品失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_product(self, product_id: int, ec_id: int = None) -> Optional[Dict]:
        """获取商品详情"""
        sql = "SELECT * FROM business_products WHERE id = %s AND deleted = 0"
        params = [product_id]

        if ec_id:
            sql += " AND ec_id = %s"
            params.append(ec_id)

        product = db.get_one(sql, params)

        if product:
            # 获取SKU列表
            product['skus'] = self.get_product_skus(product_id)

            # 获取分类信息
            if product.get('category_id'):
                category = self.get_category(product['category_id'])
                product['category_name'] = category.get('name') if category else None

            # 增加浏览数
            self.increment_view_count(product_id)

        return product

    def get_products(self, ec_id: int, project_id: int = None,
                    category_id: int = None, keyword: str = None,
                    status: str = 'active', page: int = 1,
                    page_size: int = 20, order_by: str = 'created_at DESC') -> Dict[str, Any]:
        """获取商品列表"""
        # V43.0安全修复：验证order_by参数防止SQL注入
        safe_order_by = _validate_order_by(order_by)
        
        conditions = ["deleted = 0"]
        params = [ec_id]

        conditions.append("ec_id = %s")
        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)
        if category_id:
            conditions.append("category_id = %s")
            params.append(category_id)
        if keyword:
            conditions.append("(name LIKE %s OR description LIKE %s)")
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        if status:
            conditions.append("status = %s")
            params.append(status)

        where = " AND ".join(conditions)

        # 统计
        count_sql = f"SELECT COUNT(*) as total FROM business_products WHERE {where}"
        count_result = db.get_one(count_sql, params)
        total = count_result.get('total', 0) if count_result else 0

        # 分页查询
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT * FROM business_products WHERE {where}
            ORDER BY {safe_order_by}
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        products = db.get_all(query_sql, params) or []

        # 处理图片字段
        for p in products:
            p['images'] = p.get('images', '').split(',') if p.get('images') else []

        return {
            'products': products,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size
        }

    # ============ SKU管理 ============

    def add_sku(self, product_id: int, sku_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加SKU"""
        try:
            sql = """
                INSERT INTO business_product_skus (
                    product_id, sku_code, specs, price, original_price,
                    stock, sales_count, weight, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """

            specs_json = json.dumps(sku_data.get('specs', {})) if isinstance(sku_data.get('specs'), dict) else sku_data.get('specs', '{}')

            params = [
                product_id,
                sku_data.get('sku_code', self._generate_sku_code()),
                specs_json,
                sku_data.get('price', 0),
                sku_data.get('original_price', sku_data.get('price', 0)),
                sku_data.get('stock', 0),
                0,
                sku_data.get('weight', 0),
            ]

            db.execute(sql, params)

            result = db.get_one("SELECT LAST_INSERT_ID() as id")
            sku_id = result['id'] if result else 0

            return {
                'success': True,
                'sku_id': sku_id,
                'msg': 'SKU添加成功'
            }

        except Exception as e:
            logger.error(f"[ProductService] 添加SKU失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_product_skus(self, product_id: int) -> List[Dict]:
        """获取商品的所有SKU"""
        sql = "SELECT * FROM business_product_skus WHERE product_id = %s ORDER BY id"
        skus = db.get_all(sql, [product_id]) or []

        for sku in skus:
            if sku.get('specs') and isinstance(sku['specs'], str):
                import json
                try:
                    sku['specs'] = json.loads(sku['specs'])
                except:
                    sku['specs'] = {}

        return skus

    def update_sku_stock(self, sku_id: int, quantity_change: int) -> Dict[str, Any]:
        """更新SKU库存"""
        try:
            if quantity_change > 0:
                sql = "UPDATE business_product_skus SET stock = stock + %s WHERE id = %s AND stock + %s >= 0"
            else:
                sql = "UPDATE business_product_skus SET stock = stock + %s WHERE id = %s AND stock >= %s"
                quantity_change = abs(quantity_change)

            affected = db.execute(sql, [quantity_change, sku_id, quantity_change])

            if affected == 0:
                return {'success': False, 'msg': '库存不足或SKU不存在'}

            return {'success': True, 'msg': '库存更新成功'}

        except Exception as e:
            logger.error(f"[ProductService] 更新SKU库存失败: {e}")
            return {'success': False, 'msg': str(e)}

    def _generate_sku_code(self) -> str:
        """生成SKU编码"""
        import time
        import random
        return f"SKU{int(time.time())}{random.randint(100, 999)}"

    # ============ 库存操作 ============

    def check_stock(self, product_id: int, sku_id: int = None,
                   quantity: int = 1) -> Dict[str, Any]:
        """检查库存是否充足"""
        if sku_id:
            sql = "SELECT stock FROM business_product_skus WHERE id = %s"
            result = db.get_one(sql, [sku_id])
            stock = result.get('stock', 0) if result else 0
        else:
            sql = "SELECT stock FROM business_products WHERE id = %s"
            result = db.get_one(sql, [product_id])
            stock = result.get('stock', 0) if result else 0

        return {
            'success': True,
            'sufficient': stock >= quantity,
            'stock': stock,
            'required': quantity
        }

    def lock_stock(self, product_id: int, sku_id: int = None,
                  quantity: int = 1) -> Dict[str, Any]:
        """锁定库存"""
        if sku_id:
            sql = "UPDATE business_product_skus SET stock = stock - %s WHERE id = %s AND stock >= %s"
        else:
            sql = "UPDATE business_products SET stock = stock - %s WHERE id = %s AND stock >= %s"

        affected = db.execute(sql, [quantity, sku_id or product_id, quantity])

        if affected == 0:
            return {'success': False, 'msg': '库存不足'}

        return {'success': True, 'msg': '库存锁定成功'}

    def unlock_stock(self, product_id: int, sku_id: int = None,
                    quantity: int = 1) -> Dict[str, Any]:
        """解锁库存"""
        if sku_id:
            sql = "UPDATE business_product_skus SET stock = stock + %s WHERE id = %s"
        else:
            sql = "UPDATE business_products SET stock = stock + %s WHERE id = %s"

        db.execute(sql, [quantity, sku_id or product_id])

        return {'success': True, 'msg': '库存解锁成功'}

    def increment_view_count(self, product_id: int) -> Dict[str, Any]:
        """增加浏览数"""
        try:
            sql = "UPDATE business_products SET view_count = view_count + 1 WHERE id = %s"
            db.execute(sql, [product_id])
            return {'success': True}
        except Exception as e:
            logger.error(f"[ProductService] 增加浏览数失败: {e}")
            return {'success': False, 'msg': str(e)}

    def increment_sales_count(self, product_id: int, sku_id: int = None,
                             quantity: int = 1) -> Dict[str, Any]:
        """增加销量"""
        try:
            if sku_id:
                sql = "UPDATE business_product_skus SET sales_count = sales_count + %s WHERE id = %s"
                db.execute(sql, [quantity, sku_id])

            sql = "UPDATE business_products SET sales_count = sales_count + %s WHERE id = %s"
            db.execute(sql, [quantity, product_id])

            return {'success': True}
        except Exception as e:
            logger.error(f"[ProductService] 增加销量失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ 分类管理 ============

    def get_categories(self, ec_id: int, parent_id: int = None) -> List[Dict]:
        """获取分类列表"""
        if parent_id is None:
            sql = "SELECT * FROM business_product_categories WHERE ec_id = %s ORDER BY sort_order"
            return db.get_all(sql, [ec_id]) or []
        else:
            sql = "SELECT * FROM business_product_categories WHERE ec_id = %s AND parent_id = %s ORDER BY sort_order"
            return db.get_all(sql, [ec_id, parent_id]) or []

    def get_category(self, category_id: int) -> Optional[Dict]:
        """获取分类详情"""
        sql = "SELECT * FROM business_product_categories WHERE id = %s"
        return db.get_one(sql, [category_id])

    def create_category(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建分类"""
        try:
            sql = """
                INSERT INTO business_product_categories (
                    name, parent_id, icon, sort_order, ec_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, NOW())
            """

            params = [
                data.get('name'),
                data.get('parent_id'),
                data.get('icon', ''),
                data.get('sort_order', 0),
                data.get('ec_id'),
            ]

            db.execute(sql, params)
            result = db.get_one("SELECT LAST_INSERT_ID() as id")

            return {
                'success': True,
                'category_id': result['id'] if result else 0,
                'msg': '分类创建成功'
            }

        except Exception as e:
            logger.error(f"[ProductService] 创建分类失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ 收藏管理 ============

    def add_favorite(self, user_id: int, product_id: int,
                   ec_id: int, project_id: int) -> Dict[str, Any]:
        """添加收藏"""
        try:
            # 检查是否已收藏
            check_sql = """
                SELECT * FROM business_favorites
                WHERE user_id = %s AND product_id = %s
            """
            existing = db.get_one(check_sql, [user_id, product_id])

            if existing:
                return {'success': True, 'msg': '已收藏', 'already_favorited': True}

            sql = """
                INSERT INTO business_favorites (user_id, product_id, ec_id, project_id, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            db.execute(sql, [user_id, product_id, ec_id, project_id])

            return {'success': True, 'msg': '收藏成功'}

        except Exception as e:
            logger.error(f"[ProductService] 添加收藏失败: {e}")
            return {'success': False, 'msg': str(e)}

    def remove_favorite(self, user_id: int, product_id: int) -> Dict[str, Any]:
        """取消收藏"""
        try:
            sql = "DELETE FROM business_favorites WHERE user_id = %s AND product_id = %s"
            db.execute(sql, [user_id, product_id])
            return {'success': True, 'msg': '已取消收藏'}
        except Exception as e:
            logger.error(f"[ProductService] 取消收藏失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_favorites(self, user_id: int, page: int = 1,
                     page_size: int = 20) -> Dict[str, Any]:
        """获取收藏列表"""
        count_sql = "SELECT COUNT(*) as total FROM business_favorites WHERE user_id = %s"
        count_result = db.get_one(count_sql, [user_id])
        total = count_result.get('total', 0) if count_result else 0

        offset = (page - 1) * page_size
        sql = """
            SELECT f.*, p.name, p.price, p.images, p.stock
            FROM business_favorites f
            JOIN business_products p ON f.product_id = p.id
            WHERE f.user_id = %s AND p.deleted = 0
            ORDER BY f.created_at DESC
            LIMIT %s OFFSET %s
        """
        favorites = db.get_all(sql, [user_id, page_size, offset]) or []

        for f in favorites:
            f['images'] = f.get('images', '').split(',') if f.get('images') else []

        return {
            'favorites': favorites,
            'total': total,
            'page': page,
            'page_size': page_size
        }

    # ============ 浏览足迹 ============

    def add_view_history(self, user_id: int, product_id: int,
                        ec_id: int, project_id: int) -> Dict[str, Any]:
        """添加浏览足迹"""
        try:
            # 更新或插入浏览记录
            sql = """
                INSERT INTO business_view_history (user_id, product_id, ec_id, project_id, viewed_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE viewed_at = NOW()
            """
            db.execute(sql, [user_id, product_id, ec_id, project_id])

            return {'success': True}

        except Exception as e:
            # 如果表不存在，静默失败
            logger.debug(f"[ProductService] 添加浏览足迹失败(可能表不存在): {e}")
            return {'success': False, 'msg': str(e)}

    def get_view_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """获取浏览足迹"""
        try:
            sql = """
                SELECT vh.*, p.name, p.price, p.images
                FROM business_view_history vh
                JOIN business_products p ON vh.product_id = p.id
                WHERE vh.user_id = %s AND p.deleted = 0
                ORDER BY vh.viewed_at DESC
                LIMIT %s
            """
            history = db.get_all(sql, [user_id, limit]) or []

            for h in history:
                h['images'] = h.get('images', '').split(',') if h.get('images') else []

            return history

        except Exception as e:
            logger.debug(f"[ProductService] 获取浏览足迹失败: {e}")
            return []

    # ============ 智能推荐 ============

    def get_recommendations(self, user_id: int, ec_id: int,
                           limit: int = 10) -> List[Dict]:
        """
        获取商品推荐

        策略:
        1. 基于用户浏览历史的同类商品
        2. 热销商品
        3. 新上架商品
        """
        recommendations = []

        try:
            # 1. 基于浏览历史的推荐
            view_sql = """
                SELECT DISTINCT p.category_id
                FROM business_view_history vh
                JOIN business_products p ON vh.product_id = p.id
                WHERE vh.user_id = %s AND p.deleted = 0 AND p.status = 'active'
                ORDER BY vh.viewed_at DESC
                LIMIT 5
            """
            view_history = db.get_all(view_sql, [user_id]) or []

            if view_history:
                category_ids = [v['category_id'] for v in view_history if v.get('category_id')]
                if category_ids:
                    placeholders = ','.join(['%s'] * len(category_ids))
                    rec_sql = f"""
                        SELECT * FROM business_products
                        WHERE ec_id = %s AND status = 'active' AND deleted = 0
                        AND category_id IN ({placeholders})
                        ORDER BY sales_count DESC, created_at DESC
                        LIMIT %s
                    """
                    recommendations = db.get_all(rec_sql, [ec_id] + category_ids + [limit]) or []

            # 2. 如果推荐不足，补充热销商品
            if len(recommendations) < limit:
                existing_ids = [r['id'] for r in recommendations]
                exclude_clause = f"AND id NOT IN ({','.join(['%s'] * len(existing_ids))})" if existing_ids else ""

                hot_sql = f"""
                    SELECT * FROM business_products
                    WHERE ec_id = %s AND status = 'active' AND deleted = 0
                    {exclude_clause}
                    ORDER BY sales_count DESC
                    LIMIT %s
                """
                params = [ec_id] + existing_ids + [limit - len(recommendations)]
                hot_products = db.get_all(hot_sql, params) or []
                recommendations.extend(hot_products)

        except Exception as e:
            logger.error(f"[ProductService] 获取推荐失败: {e}")
            # 返回默认的热销商品
            sql = """
                SELECT * FROM business_products
                WHERE ec_id = %s AND status = 'active' AND deleted = 0
                ORDER BY sales_count DESC
                LIMIT %s
            """
            recommendations = db.get_all(sql, [ec_id, limit]) or []

        # 处理图片
        for r in recommendations:
            r['images'] = r.get('images', '').split(',') if r.get('images') else []

        return recommendations[:limit]


import json

# 单例实例
product_service = ProductService()
