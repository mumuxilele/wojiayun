# db/models/complaint.py - 投诉建议表模型
from sqlalchemy import Column, String, Text
from db.base import BaseModel


class Complaint(BaseModel):
    """投诉建议表 · t_complaint_info"""
    __tablename__ = "t_complaint_info"
    __table_args__ = {"comment": "投诉建议表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    enterprise_id = Column(String(64), nullable=False, comment="园区ID")
    building_id = Column(String(64), nullable=True, comment="楼栋ID")
    room_number = Column(String(32), nullable=True, comment="房间号")
    reporter_name = Column(String(64), nullable=False, comment="投诉人")
    reporter_phone = Column(String(20), nullable=False, comment="联系电话")
    type = Column(String(32), nullable=False, comment="类型：投诉/建议/表扬")
    category = Column(String(32), nullable=False, comment="分类：噪音/卫生/服务/安全/设施/其他")
    content = Column(Text, nullable=False, comment="投诉内容")
    status = Column(String(32), default="待处理", comment="状态：待处理/处理中/已处理/已回访")
    handler_name = Column(String(64), nullable=True, comment="处理人")
    handler_comment = Column(Text, nullable=True, comment="处理意见")
