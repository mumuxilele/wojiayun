# db/models/wo_flow.py - 工单流转与日志模型
from sqlalchemy import Column, String, Integer, Text, DateTime
from db.base import BaseModel


class WoFlowNode(BaseModel):
    """工单流转节点定义表 · t_wo_flow_node"""
    __tablename__ = "t_wo_flow_node"
    __table_args__ = {"comment": "工单流转节点定义表"}

    fid = Column(String(64), primary_key=True, comment="节点ID")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=True, comment="项目ID(NULL=全局)")

    fflow_name = Column(String(100), nullable=False, comment="流程名称")
    fwo_type = Column(String(30), nullable=False, comment="适用工单类型")
    fnode_code = Column(String(50), nullable=False, comment="节点编码")
    fnode_name = Column(String(100), nullable=False, comment="节点名称")
    fnode_type = Column(String(20), nullable=False,
                        comment="节点类型: start=开始 task=任务 approval=审批 end=结束 condition=条件")
    fsort_order = Column(Integer, default=0, comment="排序号")
    fassignee_type = Column(String(20), nullable=True,
                            comment="处理人类型: creator=创建人 dispatcher=派单人 assignee=执行人 reviewer=审核人")
    faction_required = Column(Integer, default=1, comment="是否需要操作: 0=自动 1=需要")
    ftimeout_minutes = Column(Integer, nullable=True, comment="超时时间(分钟)")
    ftimeout_action = Column(String(20), nullable=True, comment="超时动作")
    fremark = Column(Text, nullable=True, comment="备注")


class WoFlowInstance(BaseModel):
    """工单流转实例表 · t_wo_flow_instance"""
    __tablename__ = "t_wo_flow_instance"
    __table_args__ = {"comment": "工单流转实例表"}

    fid = Column(String(64), primary_key=True, comment="实例ID")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    fwo_id = Column(String(64), nullable=False, index=True, comment="工单ID")

    ffrom_node = Column(String(50), nullable=True, comment="来源节点")
    fto_node = Column(String(50), nullable=False, comment="目标节点")
    ffrom_status = Column(String(30), nullable=True, comment="来源状态")
    fto_status = Column(String(30), nullable=False, comment="目标状态")

    foperator_id = Column(String(64), nullable=True, index=True, comment="操作人ID")
    foperator_name = Column(String(64), nullable=True, comment="操作人姓名")
    faction = Column(String(50), nullable=False,
                     comment="操作: create=创建 dispatch=派单 accept=接收 start=开始 execute=执行 "
                             "complete=完成 submit_review=提交审核 review=审核 approve=通过 reject=驳回 "
                             "close=关闭 cancel=取消 transfer=转单 escalate=升级 remind=催办")
    fopinion = Column(Text, nullable=True, comment="操作意见")
    fattachment_urls = Column(Text, nullable=True, comment="附件URLs(JSON数组)")
    fduration_seconds = Column(Integer, nullable=True, comment="节点停留时长(秒)")


class WoOperationLog(BaseModel):
    """工单操作日志表 · t_wo_operation_log"""
    __tablename__ = "t_wo_operation_log"
    __table_args__ = {"comment": "工单操作日志表"}

    fid = Column(String(64), primary_key=True, comment="日志ID")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    fwo_id = Column(String(64), nullable=False, index=True, comment="工单ID")

    foperator_id = Column(String(64), nullable=True, index=True, comment="操作人ID")
    foperator_name = Column(String(64), nullable=True, comment="操作人姓名")
    foperator_type = Column(String(20), nullable=True,
                            comment="操作人类型: system=系统 admin=管理员 staff=员工 owner=业主")
    faction = Column(String(50), nullable=False, index=True, comment="操作类型")
    fdetail = Column(Text, nullable=True, comment="操作详情")
    fip_address = Column(String(50), nullable=True, comment="IP地址")
    fuser_agent = Column(String(500), nullable=True, comment="用户代理")
    fextra_data = Column(Text, nullable=True, comment="扩展数据(JSON)")


class WoCheckRecord(BaseModel):
    """工单检查记录表 · t_wo_check_record"""
    __tablename__ = "t_wo_check_record"
    __table_args__ = {"comment": "工单检查记录表"}

    fid = Column(String(64), primary_key=True, comment="记录ID")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    fwo_id = Column(String(64), nullable=False, index=True, comment="工单ID")
    ftemplate_item_id = Column(String(64), nullable=True, index=True, comment="模板检查项ID")

    fitem_name = Column(String(200), nullable=False, comment="检查项名称")
    fitem_type = Column(String(20), default="check", comment="检查项类型")
    fcheck_result = Column(String(20), nullable=False,
                           comment="检查结果: pass=合格 fail=不合格 na=不适用")
    fscore = Column(Integer, nullable=True, comment="评分")
    fcheck_value = Column(Text, nullable=True, comment="检查值")
    fphoto_urls = Column(Text, nullable=True, comment="照片URLs(JSON数组)")
    fremark = Column(Text, nullable=True, comment="备注")
    finspector_id = Column(String(64), nullable=True, comment="检查人ID")
    finspector_name = Column(String(64), nullable=True, comment="检查人姓名")
    fcheck_time = Column(DateTime, nullable=True, comment="检查时间")


class WoReminder(BaseModel):
    """工单催办记录表 · t_wo_reminder"""
    __tablename__ = "t_wo_reminder"
    __table_args__ = {"comment": "工单催办记录表"}

    fid = Column(String(64), primary_key=True, comment="催办ID")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    fwo_id = Column(String(64), nullable=False, index=True, comment="工单ID")

    freminder_type = Column(String(20), nullable=False, comment="催办类型: system=系统自动 manual=手动")
    freminder_channel = Column(String(20), default="system",
                               comment="催办渠道: system=站内 push=推送 sms=短信 dingtalk=钉钉")
    freminder_content = Column(Text, nullable=True, comment="催办内容")
    freminder_user_id = Column(String(64), nullable=False, comment="催办人ID")
    freminder_user_name = Column(String(64), nullable=True, comment="催办人姓名")
    ftarget_user_id = Column(String(64), nullable=False, index=True, comment="被催办人ID")
    ftarget_user_name = Column(String(64), nullable=True, comment="被催办人姓名")
    fis_read = Column(Integer, default=0, comment="是否已读: 0=未读 1=已读")
    fread_time = Column(DateTime, nullable=True, comment="阅读时间")
