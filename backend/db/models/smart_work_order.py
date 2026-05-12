# db/models/smart_work_order.py - 智慧工单主表模型
from sqlalchemy import Column, String, Integer, Text, DateTime, Date, Numeric
from db.base import BaseModel


class SmartWorkOrder(BaseModel):
    """智慧工单主表 · t_smart_work_order"""
    __tablename__ = "t_smart_work_order"
    __table_args__ = {"comment": "智慧工单主表"}

    fid = Column(String(64), primary_key=True, comment="工单ID")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")

    # 工单基本信息
    fwo_no = Column(String(50), nullable=False, unique=True, comment="工单编号")
    ftitle = Column(String(300), nullable=False, comment="工单标题")
    fdescription = Column(Text, nullable=True, comment="工单描述")

    # 分类与类型
    fcategory_id = Column(String(64), nullable=True, index=True, comment="分类ID")
    fwo_type = Column(String(30), nullable=False, index=True,
                      comment="工单类型: quality=品质检查 equipment=设备巡查 comprehensive=综合巡查 repair=报事报修 other=其他")
    fsub_type = Column(String(50), nullable=True, comment="子类型")

    # 来源
    fsource = Column(String(20), default="manual",
                     comment="来源: manual=手动 system=系统自动 eba=EBA系统 ai=AI品控 complaint=投诉转 inspection=巡检转")
    fsource_id = Column(String(64), nullable=True, comment="来源关联ID")

    # 位置信息
    flocation_type = Column(String(20), default="building",
                            comment="位置类型: building=楼栋 area=区域 equipment=设备 outdoor=室外")
    fbuilding_id = Column(String(64), nullable=True, comment="楼栋ID")
    fbuilding_name = Column(String(100), nullable=True, comment="楼栋名称")
    ffloor = Column(String(20), nullable=True, comment="楼层")
    froom_number = Column(String(32), nullable=True, comment="房间号")
    fequipment_id = Column(String(64), nullable=True, comment="设备ID")
    fequipment_name = Column(String(200), nullable=True, comment="设备名称")
    flocation_detail = Column(String(500), nullable=True, comment="详细位置描述")

    # 优先级与SLA
    fpriority = Column(String(10), default="medium", index=True,
                       comment="优先级: urgent=紧急 high=高 medium=中 low=低")
    fsla_level = Column(String(10), default="L3", index=True, comment="SLA等级: L1/L2/L3/L4")
    fsla_response_deadline = Column(DateTime, nullable=True, comment="SLA响应截止时间")
    fsla_complete_deadline = Column(DateTime, nullable=True, comment="SLA完成截止时间")

    # 模板关联(标准周期工单)
    ftemplate_id = Column(String(64), nullable=True, index=True, comment="模板ID")
    fplan_date = Column(Date, nullable=True, index=True, comment="计划执行日期")
    fplan_time = Column(String(10), nullable=True, comment="计划执行时间")

    # 状态流转
    fstatus = Column(String(30), nullable=False, default="draft", index=True,
                     comment="状态: draft=草稿 pending_dispatch=待派单 dispatched=已派单 accepted=已接收 "
                             "in_progress=执行中 completed=已完成 reviewing=审核中 closed=已关闭 "
                             "cancelled=已取消 rejected=已驳回")
    fcurrent_node = Column(String(50), nullable=True, comment="当前流转节点")

    # 报单人信息
    freporter_id = Column(String(64), nullable=True, index=True, comment="报单人ID")
    freporter_name = Column(String(64), nullable=True, comment="报单人姓名")
    freporter_phone = Column(String(20), nullable=True, comment="报单人电话")
    freporter_type = Column(String(20), default="owner",
                            comment="报单人类型: owner=业主 tenant=租户 staff=员工 system=系统 visitor=访客")

    # 联系人
    fcontact_name = Column(String(64), nullable=True, comment="联系人姓名")
    fcontact_phone = Column(String(20), nullable=True, comment="联系人电话")
    fcontact_time = Column(String(50), nullable=True, comment="期望联系时间")

    # 派单信息
    fdispatch_type = Column(String(20), default="manual", comment="派单方式: auto=自动 manual=手动")
    fdispatch_rule_id = Column(String(64), nullable=True, comment="派单规则ID")
    fdispatched_at = Column(DateTime, nullable=True, comment="派单时间")
    fdispatcher_id = Column(String(64), nullable=True, comment="派单人ID")
    fdispatcher_name = Column(String(64), nullable=True, comment="派单人姓名")

    # 执行人信息
    fassignee_id = Column(String(64), nullable=True, index=True, comment="执行人ID")
    fassignee_name = Column(String(64), nullable=True, comment="执行人姓名")
    fassignee_dept = Column(String(100), nullable=True, comment="执行人部门")
    faccepted_at = Column(DateTime, nullable=True, comment="接收时间")
    fexpected_start_time = Column(DateTime, nullable=True, comment="预计开始时间")
    fexpected_end_time = Column(DateTime, nullable=True, comment="预计完成时间")
    factual_start_time = Column(DateTime, nullable=True, comment="实际开始时间")
    factual_end_time = Column(DateTime, nullable=True, comment="实际完成时间")

    # 处理结果
    fresult_description = Column(Text, nullable=True, comment="处理结果描述")
    fresult_summary = Column(String(500), nullable=True, comment="处理结果摘要")

    # 审核信息
    freviewer_id = Column(String(64), nullable=True, comment="审核人ID")
    freviewer_name = Column(String(64), nullable=True, comment="审核人姓名")
    freviewed_at = Column(DateTime, nullable=True, comment="审核时间")
    freview_opinion = Column(Text, nullable=True, comment="审核意见")
    freview_result = Column(String(20), nullable=True, comment="审核结果: pass=通过 reject=驳回")

    # 评价
    fevaluation_score = Column(Integer, nullable=True, comment="评价分数(1-5)")
    fevaluation_content = Column(Text, nullable=True, comment="评价内容")
    fevaluated_at = Column(DateTime, nullable=True, comment="评价时间")

    # 超期
    fis_overdue = Column(Integer, default=0, comment="是否超期: 0=否 1=是")
    foverdue_minutes = Column(Integer, default=0, comment="超期分钟数")
    foverdue_type = Column(String(20), nullable=True, comment="超期类型: response=响应超期 complete=完成超期")

    # 关联
    fparent_order_id = Column(String(64), nullable=True, comment="父工单ID")
    frelated_order_ids = Column(Text, nullable=True, comment="关联工单IDs(JSON数组)")

    # 附件
    fimage_urls = Column(Text, nullable=True, comment="图片URLs(JSON数组)")
    fvideo_urls = Column(Text, nullable=True, comment="视频URLs(JSON数组)")
    fattachment_urls = Column(Text, nullable=True, comment="附件URLs(JSON数组)")

    # 扩展
    fextra_data = Column(Text, nullable=True, comment="扩展数据(JSON)")
    fremark = Column(Text, nullable=True, comment="备注")
    fcreate_user_id = Column(String(64), nullable=True, comment="创建人ID")
