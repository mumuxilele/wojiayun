"""
ProductCategory Service
商品分类业务逻辑层
"""
import logging
from typing import Dict, Any, List

from .base_service import BaseService
from ..models.category import ProductCategory
from ..repositories.product_category_repository import ProductCategoryRepository

logger = logging.getLogger(__name__)


class ProductCategoryService(BaseService):
    """商品分类服务"""
    
    SERVICE_NAME = 'ProductCategoryService'
    
    def __init__(self):
        super().__init__()
        self.category_repo = ProductCategoryRepository()
    
    # ============ 查询 ============
    
    def get_category_list(self, level: int = None, parent_id: int = None) -> Dict[str, Any]:
        """获取分类列表"""
        try:
            if parent_id is not None:
                items = self.category_repo.find_by_parent(parent_id)
            elif level is not None:
                items = self.category_repo.find_by_level(level)
            else:
                items = self.category_repo.find_all()
            return self.success({'items': items})
        except Exception as e:
            self.logger.error(f"查询分类列表失败: {e}")
            return self.error('查询失败')
    
    def get_category_tree(self) -> Dict[str, Any]:
        """获取分类树（带层级关系）"""
        try:
            tree = self.category_repo.get_tree(status=1)
            return self.success(tree)
        except Exception as e:
            self.logger.error(f"查询分类树失败: {e}")
            return self.error('查询失败')
    
    def get_category_by_id(self, category_id: int) -> Dict[str, Any]:
        """获取分类详情"""
        try:
            data = self.category_repo.find_by_id(category_id)
            if not data:
                return self.error('分类不存在')
            return self.success(data)
        except Exception as e:
            self.logger.error(f"查询分类详情失败: {e}")
            return self.error('查询失败')
    
    # ============ 新增 ============
    
    def create_category(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """新增分类"""
        try:
            name = data.get('name', '').strip()
            if not name:
                return self.error('请输入分类名称')
            
            # 确定层级
            parent_id = data.get('parent_id', 0)
            if parent_id:
                parent = self.category_repo.find_by_id(parent_id)
                if not parent:
                    return self.error('父级分类不存在')
                level = parent['level'] + 1
                if level > 3:
                    return self.error('最多支持三级分类')
            else:
                level = 1
            
            category_id = self.category_repo.insert({
                'name': name,
                'parent_id': parent_id,
                'level': level,
                'sort_order': data.get('sort_order', 0),
                'icon': data.get('icon'),
                'status': data.get('status', 1)
            })
            
            if category_id:
                return self.success({'id': category_id}, '新增成功')
            return self.error('新增失败')
        except Exception as e:
            self.logger.error(f"新增分类失败: {e}")
            return self.error('新增失败')
    
    # ============ 修改 ============
    
    def update_category(self, category_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新分类"""
        try:
            name = data.get('name', '').strip()
            if not name:
                return self.error('请输入分类名称')
            
            # 检查分类是否存在
            existing = self.category_repo.find_by_id(category_id)
            if not existing:
                return self.error('分类不存在')
            
            # 如果修改了父级，需要重新计算层级
            if 'parent_id' in data:
                parent_id = data['parent_id']
                if parent_id == category_id:
                    return self.error('不能将自己设为父级')
                
                if parent_id:
                    parent = self.category_repo.find_by_id(parent_id)
                    if not parent:
                        return self.error('父级分类不存在')
                    level = parent['level'] + 1
                    if level > 3:
                        return self.error('最多支持三级分类')
                    data['level'] = level
                else:
                    data['level'] = 1
            
            affected = self.category_repo.update(category_id, data)
            if affected > 0:
                return self.success(msg='更新成功')
            return self.error('更新失败')
        except Exception as e:
            self.logger.error(f"更新分类失败: {e}")
            return self.error('更新失败')
    
    # ============ 删除 ============
    
    def delete_category(self, category_id: int) -> Dict[str, Any]:
        """删除分类"""
        try:
            # 检查是否有子分类
            if self.category_repo.has_children(category_id):
                return self.error('该分类下有子分类，无法删除')
            
            # 检查是否有商品
            if self.category_repo.has_products(category_id):
                return self.error('该分类下有商品，无法删除')
            
            affected = self.category_repo.soft_delete(category_id)
            if affected > 0:
                return self.success(msg='删除成功')
            return self.error('删除失败，分类可能不存在')
        except Exception as e:
            self.logger.error(f"删除分类失败: {e}")
            return self.error('删除失败')
    
    # ============ 状态切换 ============
    
    def toggle_status(self, category_id: int, status: int) -> Dict[str, Any]:
        """切换分类状态"""
        try:
            if status not in [0, 1]:
                return self.error('状态值无效')
            affected = self.category_repo.update(category_id, {'status': status})
            if affected > 0:
                return self.success(msg='状态更新成功')
            return self.error('更新失败')
        except Exception as e:
            self.logger.error(f"切换分类状态失败: {e}")
            return self.error('更新失败')
    
    # ============ 管理后台接口 ============
    
    def get_all_categories(self) -> Dict[str, Any]:
        """管理后台获取所有分类（带层级信息）"""
        try:
            items = self.category_repo.find_all()
            
            # 构建ID到名称的映射
            id_to_name = {item['id']: item['name'] for item in items}
            
            # 添加父级名称
            for item in items:
                if item['parent_id'] and item['parent_id'] in id_to_name:
                    item['parent_name'] = id_to_name[item['parent_id']]
                else:
                    item['parent_name'] = None
            
            return self.success({'items': items})
        except Exception as e:
            self.logger.error(f"查询分类列表失败: {e}")
            return self.error('查询失败')
