"""
品质管理模型
包含：巡检任务、巡检记录、PCAR表
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric, Date
from db.base import BaseModel
import datetime


class InspectionTask(BaseModel):
    """巡检任务表"""
    __tablename__ = "t_inspection_task"

    fid = Column(String(64), primary_key=True, comment="任务ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 任务基本信息
    ftask_name = Column(String(200), nullable=False, comment="任务名称")
    ftask_code = Column(String(50), nullable=True, comment="任务编号")
    ftask_type = Column(String(50), nullable=False, comment="任务类型：daily=日常巡检 weekly=周巡检 monthly=月巡检 special=专项巡检")
    
    # 巡检范围
    fscope_type = Column(String(20), default="project", comment="范围类型：project=全项目 building=楼栋 area=区域")
    fscope_ids = Column(Text, nullable=True, comment="范围IDs(JSON数组)")
    
    # 巡检内容
    fcheck_items = Column(Text, nullable=False, comment="检查项JSON数组")
    
    # 执行周期
    fcycle_type = Column(String(20), default="daily", comment="周期类型：daily=每日 weekly=每周 monthly=每月")
    fcycle_value = Column(Integer, default=1, comment="周期数值")
    fexecute_time = Column(String(10), nullable=True, comment="执行时间点(如:09:00)")
    
    # 执行人员
    fexecutor_type = Column(String(20), default="assign", comment="执行人类型：assign=指定 auto=自动分配")
    fexecutor_ids = Column(Text, nullable=True, comment="执行人IDs(JSON数组)")
    
    # 时间范围
    fstart_date = Column(Date, nullable=False, comment="开始日期")
    fend_date = Column(Date, nullable=True, comment="结束日期")
    
    # 状态
    fstatus = Column(String(20), default="active", comment="状态：active=生效 inactive=停用")
    
    # 统计
    ftotal_count = Column(Integer, default=0, comment="总执行次数")
    fcompleted_count = Column(Integer, default=0, comment="完成次数")
    fpass_count = Column(Integer, default=0, comment="合格次数")
    
    fremark = Column(Text, nullable=True, comment="备注")
    fcreate_user_id = Column(String(64), nullable=True, comment="创建人ID")


class InspectionRecord(BaseModel):
    """巡检记录表"""
    __tablename__ = "t_inspection_record"

    fid = Column(String(64), primary_key=True, comment="记录ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 关联任务
    ftask_id = Column(String(64), nullable=True, index=True, comment="任务ID(临时巡检可为空)")
    
    # 巡检信息
    finspection_type = Column(String(20), nullable=False, comment="巡检类型：routine=常规临时 special=专项")
    finspection_date = Column(Date, nullable=False, comment="巡检日期")
    finspection_time = Column(DateTime, nullable=False, comment="巡检时间")
    
    # 巡检范围
    fbuilding_id = Column(String(64), nullable=True, comment="楼栋ID")
    funit_id = Column(String(64), nullable=True, comment="单元ID")
    farea_id = Column(String(64), nullable=True, comment="区域ID")
    flocation = Column(String(200), nullable=True, comment="巡检位置")
    
    # 巡检人员
    finspector_id = Column(String(64), nullable=False, comment="巡检人ID")
    finspector_name = Column(String(50), nullable=True, comment="巡检人姓名")
    
    # 巡检结果
    fresult = Column(String(20), default="pass", comment="结果：pass=合格 fail=不合格 partial=部分合格")
    fscore = Column(Numeric(5, 2), nullable=True, comment="得分")
    ftotal_items = Column(Integer, default=0, comment="检查项总数")
    fpass_items = Column(Integer, default=0, comment="合格项数")
    ffail_items = Column(Integer, default=0, comment="不合格项数")
    
    # 问题信息
    fissue_count = Column(Integer, default=0, comment="问题数量")
    fissue_desc = Column(Text, nullable=True, comment="问题描述")
    
    # 整改信息
    frectify_status = Column(String(20), default="none", comment="整改状态：none=无需整改 pending=待整改 completed=已整改 verified=已验收")
    frectify_deadline = Column(Date, nullable=True, comment="整改期限")
    frectify_time = Column(DateTime, nullable=True, comment="整改时间")
    frectify_user_id = Column(String(64), nullable=True, comment="整改人ID")
    frectify_user_name = Column(String(50), nullable=True, comment="整改人姓名")
    
    # 验收信息
    fverify_time = Column(DateTime, nullable=True, comment="验收时间")
    fverifier_id = Column(String(64), nullable=True, comment="验收人ID")
    fverifier_name = Column(String(50), nullable=True, comment="验收人姓名")
    
    # 附件
    fphoto_urls = Column(Text, nullable=True, comment="照片URLs(JSON数组)")
    fvideo_urls = Column(Text, nullable=True, comment="视频URLs(JSON数组)")
    
    fremark = Column(Text, nullable=True, comment="备注")


class PCAR(BaseModel):
    """PCAR表（问题整改跟踪）"""
    __tablename__ = "t_pcar"

    fid = Column(String(64), primary_key=True, comment="PCAR ID(MD5)")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    
    # 关联巡检记录
    finspection_id = Column(String(64), nullable=False, index=True, comment="巡检记录ID")
    
    # 问题信息
    fissue_no = Column(String(50), nullable=False, comment="问题编号")
    fissue_type = Column(String(50), nullable=False, comment="问题类型：safety=安全 quality=质量 environment=环境 service=服务 other=其他")
    fissue_level = Column(String(20), default="normal", comment="问题等级：critical=严重 major=较大 minor=一般")
    fissue_desc = Column(Text, nullable=False, comment="问题描述")
    fissue_location = Column(String(200), nullable=True, comment="问题位置")
    
    # 责任信息
    fresponsibility_dept = Column(String(100), nullable=True, comment="责任部门")
    fresponsibility_user_id = Column(String(64), nullable=True, comment="责任人ID")
    fresponsibility_user_name = Column(String(50), nullable=True, comment="责任人姓名")
    
    # 整改要求
    frectify_requirement = Column(Text, nullable=False, comment="整改要求")
    frectify_deadline = Column(Date, nullable=False, comment="整改期限")
    
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
    foverdue_penalty = Column(Numeric(10, 2), default=0, comment="超期扣款")
    
    # 附件
    fissue_photo_urls = Column(Text, nullable=True, comment="问题照片URLs(JSON数组)")
    frectify_photo_urls = Column(Text, nullable=True, comment="整改照片URLs(JSON数组)")
    
    fremark = Column(Text, nullable=True, comment="备注")
