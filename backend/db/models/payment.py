# db/models/payment.py - 缴费记录表模型
from sqlalchemy import Column, String, DECIMAL
from db.base import BaseModel


class Payment(BaseModel):
    """缴费记录表 · t_payment_record"""
    __tablename__ = "t_payment_record"
    __table_args__ = {"comment": "缴费记录表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    bill_id = Column(String(64), nullable=False, comment="关联账单ID")
    bill_no = Column(String(32), nullable=False, comment="账单编号")
    enterprise_id = Column(String(64), nullable=False, comment="园区ID")
    room_number = Column(String(32), nullable=False, comment="房间号")
    payer_name = Column(String(64), nullable=False, comment="付款人")
    amount = Column(DECIMAL(12, 2), nullable=False, comment="支付金额")
    method = Column(String(16), default="微信支付", comment="支付方式：微信支付/支付宝/银行转账/现金")
    transaction_no = Column(String(64), nullable=True, comment="交易流水号")
    paid_at = Column(String(20), nullable=False, comment="支付时间")
    remark = Column(String(256), nullable=True, comment="备注")
