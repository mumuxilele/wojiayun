"""
User Service - 用户业务逻辑层
V48.0: MVC架构改造 - Service层
职责：
  - 封装用户相关业务逻辑
  - 协调 Repository 完成数据操作
  - 处理事务、缓存、日志等横切关注点
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from business_common.repositories.user_repository import UserRepository
from business_common.models.user import User

logger = logging.getLogger(__name__)


class UserService:
    """用户服务类"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    # ============ 查询 ============
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        根据 user_id 获取用户
        
        Args:
            user_id: 外部用户ID
            
        Returns:
            User 对象或 None
        """
        data = self.user_repo.find_by_user_id(user_id)
        return User.from_dict(data) if data else None
    
    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """根据手机号获取用户"""
        data = self.user_repo.find_by_phone(phone)
        return User.from_dict(data) if data else None
    
    def get_user_list(self, 
                      ec_id: str,
                      project_id: str = None,
                      page: int = 1,
                      page_size: int = 20) -> Dict[str, Any]:
        """
        获取用户列表（分页）
        
        Returns:
            {
                'items': [User, User, ...],
                'total': 100,
                'page': 1,
                'page_size': 20,
                'pages': 5
            }
        """
        result = self.user_repo.find_by_ec(ec_id, project_id, page, page_size)
        
        # 将字典列表转换为 User 对象列表
        if result.get('items'):
            result['items'] = [User.from_dict(item) for item in result['items']]
        
        return result
    
    def get_user_stats(self, ec_id: str, project_id: str = None) -> Dict[str, int]:
        """
        获取用户统计
        
        Returns:
            {
                'total': 总用户数,
                'active': 活跃用户数,
                'inactive': 禁用用户数
            }
        """
        total = self.user_repo.count_by_ec(ec_id, project_id)
        
        # 可以扩展：查询活跃用户数
        # active = self.user_repo.count_active(ec_id, project_id)
        
        return {
            'total': total,
            'active': total,  # 简化处理，实际需要单独查询
            'inactive': 0
        }
    
    # ============ 业务操作 ============
    
    def create_user(self, 
                    user_id: str,
                    user_name: str,
                    phone: str,
                    ec_id: str,
                    project_id: str = None,
                    avatar: str = None) -> Dict[str, Any]:
        """
        创建新用户
        
        Args:
            user_id: 外部用户ID
            user_name: 用户名
            phone: 手机号
            ec_id: 企业ID
            project_id: 项目ID（可选）
            avatar: 头像URL（可选）
            
        Returns:
            {'success': True, 'user': User, 'msg': '创建成功'}
            或 {'success': False, 'msg': '错误信息'}
        """
        try:
            # 1. 检查用户是否已存在
            existing = self.get_user_by_id(user_id)
            if existing:
                return {'success': False, 'msg': '用户已存在'}
            
            # 2. 检查手机号是否已被使用
            if phone:
                existing_phone = self.get_user_by_phone(phone)
                if existing_phone:
                    return {'success': False, 'msg': '手机号已被使用'}
            
            # 3. 准备数据
            user_data = {
                'user_id': user_id,
                'user_name': user_name,
                'phone': phone,
                'ec_id': ec_id,
                'project_id': project_id,
                'avatar': avatar,
                'status': 1,
                'deleted': 0
            }
            
            # 4. 插入数据库
            new_id = self.user_repo.insert(user_data)
            
            if not new_id:
                return {'success': False, 'msg': '创建失败'}
            
            # 5. 查询新创建的用户
            new_user = self.user_repo.find_by_id(new_id)
            
            return {
                'success': True,
                'user': User.from_dict(new_user) if new_user else None,
                'msg': '创建成功'
            }
            
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return {'success': False, 'msg': f'系统错误: {str(e)}'}
    
    def update_user(self, 
                    user_id: int,
                    update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID（主键）
            update_data: 要更新的字段字典
            
        Returns:
            {'success': True, 'msg': '更新成功'}
            或 {'success': False, 'msg': '错误信息'}
        """
        try:
            # 1. 检查用户是否存在
            user = self.user_repo.find_by_id(user_id)
            if not user:
                return {'success': False, 'msg': '用户不存在'}
            
            # 2. 过滤不允许更新的字段
            allowed_fields = {'user_name', 'phone', 'avatar', 'status'}
            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            if not filtered_data:
                return {'success': False, 'msg': '没有可更新的字段'}
            
            # 3. 执行更新
            affected = self.user_repo.update(user_id, filtered_data)
            
            if affected > 0:
                return {'success': True, 'msg': '更新成功'}
            else:
                return {'success': False, 'msg': '更新失败或数据未变化'}
                
        except Exception as e:
            logger.error(f"更新用户失败: {e}")
            return {'success': False, 'msg': f'系统错误: {str(e)}'}
    
    def disable_user(self, user_id: int) -> Dict[str, Any]:
        """禁用用户"""
        return self.update_user(user_id, {'status': 0})
    
    def enable_user(self, user_id: int) -> Dict[str, Any]:
        """启用用户"""
        return self.update_user(user_id, {'status': 1})
    
    def delete_user(self, user_id: int, soft: bool = True) -> Dict[str, Any]:
        """
        删除用户
        
        Args:
            user_id: 用户ID
            soft: True-软删除, False-硬删除
            
        Returns:
            {'success': True, 'msg': '删除成功'}
        """
        try:
            user = self.user_repo.find_by_id(user_id)
            if not user:
                return {'success': False, 'msg': '用户不存在'}
            
            if soft:
                affected = self.user_repo.soft_delete(user_id)
            else:
                affected = self.user_repo.delete(user_id)
            
            if affected > 0:
                return {'success': True, 'msg': '删除成功'}
            else:
                return {'success': False, 'msg': '删除失败'}
                
        except Exception as e:
            logger.error(f"删除用户失败: {e}")
            return {'success': False, 'msg': f'系统错误: {str(e)}'}


    def get_user_profile(self, user_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        获取个人中心综合信息
        
        整合：会员信息 + 未读通知 + 收藏数 + 优惠券数 + 评价数
        
        Args:
            user_id: 用户ID
            use_cache: 是否使用缓存
            
        Returns:
            {'success': True, 'data': {profile_data}}
        """
        try:
            # 1. 尝试缓存
            if use_cache:
                try:
                    from business_common.cache_service import cache_get
                    cached = cache_get(f'user_profile_{user_id}')
                    if cached:
                        return {'success': True, 'data': cached}
                except Exception:
                    pass
            
            # 2. 查询会员信息
            member = self.user_repo.db.get_one(
                "SELECT user_id, user_name, phone, member_level, points, "
                "total_points, balance FROM business_members WHERE user_id=%s",
                [user_id]
            )
            if not member:
                member = {
                    'user_id': user_id, 'points': 0, 'total_points': 0,
                    'balance': 0, 'member_level': 'bronze'
                }
            
            # 3. 查询未读通知数
            unread_notif = self.user_repo.db.get_total(
                "SELECT COUNT(*) FROM business_notifications "
                "WHERE user_id=%s AND is_read=0 AND deleted=0", [user_id]
            )
            
            # 4. 查询收藏数
            fav_count = self.user_repo.db.get_total(
                "SELECT COUNT(*) FROM business_favorites WHERE user_id=%s", [user_id]
            )
            
            # 5. 查询可用优惠券数
            coupon_count = 0
            try:
                coupon_count = self.user_repo.db.get_total(
                    """SELECT COUNT(*) FROM business_user_coupons uc
                       WHERE uc.user_id=%s AND uc.status='unused'
                       AND (SELECT valid_until FROM business_coupons c WHERE c.id=uc.coupon_id) >= CURDATE()""",
                    [user_id]
                )
            except Exception:
                pass
            
            # 6. 查询评价数
            review_count = 0
            try:
                review_count = self.user_repo.db.get_total(
                    "SELECT COUNT(*) FROM business_reviews WHERE user_id=%s AND deleted=0",
                    [user_id]
                )
            except Exception:
                pass
            
            # 7. 组装数据
            data = {
                'member': member,
                'unread_notifications': unread_notif,
                'favorites_count': fav_count,
                'coupons_count': coupon_count,
                'reviews_count': review_count
            }
            
            # 8. 写入缓存（30秒）
            if use_cache:
                try:
                    from business_common.cache_service import cache_set
                    cache_set(f'user_profile_{user_id}', data, 30)
                except Exception:
                    pass
            
            return {'success': True, 'data': data}
            
        except Exception as e:
            logger.error(f"获取用户档案失败: {e}")
            return {'success': False, 'msg': f'系统错误: {str(e)}'}


# 单例模式，方便全局使用
_user_service = None

def get_user_service() -> UserService:
    """获取 UserService 单例"""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
