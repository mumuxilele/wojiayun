# db/models/staff.py - 员工信息表模型
from sqlalchemy import Column, String
from db.base import BaseModel


class Staff(BaseModel):
    """员工信息表 · t_staff_info"""
    __tablename__ = "t_staff_info"
    __table_args__ = {"comment": "员工信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    staff_no = Column(String(32), nullable=False, comment="工号")
    name = Column(String(64), nullable=False, comment="员工姓名")
    phone = Column(String(20), nullable=False, comment="手机号")
    department = Column(String(32), nullable=False, comment="部门：客服部/工程部/安保部/行政部")
    position = Column(String(64), nullable=False, comment="职位")
    enterprise_id = Column(String(64), nullable=True, comment="所属园区ID")
    status = Column(String(16), default="在岗", comment="状态：在岗/休息/外勤/离职")
    avatar_url = Column(String(256), nullable=True, comment="头像URL")
    hire_date = Column(String(16), nullable=True, comment="入职日期")
