"""
Product Service
商品业务逻辑层
"""
import logging
from typing import Dict, Any, Optional, List

from .base_service import BaseService
from ..models.product import Product
from ..repositories.product_repository import ProductRepository

logger = logging.getLogger(__name__)


class ProductService(BaseService):
    """商品服务"""
    
    SERVICE_NAME = 'ProductService'
    
    def __init__(self):
        super().__init__()
        self.product_repo = ProductRepository()
    
    # ============ 查询商品 ============
    
    def get_product_list(self,
                        ec_id: str = None,
                        project_id: str = None,
                        category_id: int = None,
                        keyword: str = None,
                        page: int = 1,
                        page_size: int = 20) -> Dict[str, Any]:
        """获取商品列表"""
        try:
            result = self.product_repo.find_on_sale(
                ec_id=ec_id,
                project_id=project_id,
                category_id=category_id,
                keyword=keyword,
                page=page,
                page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error(f"查询商品列表失败: {e}")
            return self.error('查询失败')
    
    def get_product_detail(self, product_id: int) -> Dict[str, Any]:
        """获取商品详情"""
        try:
            data = self.product_repo.find_detail_by_id(product_id)
            
            if not data:
                return self.error('商品不存在')
            
            # 增加浏览量
            self.product_repo.update_view_count(product_id)
            
            # 转换为 Product 对象
            product = Product.from_dict(data)
            return self.success(product.to_dict() if product else data)
            
        except Exception as e:
            self.logger.error(f"查询商品详情失败: {e}")
            return self.error('查询失败')
    
    # ============ 收藏相关 ============
    
    def update_favorite(self,
                       product_id: int,
                       is_favorite: bool) -> Dict[str, Any]:
        """更新商品收藏数"""
        try:
            delta = 1 if is_favorite else -1
            self.product_repo.update_favorite_count(product_id, delta)
            return self.success(msg='操作成功')
        except Exception as e:
            self.logger.error(f"更新收藏数失败: {e}")
            return self.error('操作失败')
    
    # ============ 管理后台功能 ============
    
    def get_all_products(self,
                        ec_id: str = None,
                        project_id: str = None,
                        status: str = None,
                        category_id: int = None,
                        keyword: str = None,
                        page: int = 1,
                        page_size: int = 20) -> Dict[str, Any]:
        """管理后台获取所有商品"""
        try:
            result = self.product_repo.find_all_with_filters(
                ec_id=ec_id,
                project_id=project_id,
                status=status,
                category_id=category_id,
                keyword=keyword,
                page=page,
                page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error(f"管理后台查询商品失败: {e}")
            return self.error('查询失败')
    
    def get_stock_alert(self,
                       ec_id: str = None,
                       min_stock: int = 10) -> Dict[str, Any]:
        """获取库存预警列表"""
        try:
            items = self.product_repo.get_stock_alert_list(ec_id, min_stock)
            return self.success({'items': items})
        except Exception as e:
            self.logger.error(f"获取库存预警失败: {e}")
            return self.error('获取失败')
