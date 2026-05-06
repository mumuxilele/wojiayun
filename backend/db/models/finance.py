"""
财务管理模型
包含：收费项目、账单、缴费记录、发票
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric, Date
from db.base import BaseModel
import datetime


class FeeItem(BaseModel):
    """收费项目表"""
    __tablename__ = "t_fee_item"

    fid = Column(String(64), primary_key=True, comment="项目ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 基本信息
    fitem_name = Column(String(100), nullable=False, comment="收费项目名称")
    fitem_code = Column(String(50), nullable=True, comment="项目编码")
    fcategory = Column(String(50), nullable=False, comment="收费类型：property=物业费 parking=停车费 water=水费 electricity=电费 gas=燃气费 other=其他")
    
    # 计费方式
    fcharge_type = Column(String(20), nullable=False, comment="计费方式：fixed=固定金额 area=按面积 meter=按表计 other=其他")
    fprice = Column(Numeric(10, 4), nullable=True, comment="单价")
    fprice_unit = Column(String(20), nullable=True, comment="单价单位：yuan_per_sqm=元/㎡ yuan_per_degree=元/度 yuan_per_ton=元/吨")
    
    # 周期设置
    fcycle_type = Column(String(20), default="monthly", comment="收费周期：monthly=按月 quarterly=按季 yearly=按年 once=一次性")
    
    # 状态
    fstatus = Column(String(20), default="active", comment="状态：active=生效 inactive=停用")
    
    fremark = Column(Text, nullable=True, comment="备注")
    fcreate_user_id = Column(String(64), nullable=True, comment="创建人ID")


class Bill(BaseModel):
    """账单表"""
    __tablename__ = "t_bill"

    fid = Column(String(64), primary_key=True, comment="账单ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 关联信息
    ffee_item_id = Column(String(64), nullable=False, comment="收费项目ID")
    fowner_id = Column(String(64), nullable=False, index=True, comment="业主ID")
    froom_id = Column(String(64), nullable=False, index=True, comment="房间ID")
    
    # 账单编号
    fbill_no = Column(String(50), nullable=False, unique=True, comment="账单编号")
    
    # 账单周期
    fbill_period_start = Column(Date, nullable=False, comment="账单周期开始")
    fbill_period_end = Column(Date, nullable=False, comment="账单周期结束")
    
    # 金额信息
    fquantity = Column(Numeric(10, 2), default=1, comment="数量(面积/用量)")
    fprice = Column(Numeric(10, 4), nullable=False, comment="单价")
    famount = Column(Numeric(12, 2), nullable=False, comment="应收金额")
    fpaid_amount = Column(Numeric(12, 2), default=0, comment="已缴金额")
    fdiscount_amount = Column(Numeric(12, 2), default=0, comment="优惠金额")
    flate_fee = Column(Numeric(12, 2), default=0, comment="滞纳金")
    fbalance = Column(Numeric(12, 2), nullable=False, comment="欠缴金额")
    
    # 缴费状态
    fstatus = Column(String(20), default="unpaid", comment="状态：unpaid=未缴 partial=部分已缴 paid=已缴 overdue=逾期")
    
    # 时间信息
    fissue_date = Column(Date, nullable=False, comment="开单日期")
    fdue_date = Column(Date, nullable=False, comment="应缴日期")
    fpaid_time = Column(DateTime, nullable=True, comment="缴费时间")
    
    # 打印信息
    fprint_count = Column(Integer, default=0, comment="打印次数")
    flast_print_time = Column(DateTime, nullable=True, comment="最后打印时间")
    
    fremark = Column(Text, nullable=True, comment="备注")
    fcreate_user_id = Column(String(64), nullable=True, comment="创建人ID")


class Payment(BaseModel):
    """缴费记录表"""
    __tablename__ = "t_payment"

    fid = Column(String(64), primary_key=True, comment="记录ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 关联信息
    fbill_id = Column(String(64), nullable=False, index=True, comment="账单ID")
    fowner_id = Column(String(64), nullable=False, index=True, comment="业主ID")
    froom_id = Column(String(64), nullable=False, comment="房间ID")
    
    # 支付信息
    fpayment_no = Column(String(50), nullable=False, unique=True, comment="支付流水号")
    fpayment_method = Column(String(20), nullable=False, comment="支付方式：wechat=微信 alipay=支付宝 cash=现金 bank=银行转账 pos=POS机")
    fpayment_channel = Column(String(50), nullable=True, comment="支付渠道：app=APP miniprogram=小程序 counter=柜台")
    
    # 金额信息
    fpayment_amount = Column(Numeric(12, 2), nullable=False, comment="支付金额")
    fdiscount_amount = Column(Numeric(12, 2), default=0, comment="优惠金额")
    
    # 第三方支付信息
    fthird_party_no = Column(String(100), nullable=True, comment="第三方支付单号")
    fpay_time = Column(DateTime, nullable=False, comment="支付时间")
    
    # 状态
    fstatus = Column(String(20), default="success", comment="状态：pending=待支付 success=成功 failed=失败 refund=已退款")
    
    # 退款信息
    frefund_amount = Column(Numeric(12, 2), nullable=True, comment="退款金额")
    frefund_time = Column(DateTime, nullable=True, comment="退款时间")
    frefund_reason = Column(Text, nullable=True, comment="退款原因")
    
    # 操作信息
    foperator_id = Column(String(64), nullable=True, comment="操作人ID")
    foperator_name = Column(String(50), nullable=True, comment="操作人姓名")
    
    fremark = Column(Text, nullable=True, comment="备注")


class Invoice(BaseModel):
    """发票表"""
    __tablename__ = "t_invoice"

    fid = Column(String(64), primary_key=True, comment="发票ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 关联信息
    fpayment_id = Column(String(64), nullable=False, index=True, comment="缴费记录ID")
    fowner_id = Column(String(64), nullable=False, index=True, comment="业主ID")
    
    # 发票信息
    finvoice_no = Column(String(50), nullable=False, unique=True, comment="发票号码")
    finvoice_type = Column(String(20), nullable=False, comment="发票类型：normal=普通发票 special=增值税专用发票 electronic=电子发票")
    finvoice_title = Column(String(200), nullable=False, comment="发票抬头")
    ftax_no = Column(String(50), nullable=True, comment="纳税人识别号")
    
    # 开票信息
    fbank_name = Column(String(100), nullable=True, comment="开户银行")
    fbank_account = Column(String(50), nullable=True, comment="银行账号")
    faddress = Column(String(200), nullable=True, comment="地址")
    fphone = Column(String(20), nullable=True, comment="电话")
    
    # 金额信息
    famount = Column(Numeric(12, 2), nullable=False, comment="开票金额")
    ftax_amount = Column(Numeric(12, 2), default=0, comment="税额")
    
    # 状态
    fstatus = Column(String(20), default="issued", comment="状态：issued=已开票 voided=已作废")
    
    # 时间信息
    fissue_date = Column(Date, nullable=False, comment="开票日期")
    fvoid_time = Column(DateTime, nullable=True, comment="作废时间")
    fvoid_reason = Column(Text, nullable=True, comment="作废原因")
    
    # 电子发票
    felectronic_url = Column(String(500), nullable=True, comment="电子发票URL")
    
    # 操作信息
    foperator_id = Column(String(64), nullable=True, comment="开票人ID")
    foperator_name = Column(String(50), nullable=True, comment="开票人姓名")
    
    fremark = Column(Text, nullable=True, comment="备注")
