"""
User Service
用户业务逻辑层
"""
import logging
from typing import Dict, Any, Optional

from .base_service import BaseService
from ..models.user import User
from ..repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """用户服务"""
    
    SERVICE_NAME = 'UserService'
    
    def __init__(self):
        super().__init__()
        self.user_repo = UserRepository()
    
    # ============ 查询用户 ============
    
    def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """根据 user_id 查询用户"""
        try:
            data = self.user_repo.find_by_user_id(user_id)
            
            if not data:
                return self.error('用户不存在')
            
            # 转换为 User 对象
            user = User.from_dict(data)
            return self.success(user.to_dict() if user else data)
            
        except Exception as e:
            self.logger.error(f"查询用户失败: {e}")
            return self.error('查询失败')
    
    def get_user_by_phone(self, phone: str) -> Dict[str, Any]:
        """根据手机号查询用户"""
        try:
            data = self.user_repo.find_by_phone(phone)
            
            if not data:
                return self.error('用户不存在')
            
            user = User.from_dict(data)
            return self.success(user.to_dict() if user else data)
            
        except Exception as e:
            self.logger.error(f"查询用户失败: {e}")
            return self.error('查询失败')
    
    def get_user_list(self,
                     ec_id: str,
                     project_id: str = None,
                     page: int = 1,
                     page_size: int = 20) -> Dict[str, Any]:
        """获取用户列表"""
        try:
            result = self.user_repo.find_by_ec(
                ec_id=ec_id,
                project_id=project_id,
                page=page,
                page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error(f"查询用户列表失败: {e}")
            return self.error('查询失败')
    
    # ============ 统计 ============
    
    def get_user_count(self,
                      ec_id: str,
                      project_id: str = None) -> Dict[str, Any]:
        """获取用户数量统计"""
        try:
            count = self.user_repo.count_by_ec(ec_id, project_id)
            return self.success({'count': count})
        except Exception as e:
            self.logger.error(f"获取用户统计失败: {e}")
            return self.error('获取统计失败')
    
    # ============ 更新操作 ============
    
    def update_user_status(self,
                          user_id: int,
                          status: int) -> Dict[str, Any]:
        """更新用户状态"""
        try:
            if status not in [0, 1]:
                return self.error('状态值无效')
            
            affected = self.user_repo.update_status(user_id, status)
            
            if affected > 0:
                return self.success(msg='状态更新成功')
            else:
                return self.error('更新失败')
                
        except Exception as e:
            self.logger.error(f"更新用户状态失败: {e}")
            return self.error(f'更新失败: {str(e)}')
