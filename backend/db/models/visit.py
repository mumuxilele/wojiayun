# db/models/visit.py - 访客预约表模型
from sqlalchemy import Column, String, Text
from db.base import BaseModel


class Visit(BaseModel):
    """访客预约表 · t_visit_info"""
    __tablename__ = "t_visit_info"
    __table_args__ = {"comment": "访客预约表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    enterprise_id = Column(String(64), nullable=False, comment="园区ID")
    building_id = Column(String(64), nullable=False, comment="楼栋ID")
    room_number = Column(String(32), nullable=False, comment="到访房间号")
    host_name = Column(String(64), nullable=False, comment="被访人姓名")
    host_phone = Column(String(20), nullable=False, comment="被访人电话")
    visitor_name = Column(String(64), nullable=False, comment="访客姓名")
    visitor_phone = Column(String(20), nullable=False, comment="访客电话")
    visitor_count = Column(String(8), default="1", comment="到访人数")
    visit_date = Column(String(16), nullable=False, comment="到访日期")
    visit_time_start = Column(String(8), nullable=False, comment="到访开始时间")
    visit_time_end = Column(String(8), nullable=False, comment="到访结束时间")
    reason = Column(Text, nullable=True, comment="到访事由")
    pass_code = Column(String(16), nullable=True, comment="通行码")
    status = Column(String(16), default="待审核", comment="状态：待审核/已通过/已到访/已离开/已拒绝")
