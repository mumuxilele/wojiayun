# db/models/enterprise.py - 园区/企业信息表模型
from sqlalchemy import Column, String, Integer, Text
from db.base import BaseModel


class Enterprise(BaseModel):
    """园区/企业信息表 · t_enterprise_info"""
    __tablename__ = "t_enterprise_info"
    __table_args__ = {"comment": "园区/企业信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    name = Column(String(128), nullable=False, comment="园区/企业名称")
    address = Column(String(256), nullable=False, comment="详细地址")
    type = Column(String(32), nullable=False, default="住宅", comment="业态类型：住宅/写字楼/商业/产业园/公寓")
    contact_person = Column(String(64), nullable=True, comment="联系人")
    contact_phone = Column(String(20), nullable=True, comment="联系电话")
    total_area = Column(Integer, default=0, comment="总面积（平方米）")
    description = Column(Text, nullable=True, comment="园区描述")
    status = Column(String(16), default="运营中", comment="状态：运营中/筹备中/停运")
