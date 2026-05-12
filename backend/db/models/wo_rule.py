# db/models/wo_rule.py - 工单规则相关模型
from sqlalchemy import Column, String, Integer, Text
from db.base import BaseModel


class WoSlaRule(BaseModel):
    """SLA规则表 · t_wo_sla_rule"""
    __tablename__ = "t_wo_sla_rule"
    __table_args__ = {"comment": "SLA规则表"}

    fid = Column(String(64), primary_key=True, comment="规则ID")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")

    frule_name = Column(String(100), nullable=False, comment="规则名称")
    fsla_level = Column(String(10), nullable=False, unique=True, comment="SLA等级: L1/L2/L3/L4")
    flevel_name = Column(String(50), nullable=False, comment="等级名称: 紧急/高/中/低")
    fpriority = Column(String(10), nullable=False, comment="对应优先级: urgent/high/medium/low")

    fresponse_minutes = Column(Integer, nullable=False, comment="响应时限(分钟)")
    fcomplete_hours = Column(Integer, nullable=False, comment="完成时限(小时)")

    fescalate_minutes = Column(Integer, nullable=True, comment="升级提醒时间(分钟)")
    fescalate_count = Column(Integer, default=3, comment="最大升级次数")
    fescalate_to = Column(String(64), nullable=True, comment="升级通知人ID")

    fis_enabled = Column(Integer, default=1, comment="是否启用: 0=禁用 1=启用")
    fremark = Column(Text, nullable=True, comment="备注")


class WoDispatchRule(BaseModel):
    """派单规则表 · t_wo_dispatch_rule"""
    __tablename__ = "t_wo_dispatch_rule"
    __table_args__ = {"comment": "派单规则表"}

    fid = Column(String(64), primary_key=True, comment="规则ID")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")

    frule_name = Column(String(100), nullable=False, comment="规则名称")
    frule_type = Column(String(20), nullable=False,
                        comment="规则类型: category=按分类 location=按位置 priority=按优先级 time=按时间 keyword=按关键词")
    fmatch_condition = Column(Text, nullable=False, comment="匹配条件(JSON)")
    fdispatch_action = Column(String(20), nullable=False,
                              comment="派单动作: assign_user=指定人员 assign_role=指定角色 assign_dept=指定部门 rotate=轮询")
    fdispatch_target = Column(Text, nullable=False, comment="派单目标(JSON)")

    fpriority = Column(Integer, default=0, comment="规则优先级(数字越大优先级越高)")
    fis_enabled = Column(Integer, default=1, comment="是否启用: 0=禁用 1=启用")
    fremark = Column(Text, nullable=True, comment="备注")


class WoCategory(BaseModel):
    """工单分类表 · t_wo_category"""
    __tablename__ = "t_wo_category"
    __table_args__ = {"comment": "工单分类表"}

    fid = Column(String(64), primary_key=True, comment="分类ID")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")
    fparent_id = Column(String(64), nullable=True, index=True, comment="父分类ID(NULL=顶级)")
    fcategory_name = Column(String(100), nullable=False, comment="分类名称")
    fcategory_code = Column(String(50), nullable=False, comment="分类编码")
    fcategory_type = Column(String(30), nullable=False, index=True,
                            comment="分类类型: quality=品质检查 equipment=设备巡查 comprehensive=综合巡查 repair=报事报修 other=其他")
    ficon = Column(String(200), nullable=True, comment="分类图标URL")
    fsort_order = Column(Integer, default=0, comment="排序号")
    fdescription = Column(Text, nullable=True, comment="分类描述")
    fis_enabled = Column(Integer, default=1, comment="是否启用: 0=禁用 1=启用")
    fcreate_user_id = Column(String(64), nullable=True, comment="创建人ID")
