from sqlalchemy import Column, String, Integer, Text, Boolean
from db.base import BaseModel

class User(BaseModel):
    """
    用户表模型
    对应数据库表：t_user
    """
    __tablename__ = "t_user"
    __table_args__ = {"comment": "用户信息表"}

    # 主键+隔离字段（强制）
    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    
    # 基础信息
    username = Column(String(50), nullable=False, unique=True, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码（加密存储）")
    real_name = Column(String(50), nullable=False, comment="真实姓名")
    phone = Column(String(20), nullable=False, comment="手机号")
    email = Column(String(100), nullable=True, comment="邮箱")
    avatar = Column(String(512), nullable=True, comment="头像URL")
    
    # 状态与权限
    status = Column(Integer, default=1, comment="状态：0=禁用 1=启用")
    is_admin = Column(Integer, default=0, comment="是否管理员：0=否 1=是")
    department = Column(String(100), nullable=True, comment="部门")
    position = Column(String(100), nullable=True, comment="职位")
    
    # 工号信息
    employee_id = Column(String(50), nullable=True, comment="工号")
    id_card = Column(String(18), nullable=True, comment="身份证号（加密）")
    
    # 微信信息
    wechat_openid = Column(String(64), nullable=True, comment="微信OpenID")
    wechat_unionid = Column(String(64), nullable=True, comment="微信UnionID")


class Role(BaseModel):
    """
    角色表模型
    对应数据库表：t_role
    """
    __tablename__ = "t_role"
    __table_args__ = {"comment": "角色信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    
    role_name = Column(String(50), nullable=False, comment="角色名称")
    role_code = Column(String(50), nullable=False, comment="角色编码")
    description = Column(String(255), nullable=True, comment="角色描述")
    status = Column(Integer, default=1, comment="状态：0=禁用 1=启用")


class Permission(BaseModel):
    """
    权限表模型
    对应数据库表：t_permission
    """
    __tablename__ = "t_permission"
    __table_args__ = {"comment": "权限信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    
    permission_name = Column(String(50), nullable=False, comment="权限名称")
    permission_code = Column(String(50), nullable=False, comment="权限编码")
    permission_type = Column(String(20), nullable=False, comment="权限类型：menu/button/api")
    parent_id = Column(String(64), nullable=True, comment="父权限ID")
    path = Column(String(255), nullable=True, comment="路由路径")
    component = Column(String(255), nullable=True, comment="组件路径")
    icon = Column(String(100), nullable=True, comment="图标")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(Integer, default=1, comment="状态：0=禁用 1=启用")


class UserRole(BaseModel):
    """
    用户角色关联表模型
    对应数据库表：t_user_role
    """
    __tablename__ = "t_user_role"
    __table_args__ = {"comment": "用户角色关联表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    
    user_id = Column(String(64), nullable=False, comment="用户ID")
    role_id = Column(String(64), nullable=False, comment="角色ID")


class RolePermission(BaseModel):
    """
    角色权限关联表模型
    对应数据库表：t_role_permission
    """
    __tablename__ = "t_role_permission"
    __table_args__ = {"comment": "角色权限关联表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    
    role_id = Column(String(64), nullable=False, comment="角色ID")
    permission_id = Column(String(64), nullable=False, comment="权限ID")
