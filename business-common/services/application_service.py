"""
Application Service
申请单业务逻辑层
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_service import BaseService
from ..models.application import Application
from ..repositories.application_repository import ApplicationRepository
from ..repositories.user_repository import UserRepository
from ..fid_utils import generate_business_fid

logger = logging.getLogger(__name__)


class ApplicationService(BaseService):
    """申请单服务"""
    
    SERVICE_NAME = 'ApplicationService'
    
    def __init__(self):
        super().__init__()
        self.app_repo = ApplicationRepository()
        self.user_repo = UserRepository()
    
    # ============ 创建申请 ============
    
    def create_application(self,
                         user_id: str,
                         user_name: str,
                         type_code: str,
                         title: str,
                         form_data: Dict = None,
                         ec_id: str = None,
                         project_id: str = None,
                         attachments: List = None,
                         remark: str = None) -> Dict[str, Any]:
        """
        创建申请单
        
        Args:
            user_id: 用户ID
            user_name: 用户姓名
            type_code: 申请类型代码
            title: 申请标题
            form_data: 表单数据
            ec_id: 企业ID
            project_id: 项目ID
            attachments: 附件列表
            remark: 备注
            
        Returns:
            {'success': True/False, 'msg': '...', 'data': {...}}
        """
        try:
            # 参数校验
            if not type_code:
                return self.error('请选择申请类型')
            if not title or not title.strip():
                return self.error('请输入申请标题')
            if len(title) > 100:
                return self.error('标题不能超过100个字符')
            
            # 生成 FID 和申请编号
            fid = generate_business_fid('app')
            today = datetime.now().strftime('%Y%m%d')
            
            # 查询当日序号
            count = self.app_repo.count_by_user_and_status(user_id)
            application_no = f"APP{today}{count + 1:05d}"
            
            # 构建数据
            data = {
                'fid': fid,
                'application_no': application_no,
                'type_code': type_code,
                'title': title.strip(),
                'user_id': user_id,
                'user_name': user_name,
                'ec_id': ec_id,
                'project_id': project_id,
                'status': Application.STATUS_PENDING,
                'priority': 0,
            }
            
            if form_data:
                import json
                data['form_data'] = json.dumps(form_data, ensure_ascii=False)
            
            if attachments:
                import json
                data['attachments'] = json.dumps(attachments, ensure_ascii=False)
            
            if remark:
                data['remark'] = remark.strip()
            
            # 插入数据库
            app_id = self.app_repo.insert(data)
            
            if not app_id:
                return self.error('创建申请失败')
            
            self.logger.info(f"创建申请成功: id={app_id}, user_id={user_id}")
            
            return self.success({
                'id': app_id,
                'fid': fid,
                'application_no': application_no,
                'status': Application.STATUS_PENDING
            }, '申请提交成功')
            
        except Exception as e:
            self.logger.error(f"创建申请失败: {e}")
            return self.error(f'提交失败: {str(e)}')
    
    # ============ 查询申请 ============
    
    def get_user_applications(self,
                            user_id: str,
                            status: str = None,
                            type_code: str = None,
                            page: int = 1,
                            page_size: int = 20) -> Dict[str, Any]:
        """获取用户的申请列表"""
        try:
            result = self.app_repo.find_by_user(
                user_id=user_id,
                status=status,
                type_code=type_code,
                page=page,
                page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error(f"查询申请列表失败: {e}")
            return self.error('查询失败')
    
    def get_application_detail(self,
                              app_id: int,
                              user_id: str = None) -> Dict[str, Any]:
        """获取申请详情"""
        try:
            data = self.app_repo.find_detail_by_id(app_id, user_id)
            
            if not data:
                return self.error('申请不存在')
            
            # 转换为 Application 对象再转回字典（用于格式化和默认值处理）
            app = Application.from_dict(data)
            return self.success(app.to_dict() if app else data)
            
        except Exception as e:
            self.logger.error(f"查询申请详情失败: {e}")
            return self.error('查询失败')
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户申请统计"""
        try:
            stats = self.app_repo.get_user_stats(user_id)
            return self.success(stats)
        except Exception as e:
            self.logger.error(f"获取用户统计失败: {e}")
            return self.error('获取统计失败')
    
    # ============ 操作申请 ============
    
    def cancel_application(self, 
                          app_id: int,
                          user_id: str) -> Dict[str, Any]:
        """取消申请"""
        try:
            # 先查询申请是否存在且属于该用户
            app_data = self.app_repo.find_detail_by_id(app_id, user_id)
            
            if not app_data:
                return self.error('申请不存在')
            
            app = Application.from_dict(app_data)
            
            if not app.can_cancel:
                return self.error('该申请状态不允许取消')
            
            # 执行取消
            success = self.app_repo.cancel(app_id, user_id)
            
            if success:
                self.logger.info(f"取消申请成功: id={app_id}, user_id={user_id}")
                return self.success(msg='申请已取消')
            else:
                return self.error('取消失败')
                
        except Exception as e:
            self.logger.error(f"取消申请失败: {e}")
            return self.error(f'取消失败: {str(e)}')
    
    # ============ 管理后台功能 ============
    
    def get_all_applications(self,
                           ec_id: str = None,
                           project_id: str = None,
                           status: str = None,
                           type_code: str = None,
                           keyword: str = None,
                           page: int = 1,
                           page_size: int = 20) -> Dict[str, Any]:
        """管理后台查询所有申请"""
        try:
            result = self.app_repo.find_all_with_filters(
                ec_id=ec_id,
                project_id=project_id,
                status=status,
                type_code=type_code,
                keyword=keyword,
                page=page,
                page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error(f"管理后台查询申请失败: {e}")
            return self.error('查询失败')
    
    def update_status(self,
                     app_id: int,
                     status: str,
                     approver_id: int = None,
                     approver_name: str = None,
                     remark: str = None) -> Dict[str, Any]:
        """更新申请状态（审批用）"""
        try:
            affected = self.app_repo.update_status(
                app_id=app_id,
                status=status,
                approver_id=approver_id,
                approver_name=approver_name,
                remark=remark
            )
            
            if affected > 0:
                self.logger.info(f"更新申请状态成功: id={app_id}, status={status}")
                return self.success(msg='状态更新成功')
            else:
                return self.error('更新失败')
                
        except Exception as e:
            self.logger.error(f"更新申请状态失败: {e}")
            return self.error(f'更新失败: {str(e)}')
