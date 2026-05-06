"""
访客管理模型
包含：访客记录、访客黑名单
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Date
from db.base import BaseModel
import datetime


class Visitor(BaseModel):
    """访客记录表"""
    __tablename__ = "t_visitor"

    fid = Column(String(64), primary_key=True, comment="访客ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 访客信息
    fvisitor_name = Column(String(50), nullable=False, comment="访客姓名")
    fvisitor_phone = Column(String(20), nullable=False, comment="访客电话")
    fvisitor_id_card = Column(String(18), nullable=True, comment="访客身份证号")
    fvisitor_company = Column(String(200), nullable=True, comment="访客单位")
    fvisitor_count = Column(Integer, default=1, comment="访客人数")
    
    # 被访人信息
    fowner_id = Column(String(64), nullable=False, index=True, comment="被访业主ID")
    fowner_name = Column(String(50), nullable=False, comment="被访人姓名")
    fowner_phone = Column(String(20), nullable=False, comment="被访人电话")
    froom_id = Column(String(64), nullable=False, index=True, comment="被访房间ID")
    
    # 访问信息
    fvisit_purpose = Column(String(200), nullable=True, comment="来访事由")
    fvisit_type = Column(String(20), default="personal", comment="访问类型：personal=个人访客 business=商务访客 delivery=快递外卖 maintenance=维修服务 other=其他")
    
    # 预约信息
    fis_appointment = Column(Integer, default=0, comment="是否预约：0=否 1=是")
    fappointment_time = Column(DateTime, nullable=True, comment="预约时间")
    
    # 进出信息
    fentry_time = Column(DateTime, nullable=True, comment="进入时间")
    fentry_gate = Column(String(100), nullable=True, comment="进入通道")
    fexit_time = Column(DateTime, nullable=True, comment="离开时间")
    fexit_gate = Column(String(100), nullable=True, comment="离开通道")
    
    # 状态
    fstatus = Column(String(20), default="invited", comment="状态：invited=已邀请 visiting=访问中 left=已离开 rejected=已拒绝 expired=已过期")
    
    # 车辆信息
    fhas_vehicle = Column(Integer, default=0, comment="是否有车：0=否 1=是")
    fvehicle_no = Column(String(20), nullable=True, comment="车牌号")
    
    # 邀请码
    finvite_code = Column(String(20), nullable=True, unique=True, comment="邀请码")
    finvite_expire_time = Column(DateTime, nullable=True, comment="邀请码过期时间")
    
    # 人脸照片
    fface_photo_url = Column(String(500), nullable=True, comment="人脸照片URL")
    
    fremark = Column(Text, nullable=True, comment="备注")
    fcreate_user_id = Column(String(64), nullable=True, comment="创建人ID")


class VisitorBlacklist(BaseModel):
    """访客黑名单表"""
    __tablename__ = "t_visitor_blacklist"

    fid = Column(String(64), primary_key=True, comment="记录ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 黑名单人员信息
    fperson_name = Column(String(50), nullable=False, comment="人员姓名")
    fperson_phone = Column(String(20), nullable=True, comment="人员电话")
    fperson_id_card = Column(String(18), nullable=True, index=True, comment="身份证号")
    fperson_company = Column(String(200), nullable=True, comment="单位")
    
    # 黑名单原因
    fblacklist_reason = Column(String(200), nullable=False, comment="拉黑原因：dangerous=危险人员 debt=欠费人员 malicious=恶意破坏 other=其他")
    fblacklist_desc = Column(Text, nullable=True, comment="详细说明")
    
    # 时间信息
    fblacklist_time = Column(DateTime, nullable=False, comment="拉黑时间")
    funblacklist_time = Column(DateTime, nullable=True, comment="解除时间")
    
    # 状态
    fstatus = Column(String(20), default="active", comment="状态：active=生效 inactive=已解除")
    
    # 操作人员
    foperator_id = Column(String(64), nullable=False, comment="操作人ID")
    foperator_name = Column(String(50), nullable=True, comment="操作人姓名")
    
    # 备注
    fremark = Column(Text, nullable=True, comment="备注")
