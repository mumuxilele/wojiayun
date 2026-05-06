"""
装修管理模型
包含：装修申请、装修巡查
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric, Date
from db.base import BaseModel
import datetime


class DecorationApplication(BaseModel):
    """装修申请表"""
    __tablename__ = "t_decoration_application"

    fid = Column(String(64), primary_key=True, comment="申请ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 申请人信息
    fowner_id = Column(String(64), nullable=False, index=True, comment="业主ID")
    fowner_name = Column(String(50), nullable=False, comment="业主姓名")
    fowner_phone = Column(String(20), nullable=False, comment="业主电话")
    froom_id = Column(String(64), nullable=False, index=True, comment="房间ID")
    
    # 装修信息
    fdecoration_type = Column(String(20), nullable=False, comment="装修类型：new=新装修 renovation=翻新 extension=扩建")
    fdecoration_area = Column(Numeric(10, 2), nullable=True, comment="装修面积(㎡)")
    fdecoration_scope = Column(Text, nullable=True, comment="装修范围")
    fdecoration_content = Column(Text, nullable=False, comment="装修内容")
    
    # 施工信息
    fstart_date = Column(Date, nullable=False, comment="计划开始日期")
    fend_date = Column(Date, nullable=False, comment="计划结束日期")
    fconstruction_company = Column(String(200), nullable=True, comment="施工单位")
    fconstructor_name = Column(String(50), nullable=True, comment="施工负责人")
    fconstructor_phone = Column(String(20), nullable=True, comment="施工负责人电话")
    fworker_count = Column(Integer, default=0, comment="施工人数")
    
    # 费用信息
    fdeposit = Column(Numeric(10, 2), default=0, comment="装修押金")
    fdeposit_paid = Column(Integer, default=0, comment="押金是否已缴：0=否 1=是")
    fdeposit_returned = Column(Integer, default=0, comment="押金是否已退：0=否 1=是")
    fdeposit_return_time = Column(DateTime, nullable=True, comment="押金退还时间")
    
    # 审批信息
    fstatus = Column(String(20), default="pending", comment="状态：pending=待审核 approved=已通过 rejected=已驳回 construction=施工中 completed=已完成 terminated=已终止")
    fapprover_id = Column(String(64), nullable=True, comment="审批人ID")
    fapprover_name = Column(String(50), nullable=True, comment="审批人姓名")
    fapprove_time = Column(DateTime, nullable=True, comment="审批时间")
    fapprove_opinion = Column(Text, nullable=True, comment="审批意见")
    
    # 实际时间
    factual_start_date = Column(Date, nullable=True, comment="实际开始日期")
    factual_end_date = Column(Date, nullable=True, comment="实际结束日期")
    
    # 附件
    fdesign_urls = Column(Text, nullable=True, comment="设计图纸URLs(JSON数组)")
    flicense_urls = Column(Text, nullable=True, comment="施工资质URLs(JSON数组)")
    fother_urls = Column(Text, nullable=True, comment="其他附件URLs(JSON数组)")
    
    fremark = Column(Text, nullable=True, comment="备注")
    fcreate_user_id = Column(String(64), nullable=True, comment="创建人ID")


class DecorationInspection(BaseModel):
    """装修巡查表"""
    __tablename__ = "t_decoration_inspection"

    fid = Column(String(64), primary_key=True, comment="巡查ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 关联装修申请
    fapplication_id = Column(String(64), nullable=False, index=True, comment="装修申请ID")
    froom_id = Column(String(64), nullable=False, index=True, comment="房间ID")
    
    # 巡查信息
    finspection_type = Column(String(20), nullable=False, comment="巡查类型：routine=日常巡查 acceptance=竣工验收 special=专项检查")
    finspection_date = Column(Date, nullable=False, comment="巡查日期")
    finspection_time = Column(DateTime, nullable=False, comment="巡查时间")
    
    # 巡查人员
    finspector_id = Column(String(64), nullable=False, comment="巡查人ID")
    finspector_name = Column(String(50), nullable=True, comment="巡查人姓名")
    
    # 巡查结果
    fresult = Column(String(20), default="normal", comment="巡查结果：normal=正常 abnormal=异常")
    fissue_desc = Column(Text, nullable=True, comment="问题描述")
    frectify_requirement = Column(Text, nullable=True, comment="整改要求")
    frectify_deadline = Column(Date, nullable=True, comment="整改期限")
    frectify_status = Column(String(20), default="pending", comment="整改状态：pending=待整改 completed=已整改 verified=已验收")
    
    # 验收信息
    fverifier_id = Column(String(64), nullable=True, comment="验收人ID")
    fverifier_name = Column(String(50), nullable=True, comment="验收人姓名")
    fverify_time = Column(DateTime, nullable=True, comment="验收时间")
    fverify_result = Column(Text, nullable=True, comment="验收结果")
    
    # 附件
    fphoto_urls = Column(Text, nullable=True, comment="现场照片URLs(JSON数组)")
    fvideo_urls = Column(Text, nullable=True, comment="现场视频URLs(JSON数组)")
    
    fremark = Column(Text, nullable=True, comment="备注")
