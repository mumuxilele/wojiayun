# db/models/repair.py - 报修申请表模型
from sqlalchemy import Column, String, Text
from db.base import BaseModel


class Repair(BaseModel):
    """报修申请表 · t_repair_info"""
    __tablename__ = "t_repair_info"
    __table_args__ = {"comment": "报修申请表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    enterprise_id = Column(String(64), nullable=False, comment="园区ID")
    building_id = Column(String(64), nullable=False, comment="楼栋ID")
    room_number = Column(String(32), nullable=False, comment="房间号")
    applicant_name = Column(String(64), nullable=False, comment="申请人")
    applicant_phone = Column(String(20), nullable=False, comment="联系电话")
    type = Column(String(32), nullable=False, comment="报修类型：水电/空调/门窗/电梯/管道/其他")
    description = Column(Text, nullable=False, comment="问题描述")
    level = Column(String(16), default="普通", comment="紧急程度")
    expect_time = Column(String(32), nullable=True, comment="期望上门时间")
    images = Column(String(1024), nullable=True, comment="现场照片URL，逗号分隔")
    status = Column(String(32), default="待审核", comment="状态：待审核/已派单/维修中/已完成")
    work_order_id = Column(String(64), nullable=True, comment="关联工单ID")
