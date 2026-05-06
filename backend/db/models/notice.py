# db/models/notice.py - 通知公告表模型
from sqlalchemy import Column, String, Text, Integer
from db.base import BaseModel


class Notice(BaseModel):
    """通知公告表 · t_notice_info"""
    __tablename__ = "t_notice_info"
    __table_args__ = {"comment": "通知公告表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    enterprise_id = Column(String(64), nullable=False, comment="园区ID")
    title = Column(String(256), nullable=False, comment="公告标题")
    content = Column(Text, nullable=False, comment="公告内容")
    type = Column(String(16), default="公告", comment="类型：紧急/公告/活动")
    publisher_name = Column(String(64), nullable=False, comment="发布人")
    read_count = Column(Integer, default=0, comment="阅读数")
    is_pinned = Column(Integer, default=0, comment="是否置顶：0=否 1=是")
    expire_date = Column(String(16), nullable=True, comment="过期日期")
