# db/models/wo_template.py - 工单模板相关模型
from sqlalchemy import Column, String, Integer, Text, Numeric
from db.base import BaseModel


class WoTemplate(BaseModel):
    """工单模板表 · t_wo_template"""
    __tablename__ = "t_wo_template"
    __table_args__ = {"comment": "工单模板表"}

    fid = Column(String(64), primary_key=True, comment="模板ID")
    fec_id = Column(String(64), nullable=False, index=True, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, index=True, comment="项目ID")

    ftemplate_name = Column(String(200), nullable=False, comment="模板名称")
    ftemplate_code = Column(String(50), nullable=False, comment="模板编号")
    fcategory_id = Column(String(64), nullable=False, index=True, comment="关联分类ID")
    fwo_type = Column(String(30), nullable=False, index=True,
                      comment="工单类型: quality=品质检查 equipment=设备巡查 comprehensive=综合巡查")
    fdescription = Column(Text, nullable=True, comment="模板描述")

    # 巡检范围
    fscope_type = Column(String(20), default="project",
                         comment="范围类型: project=全项目 building=楼栋 area=区域 equipment=指定设备")
    fscope_config = Column(Text, nullable=True, comment="范围配置(JSON)")

    # 执行周期
    fcycle_type = Column(String(20), nullable=False,
                         comment="周期类型: daily=每日 weekly=每周 monthly=每月 quarterly=每季度 custom=自定义")
    fcycle_value = Column(Integer, default=1, comment="周期数值")
    fexecute_time = Column(String(10), default="08:00", comment="执行时间点(HH:MM)")

    # SLA
    fsla_level = Column(String(10), default="L3", comment="默认SLA等级")
    fresponse_minutes = Column(Integer, default=60, comment="响应时限(分钟)")
    fcomplete_hours = Column(Integer, default=8, comment="完成时限(小时)")

    # 执行人
    fexecutor_type = Column(String(20), default="assign",
                            comment="执行人类型: assign=指定 role=按角色 auto=自动分配")
    fexecutor_config = Column(Text, nullable=True, comment="执行人配置(JSON)")

    # 状态
    fstatus = Column(String(20), default="active", index=True,
                     comment="状态: active=启用 inactive=停用 draft=草稿")
    fversion = Column(Integer, default=1, comment="版本号")
    fremark = Column(Text, nullable=True, comment="备注")
    fcreate_user_id = Column(String(64), nullable=True, comment="创建人ID")


class WoTemplateItem(BaseModel):
    """模板检查项表 · t_wo_template_item"""
    __tablename__ = "t_wo_template_item"
    __table_args__ = {"comment": "模板检查项表"}

    fid = Column(String(64), primary_key=True, comment="检查项ID")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    ftemplate_id = Column(String(64), nullable=False, index=True, comment="所属模板ID")

    fitem_name = Column(String(200), nullable=False, comment="检查项名称")
    fitem_code = Column(String(50), nullable=True, comment="检查项编码")
    fitem_type = Column(String(20), default="check",
                        comment="检查项类型: check=勾选 score=评分 text=文本 input=输入 photo=拍照")
    fscore_weight = Column(Numeric(5, 2), default=0, comment="评分权重")
    fpass_score = Column(Numeric(5, 2), default=60, comment="合格分数")
    foptions = Column(Text, nullable=True, comment="选项配置(JSON数组)")
    fsort_order = Column(Integer, default=0, comment="排序号")
    fis_required = Column(Integer, default=1, comment="是否必填: 0=否 1=是")
    fremark = Column(Text, nullable=True, comment="备注说明")
