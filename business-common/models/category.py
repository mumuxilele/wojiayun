"""
ProductCategory 实体
商品分类表，支持三级类目
"""
from typing import Optional, List, Dict, Any
from .base_model import BaseModel


class ProductCategory(BaseModel):
    """商品分类实体"""
    
    TABLE_NAME = 'business_product_categories'
    PRIMARY_KEY = 'id'
    
    # 层级常量
    LEVEL_1 = 1  # 一级分类
    LEVEL_2 = 2  # 二级分类
    LEVEL_3 = 3  # 三级分类
    
    def __init__(self, **kwargs):
        self.id: int = kwargs.get('id', 0)
        self.name: str = kwargs.get('name', '')
        self.parent_id: int = kwargs.get('parent_id', 0)
        self.level: int = kwargs.get('level', 1)
        self.sort_order: int = kwargs.get('sort_order', 0)
        self.icon: Optional[str] = kwargs.get('icon')
        self.status: int = kwargs.get('status', 1)  # 1启用 0禁用
        self.deleted: int = kwargs.get('deleted', 0)
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        
        # 关联数据（非数据库字段）
        self.children: List['ProductCategory'] = []
        self.parent_name: Optional[str] = None
        
        super().__init__(**kwargs)
    
    @property
    def status_text(self) -> str:
        return '启用' if self.status == 1 else '禁用'
    
    @property
    def level_text(self) -> str:
        level_map = {1: '一级', 2: '二级', 3: '三级'}
        return level_map.get(self.level, '未知')
    
    @property
    def is_enabled(self) -> bool:
        return self.status == 1 and self.deleted == 0
    
    def to_dict(self, with_children: bool = False):
        """转换为字典"""
        result = {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'level': self.level,
            'level_text': self.level_text,
            'sort_order': self.sort_order,
            'icon': self.icon,
            'status': self.status,
            'status_text': self.status_text,
            'parent_name': self.parent_name,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None
        }
        if with_children and self.children:
            result['children'] = [c.to_dict(with_children=True) for c in self.children]
        return result
