"""
User 实体
对应表: business_users
"""
from typing import Optional
from .base_model import BaseModel


class User(BaseModel):
    """用户实体"""
    
    TABLE_NAME = 'business_users'
    PRIMARY_KEY = 'id'
    
    def __init__(self, **kwargs):
        # 主键
        self.id: int = kwargs.get('id', 0)
        self.fid: Optional[str] = kwargs.get('fid')  # V47.0: FID主键
        
        # 基本信息
        self.user_id: str = kwargs.get('user_id', '')  # 外部用户ID
        self.user_name: str = kwargs.get('user_name', '')
        self.phone: str = kwargs.get('phone', '')
        self.avatar: Optional[str] = kwargs.get('avatar')
        
        # 企业信息
        self.ec_id: Optional[str] = kwargs.get('ec_id')
        self.project_id: Optional[str] = kwargs.get('project_id')
        
        # 状态
        self.status: int = kwargs.get('status', 1)  # 1-正常, 0-禁用
        self.deleted: int = kwargs.get('deleted', 0)  # 0-正常, 1-已删除
        
        # 时间戳
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        
        super().__init__(**kwargs)
    
    @property
    def is_active(self) -> bool:
        """是否活跃用户"""
        return self.status == 1 and self.deleted == 0
    
    def to_dict(self):
        """转换为字典，用于 API 响应"""
        return {
            'id': self.id,
            'fid': self.fid,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'phone': self.phone,
            'avatar': self.avatar,
            'ec_id': self.ec_id,
            'project_id': self.project_id,
            'status': self.status,
            'is_active': self.is_active,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None
        }
