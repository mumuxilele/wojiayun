# db/models/building.py - 楼栋信息表模型
from sqlalchemy import Column, String, Integer
from db.base import BaseModel


class Building(BaseModel):
    """楼栋信息表 · t_building_info"""
    __tablename__ = "t_building_info"
    __table_args__ = {"comment": "楼栋信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    enterprise_id = Column(String(64), nullable=False, comment="所属园区ID")
    name = Column(String(128), nullable=False, comment="楼栋名称/编号")
    type = Column(String(32), nullable=False, comment="楼栋类型：写字楼/商业楼/住宅楼/配套设施")
    floors = Column(Integer, default=1, comment="楼层数")
    units = Column(Integer, default=0, comment="单元/户数")
    occupied_units = Column(Integer, default=0, comment="已入驻数")
    build_year = Column(String(16), nullable=True, comment="竣工年份")
    elevators = Column(Integer, default=0, comment="电梯数量")
    area_per_floor = Column(Integer, default=0, comment="单层面积（平方米）")
    status = Column(String(16), default="运营中", comment="状态")
