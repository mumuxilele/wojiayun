# db/models/work_order.py - 工单表模型
from sqlalchemy import Column, String, Integer, Text
from db.base import BaseModel


class WorkOrder(BaseModel):
    """工单表 · t_work_order"""
    __tablename__ = "t_work_order"
    __table_args__ = {"comment": "工单表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    order_no = Column(String(32), nullable=False, comment="工单编号")
    enterprise_id = Column(String(64), nullable=False, comment="所属园区ID")
    building_id = Column(String(64), nullable=True, comment="楼栋ID")
    room_number = Column(String(32), nullable=True, comment="房间号")
    type = Column(String(32), nullable=False, comment="工单类型：报修/投诉/装修申请/访客/物品放行/其他")
    title = Column(String(256), nullable=False, comment="工单标题")
    description = Column(Text, nullable=True, comment="工单描述")
    level = Column(String(16), default="普通", comment="紧急程度：紧急/普通/低")
    status = Column(String(32), default="待派单", comment="状态：待派单/处理中/已完成/已取消")
    reporter_name = Column(String(64), nullable=True, comment="报单人")
    reporter_phone = Column(String(20), nullable=True, comment="报单人电话")
    assignee_id = Column(String(64), nullable=True, comment="指派人ID")
    assignee_name = Column(String(64), nullable=True, comment="指派人姓名")
    completed_at = Column(String(20), nullable=True, comment="完成时间")
    rating = Column(Integer, nullable=True, comment="评分：1-5")
    images = Column(String(1024), nullable=True, comment="图片URL，逗号分隔")
