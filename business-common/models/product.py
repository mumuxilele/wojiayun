"""
Product 实体
对应表: business_products
"""
from typing import Optional, List, Dict, Any
import json
from .base_model import BaseModel


class Product(BaseModel):
    """商品实体"""
    
    TABLE_NAME = 'business_products'
    PRIMARY_KEY = 'id'
    
    # 状态常量
    STATUS_ON_SALE = 'on_sale'      # 在售
    STATUS_OFF_SALE = 'off_sale'    # 下架
    STATUS_SOLD_OUT = 'sold_out'    # 售罄
    
    def __init__(self, **kwargs):
        # 主键
        self.id: int = kwargs.get('id', 0)
        self.fid: Optional[str] = kwargs.get('fid')
        
        # 商品信息
        self.product_name: str = kwargs.get('product_name', '')
        self.product_code: Optional[str] = kwargs.get('product_code')
        
        # 分类
        self.category_id: Optional[int] = kwargs.get('category_id')
        self.category_name: Optional[str] = kwargs.get('category_name')
        
        # 店铺
        self.shop_id: Optional[int] = kwargs.get('shop_id')
        self.shop_name: Optional[str] = kwargs.get('shop_name')
        
        # 价格
        self.price: float = float(kwargs.get('price', 0))
        self.original_price: float = float(kwargs.get('original_price', 0))
        self.cost_price: Optional[float] = kwargs.get('cost_price')
        
        # 库存
        self.stock: int = int(kwargs.get('stock', 0))
        self.sold_count: int = int(kwargs.get('sold_count', 0))
        
        # 状态
        self.status: str = kwargs.get('status', self.STATUS_ON_SALE)
        
        # 图片
        self.images: Optional[List] = kwargs.get('images')
        if isinstance(self.images, str):
            try:
                self.images = json.loads(self.images)
            except:
                self.images = []
        self.main_image: Optional[str] = kwargs.get('main_image')
        
        # 描述
        self.description: Optional[str] = kwargs.get('description')
        self.detail: Optional[str] = kwargs.get('detail')
        
        # 企业信息
        self.ec_id: Optional[str] = kwargs.get('ec_id')
        self.project_id: Optional[str] = kwargs.get('project_id')
        
        # 计数
        self.view_count: int = int(kwargs.get('view_count', 0))
        self.favorite_count: int = int(kwargs.get('favorite_count', 0))
        
        # 软删除
        self.deleted: int = kwargs.get('deleted', 0)
        
        # 时间戳
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        
        super().__init__(**kwargs)
    
    @property
    def status_text(self) -> str:
        """状态中文描述"""
        status_map = {
            self.STATUS_ON_SALE: '在售',
            self.STATUS_OFF_SALE: '已下架',
            self.STATUS_SOLD_OUT: '已售罄'
        }
        return status_map.get(self.status, '未知')
    
    @property
    def is_on_sale(self) -> bool:
        """是否在售"""
        return self.status == self.STATUS_ON_SALE and self.deleted == 0 and self.stock > 0
    
    @property
    def discount_rate(self) -> float:
        """折扣率"""
        if self.original_price > 0:
            return round(self.price / self.original_price, 2)
        return 1.0
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'fid': self.fid,
            'product_name': self.product_name,
            'product_code': self.product_code,
            'category_id': self.category_id,
            'category_name': self.category_name,
            'shop_id': self.shop_id,
            'shop_name': self.shop_name,
            'price': self.price,
            'original_price': self.original_price,
            'cost_price': self.cost_price,
            'stock': self.stock,
            'sold_count': self.sold_count,
            'status': self.status,
            'status_text': self.status_text,
            'is_on_sale': self.is_on_sale,
            'images': self.images,
            'main_image': self.main_image,
            'description': self.description,
            'detail': self.detail,
            'ec_id': self.ec_id,
            'project_id': self.project_id,
            'view_count': self.view_count,
            'favorite_count': self.favorite_count,
            'discount_rate': self.discount_rate,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None
        }
