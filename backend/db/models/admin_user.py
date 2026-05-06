# db/models/admin_user.py - 管理员用户表模型
from sqlalchemy import Column, String, Integer
from db.base import BaseModel


class AdminUser(BaseModel):
    """管理员用户表 · t_admin_user"""
    __tablename__ = "t_admin_user"
    __table_args__ = {"comment": "管理员用户表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    username = Column(String(64), nullable=False, comment="用户名")
    password_hash = Column(String(256), nullable=False, comment="密码哈希（bcrypt）")
    name = Column(String(64), nullable=False, comment="真实姓名")
    role = Column(String(32), nullable=False, default="管理员", comment="角色：超级管理员/管理员/客服/财务")
    phone = Column(String(20), nullable=True, comment="手机号")
    enterprise_id = Column(String(64), nullable=True, comment="管理园区ID（空=全局）")
    status = Column(String(16), default="启用", comment="状态：启用/禁用")
    last_login_at = Column(String(20), nullable=True, comment="最后登录时间")
    login_count = Column(Integer, default=0, comment="登录次数")
