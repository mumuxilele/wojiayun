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
                        category_name: str = None,
                        shop_id: int = None,
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
                category_name=category_name,
                shop_id=shop_id,
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
    
    # ============ 管理后台 CRUD ============
    
    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """新增商品"""
        try:
            if not data.get('product_name'):
                return self.error('请输入商品名称')
            if not data.get('shop_id'):
                return self.error('请选择所属门店')
            
            product_id = self.product_repo.insert(data)
            if product_id:
                return self.success({'id': product_id}, '新增成功')
            return self.error('新增失败')
        except Exception as e:
            self.logger.error(f"新增商品失败: {e}")
            return self.error('新增失败')
    
    def update_product(self, product_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新商品"""
        try:
            affected = self.product_repo.update(product_id, data)
            if affected > 0:
                return self.success(msg='更新成功')
            return self.error('更新失败，商品可能不存在')
        except Exception as e:
            self.logger.error(f"更新商品失败: {e}")
            return self.error('更新失败')
    
    def delete_product(self, product_id: int) -> Dict[str, Any]:
        """删除商品（软删除）"""
        try:
            affected = self.product_repo.soft_delete(product_id)
            if affected > 0:
                return self.success(msg='删除成功')
            return self.error('删除失败，商品可能不存在')
        except Exception as e:
            self.logger.error(f"删除商品失败: {e}")
            return self.error('删除失败')
    
    def get_product_categories(self) -> Dict[str, Any]:
        """获取所有商品分类"""
        try:
            items = self.product_repo.get_distinct_categories()
            return self.success(items)
        except Exception as e:
            self.logger.error(f"获取商品分类失败: {e}")
            return self.error('获取失败')
    
    def toggle_product_status(self, product_id: int, status: str) -> Dict[str, Any]:
        """切换商品状态（上架/下架）"""
        try:
            if status not in ['active', 'inactive']:
                return self.error('状态值无效')
            affected = self.product_repo.update(product_id, {'status': status})
            if affected > 0:
                return self.success(msg='状态更新成功')
            return self.error('更新失败，商品可能不存在')
        except Exception as e:
            self.logger.error(f"切换商品状态失败: {e}")
            return self.error('更新失败')
    
    def get_product_by_id(self, product_id: int) -> Dict[str, Any]:
        """获取商品详情（管理后台用）"""
        try:
            data = self.product_repo.find_by_id(product_id)
            if not data:
                return self.error('商品不存在')
            return self.success(data)
    
    def import_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量导入商品"""
        try:
            success_count = 0
            fail_count = 0
            errors = []
            
            for idx, item in enumerate(products):
                if not item.get('product_name'):
                    fail_count += 1
                    errors.append(f"第{idx+1}行：商品名称不能为空")
                    continue
                if not item.get('shop_id'):
                    fail_count += 1
                    errors.append(f"第{idx+1}行：请选择所属门店")
                    continue
                
                try:
                    self.product_repo.insert(item)
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    errors.append(f"第{idx+1}行：导入失败 - {str(e)}")
            
            return self.success({
                'success_count': success_count,
                'fail_count': fail_count,
                'errors': errors[:10]  # 只返回前10条错误
            }, f'导入完成：成功{success_count}条，失败{fail_count}条')
        except Exception as e:
            self.logger.error(f"批量导入商品失败: {e}")
            return self.error('导入失败')
        except Exception as e:
            self.logger.error(f"查询商品详情失败: {e}")
            return self.error('查询失败')
