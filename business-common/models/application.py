"""
Application 实体
对应表: business_applications
"""
from typing import Optional, List, Dict, Any
import json
from .base_model import BaseModel


class Application(BaseModel):
    """申请单实体"""
    
    TABLE_NAME = 'business_applications'
    PRIMARY_KEY = 'id'
    
    # 状态常量
    STATUS_PENDING = 'pending'      # 待处理
    STATUS_PROCESSING = 'processing' # 处理中
    STATUS_COMPLETED = 'completed'   # 已完成
    STATUS_CANCELLED = 'cancelled'   # 已取消
    STATUS_REJECTED = 'rejected'     # 已拒绝
    
    def __init__(self, **kwargs):
        # 主键
        self.id: int = kwargs.get('id', 0)
        self.fid: Optional[str] = kwargs.get('fid')  # V47.0: FID主键
        
        # 申请编号
        self.application_no: Optional[str] = kwargs.get('application_no')
        self.app_no: Optional[str] = kwargs.get('app_no')  # 兼容旧字段
        
        # 申请类型
        self.type_code: str = kwargs.get('type_code', '')
        self.app_type: str = kwargs.get('app_type', '')  # 兼容旧字段
        
        # 标题内容
        self.title: str = kwargs.get('title', '')
        self.content: Optional[str] = kwargs.get('content')
        
        # 表单数据 (JSON)
        self.form_data: Optional[Dict] = kwargs.get('form_data')
        if isinstance(self.form_data, str):
            try:
                self.form_data = json.loads(self.form_data)
            except:
                self.form_data = {}
        
        # 申请人信息
        self.user_id: str = kwargs.get('user_id', '')
        self.user_name: str = kwargs.get('user_name', '')
        self.user_phone: Optional[str] = kwargs.get('user_phone')
        
        # 企业信息
        self.ec_id: Optional[str] = kwargs.get('ec_id')
        self.project_id: Optional[str] = kwargs.get('project_id')
        
        # 状态
        self.status: str = kwargs.get('status', self.STATUS_PENDING)
        self.priority: int = kwargs.get('priority', 0)  # 优先级 0-3
        
        # 审批信息
        self.approver_id: Optional[int] = kwargs.get('approver_id')
        self.approver_name: Optional[str] = kwargs.get('approver_name')
        self.approve_remark: Optional[str] = kwargs.get('approve_remark')
        
        # 附件
        self.attachments: Optional[List] = kwargs.get('attachments')
        if isinstance(self.attachments, str):
            try:
                self.attachments = json.loads(self.attachments)
            except:
                self.attachments = []
        
        # 图片 (旧字段兼容)
        self.images: Optional[str] = kwargs.get('images')
        
        # 备注
        self.remark: Optional[str] = kwargs.get('remark')
        
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
            self.STATUS_PENDING: '待处理',
            self.STATUS_PROCESSING: '处理中',
            self.STATUS_COMPLETED: '已完成',
            self.STATUS_CANCELLED: '已取消',
            self.STATUS_REJECTED: '已拒绝'
        }
        return status_map.get(self.status, '未知')
    
    @property
    def images_list(self) -> List[str]:
        """解析图片列表"""
        if self.attachments:
            return self.attachments
        if self.images:
            try:
                return json.loads(self.images)
            except:
                return []
        return []
    
    @property
    def can_cancel(self) -> bool:
        """是否可以取消"""
        return self.status == self.STATUS_PENDING and self.deleted == 0
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'fid': self.fid,
            'application_no': self.application_no or self.app_no,
            'type_code': self.type_code or self.app_type,
            'title': self.title,
            'content': self.content,
            'form_data': self.form_data,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_phone': self.user_phone,
            'ec_id': self.ec_id,
            'project_id': self.project_id,
            'status': self.status,
            'status_text': self.status_text,
            'priority': self.priority,
            'approver_id': self.approver_id,
            'approver_name': self.approver_name,
            'images_list': self.images_list,
            'remark': self.remark,
            'can_cancel': self.can_cancel,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None
        }
