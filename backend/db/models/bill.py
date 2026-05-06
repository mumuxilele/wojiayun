# db/models/bill.py - 账单表模型
from sqlalchemy import Column, String, Integer, DECIMAL
from db.base import BaseModel


class Bill(BaseModel):
    """账单表 · t_bill_info"""
    __tablename__ = "t_bill_info"
    __table_args__ = {"comment": "账单信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    bill_no = Column(String(32), nullable=False, comment="账单编号")
    enterprise_id = Column(String(64), nullable=False, comment="所属园区ID")
    building_id = Column(String(64), nullable=False, comment="楼栋ID")
    room_number = Column(String(32), nullable=False, comment="房间号")
    resident_name = Column(String(64), nullable=False, comment="住户姓名")
    type = Column(String(32), nullable=False, comment="费用类型：物业费/水电费/车位费/租金/其他")
    period = Column(String(16), nullable=False, comment="费用周期：如2026-04")
    amount = Column(DECIMAL(12, 2), nullable=False, default=0, comment="应收金额")
    paid_amount = Column(DECIMAL(12, 2), default=0, comment="已缴金额")
    status = Column(String(16), default="未缴", comment="状态：未缴/部分缴/已缴")
    due_date = Column(String(16), nullable=True, comment="最后缴纳日期")
    paid_at = Column(String(20), nullable=True, comment="缴纳时间")
