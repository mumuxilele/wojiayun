"""
Model 基类
提供统一的实体属性和方法
"""
from typing import Dict, Any, Optional
from datetime import datetime


class BaseModel:
    """所有实体的基类"""
    
    # 表名，子类必须覆盖
    TABLE_NAME: str = ''
    
    # 主键字段名
    PRIMARY_KEY: str = 'id'
    
    # 数据库字段到模型属性的映射
    FIELD_MAP: Dict[str, str] = {}
    
    def __init__(self, **kwargs):
        """从字典初始化实体"""
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['BaseModel']:
        """从数据库字典创建实体"""
        if not data:
            return None
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items() 
            if not k.startswith('_')
        }
    
    def __repr__(self):
        """字符串表示"""
        pk_value = getattr(self, self.PRIMARY_KEY, None)
        return f"<{self.__class__.__name__} {self.PRIMARY_KEY}={pk_value}>"
