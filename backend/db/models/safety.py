"""
安全管理模型
包含：安全事件、安全隐患
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric, Date
from db.base import BaseModel
import datetime


class SafetyIncident(BaseModel):
    """安全事件表"""
    __tablename__ = "t_safety_incident"

    fid = Column(String(64), primary_key=True, comment="事件ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 事件基本信息
    fincident_no = Column(String(50), nullable=False, unique=True, comment="事件编号")
    fincident_name = Column(String(200), nullable=False, comment="事件名称")
    fincident_type = Column(String(50), nullable=False, comment="事件类型：fire=火灾 theft=盗窃 accident=意外事故 fight=斗殴 natural=自然灾害 other=其他")
    fincident_level = Column(String(20), default="minor", comment="事件等级：critical=重大 major=较大 moderate=一般 minor=轻微")
    
    # 发生信息
    foccur_time = Column(DateTime, nullable=False, comment="发生时间")
    foccur_location = Column(String(200), nullable=False, comment="发生地点")
    fbuilding_id = Column(String(64), nullable=True, comment="楼栋ID")
    funit_id = Column(String(64), nullable=True, comment="单元ID")
    
    # 事件描述
    fincident_desc = Column(Text, nullable=False, comment="事件描述")
    fincident_cause = Column(Text, nullable=True, comment="事件原因")
    
    # 人员伤亡
    fdeath_count = Column(Integer, default=0, comment="死亡人数")
    finjury_count = Column(Integer, default=0, comment="受伤人数")
    fcasualty_desc = Column(Text, nullable=True, comment="伤亡情况描述")
    
    # 经济损失
    feconomic_loss = Column(Numeric(12, 2), default=0, comment="经济损失(元)")
    
    # 处理信息
    fhandler_id = Column(String(64), nullable=True, comment="处理人ID")
    fhandler_name = Column(String(50), nullable=True, comment="处理人姓名")
    fhandle_time = Column(DateTime, nullable=True, comment="处理时间")
    fhandle_desc = Column(Text, nullable=True, comment="处理过程")
    
    # 状态
    fstatus = Column(String(20), default="processing", comment="状态：processing=处理中 completed=已完成 closed=已关闭")
    
    # 报告信息
    fis_reported = Column(Integer, default=0, comment="是否上报：0=否 1=是")
    freport_time = Column(DateTime, nullable=True, comment="上报时间")
    freport_dept = Column(String(100), nullable=True, comment="上报部门")
    
    # 责任认定
    fresponsibility_dept = Column(String(100), nullable=True, comment="责任部门")
    fresponsibility_user_id = Column(String(64), nullable=True, comment="责任人ID")
    fresponsibility_user_name = Column(String(50), nullable=True, comment="责任人姓名")
    fpenalty_desc = Column(Text, nullable=True, comment="处罚说明")
    
    # 附件
    fphoto_urls = Column(Text, nullable=True, comment="照片URLs(JSON数组)")
    fvideo_urls = Column(Text, nullable=True, comment="视频URLs(JSON数组)")
    fattachment_urls = Column(Text, nullable=True, comment="附件URLs(JSON数组)")
    
    fremark = Column(Text, nullable=True, comment="备注")
    fcreate_user_id = Column(String(64), nullable=True, comment="创建人ID")


class SafetyHazard(BaseModel):
    """安全隐患表"""
    __tablename__ = "t_safety_hazard"

    fid = Column(String(64), primary_key=True, comment="隐患ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 隐患基本信息
    fhazard_no = Column(String(50), nullable=False, unique=True, comment="隐患编号")
    fhazard_name = Column(String(200), nullable=False, comment="隐患名称")
    fhazard_type = Column(String(50), nullable=False, comment="隐患类型：fire=消防 electrical=电气 elevator=电梯 construction=施工 environment=环境 other=其他")
    fhazard_level = Column(String(20), default="minor", comment="隐患等级：critical=重大 major=较大 moderate=一般 minor=轻微")
    
    # 发现信息
    fdiscover_time = Column(DateTime, nullable=False, comment="发现时间")
    fdiscover_location = Column(String(200), nullable=False, comment="隐患位置")
    fbuilding_id = Column(String(64), nullable=True, comment="楼栋ID")
    funit_id = Column(String(64), nullable=True, comment="单元ID")
    
    # 隐患描述
    fhazard_desc = Column(Text, nullable=False, comment="隐患描述")
    fhazard_cause = Column(Text, nullable=True, comment="隐患原因")
    
    # 发现人
    fdiscoverer_id = Column(String(64), nullable=False, comment="发现人ID")
    fdiscoverer_name = Column(String(50), nullable=True, comment="发现人姓名")
    
    # 整改要求
    frectify_requirement = Column(Text, nullable=False, comment="整改要求")
    frectify_deadline = Column(Date, nullable=False, comment="整改期限")
    
    # 责任信息
    fresponsibility_dept = Column(String(100), nullable=True, comment="责任部门")
    fresponsibility_user_id = Column(String(64), nullable=True, comment="责任人ID")
    fresponsibility_user_name = Column(String(50), nullable=True, comment="责任人姓名")
    
    # 整改信息
    frectify_status = Column(String(20), default="pending", comment="整改状态：pending=待整改 rectifying=整改中 completed=已整改 verified=已验收 overdue=超期")
    frectify_time = Column(DateTime, nullable=True, comment="整改时间")
    frectify_user_id = Column(String(64), nullable=True, comment="整改人ID")
    frectify_user_name = Column(String(50), nullable=True, comment="整改人姓名")
    frectify_desc = Column(Text, nullable=True, comment="整改说明")
    
    # 验收信息
    fverify_status = Column(String(20), default="pending", comment="验收状态：pending=待验收 passed=通过 rejected=驳回")
    fverify_time = Column(DateTime, nullable=True, comment="验收时间")
    fverifier_id = Column(String(64), nullable=True, comment="验收人ID")
    fverifier_name = Column(String(50), nullable=True, comment="验收人姓名")
    fverify_opinion = Column(Text, nullable=True, comment="验收意见")
    
    # 超期处理
    fis_overdue = Column(Integer, default=0, comment="是否超期：0=否 1=是")
    foverdue_days = Column(Integer, default=0, comment="超期天数")
    
    # 附件
    fhazard_photo_urls = Column(Text, nullable=True, comment="隐患照片URLs(JSON数组)")
    frectify_photo_urls = Column(Text, nullable=True, comment="整改照片URLs(JSON数组)")
    
    fremark = Column(Text, nullable=True, comment="备注")
