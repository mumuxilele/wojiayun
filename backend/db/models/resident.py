# db/models/resident.py - 住户信息表模型
from sqlalchemy import Column, String, Integer
from db.base import BaseModel


class Resident(BaseModel):
    """住户信息表 · t_resident_info"""
    __tablename__ = "t_resident_info"
    __table_args__ = {"comment": "住户信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    enterprise_id = Column(String(64), nullable=False, comment="所属园区ID")
    building_id = Column(String(64), nullable=False, comment="所属楼栋ID")
    room_number = Column(String(32), nullable=False, comment="房间号")
    name = Column(String(64), nullable=False, comment="住户姓名")
    phone = Column(String(20), nullable=False, comment="手机号")
    id_card = Column(String(18), nullable=True, comment="身份证号")
    type = Column(String(16), default="业主", comment="住户类型：业主/租户/家属")
    check_in_date = Column(String(16), nullable=True, comment="入住日期")
    area = Column(Integer, default=0, comment="建筑面积（平方米）")
    member_count = Column(Integer, default=1, comment="常住人数")
    tags = Column(String(256), nullable=True, comment="标签：VIP/老人/儿童/宠物，逗号分隔")
