from sqlalchemy import Column, String, Integer, Text, Date
from db.base import BaseModel

class Owner(BaseModel):
    """
    业主表模型
    对应数据库表：t_owner
    """
    __tablename__ = "t_owner"
    __table_args__ = {"comment": "业主信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    
    # 基础信息
    owner_name = Column(String(50), nullable=False, comment="业主姓名")
    owner_type = Column(String(20), default="personal", comment="业主类型：personal/enterprise")
    gender = Column(String(10), nullable=True, comment="性别：male/female")
    phone = Column(String(20), nullable=False, comment="手机号")
    id_card = Column(String(255), nullable=True, comment="身份证号（加密）")
    birthday = Column(Date, nullable=True, comment="出生日期")
    
    # 企业信息（企业业主）
    enterprise_name = Column(String(100), nullable=True, comment="企业名称")
    credit_code = Column(String(50), nullable=True, comment="统一社会信用代码")
    legal_person = Column(String(50), nullable=True, comment="法人代表")
    
    # 关联信息
    room_id = Column(String(64), nullable=True, comment="关联房间ID")
    owner_role = Column(String(20), default="owner", comment="业主角色：owner/family/tenant/admin")
    
    # VIP信息
    vip_level = Column(String(20), default="normal", comment="VIP等级：black_gold/diamond/normal")
    vip_points = Column(Integer, default=0, comment="VIP积分")
    
    # 特殊标记
    is_special_care = Column(Integer, default=0, comment="是否特殊关怀：0=否 1=是")
    special_care_type = Column(String(50), nullable=True, comment="特殊关怀类型：elderly/disabled/attention")
    
    # 入住信息
    move_in_date = Column(Date, nullable=True, comment="入住日期")
    move_out_date = Column(Date, nullable=True, comment="搬离日期")
    
    # 微信信息
    wechat_openid = Column(String(64), nullable=True, comment="微信OpenID")
    wechat_unionid = Column(String(64), nullable=True, comment="微信UnionID")
    
    # 备注信息
    remark = Column(Text, nullable=True, comment="备注")
    status = Column(Integer, default=1, comment="状态：0=禁用 1=启用")


class Tenant(BaseModel):
    """
    租户表模型
    对应数据库表：t_tenant
    """
    __tablename__ = "t_tenant"
    __table_args__ = {"comment": "租户信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    
    # 基础信息
    tenant_name = Column(String(100), nullable=False, comment="租户名称/企业名称")
    tenant_type = Column(String(20), default="enterprise", comment="租户类型：personal/enterprise")
    
    # 企业信息
    credit_code = Column(String(50), nullable=True, comment="统一社会信用代码")
    legal_person = Column(String(50), nullable=True, comment="法人代表")
    contact_person = Column(String(50), nullable=True, comment="联系人")
    contact_phone = Column(String(20), nullable=True, comment="联系电话")
    
    # 关联信息
    room_id = Column(String(64), nullable=True, comment="关联房间ID")
    
    # 租赁信息
    lease_start_date = Column(Date, nullable=True, comment="租赁开始日期")
    lease_end_date = Column(Date, nullable=True, comment="租赁结束日期")
    
    # 行业信息（商写业态）
    industry = Column(String(50), nullable=True, comment="行业类型")
    brand = Column(String(100), nullable=True, comment="品牌名称")
    
    # VIP信息
    vip_level = Column(String(20), default="normal", comment="VIP等级：black_gold/diamond/normal")
    vip_points = Column(Integer, default=0, comment="VIP积分")
    
    # 微信信息
    wechat_openid = Column(String(64), nullable=True, comment="微信OpenID")
    wechat_unionid = Column(String(64), nullable=True, comment="微信UnionID")
    
    remark = Column(Text, nullable=True, comment="备注")
    status = Column(Integer, default=1, comment="状态：0=禁用 1=启用")


class FamilyMember(BaseModel):
    """
    家庭成员表模型
    对应数据库表：t_family_member
    """
    __tablename__ = "t_family_member"
    __table_args__ = {"comment": "家庭成员信息表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    
    # 关联业主
    owner_id = Column(String(64), nullable=False, comment="业主ID")
    room_id = Column(String(64), nullable=True, comment="房间ID")
    
    # 基础信息
    member_name = Column(String(50), nullable=False, comment="成员姓名")
    relation = Column(String(20), nullable=True, comment="与业主关系：spouse/child/parent/other")
    gender = Column(String(10), nullable=True, comment="性别：male/female")
    phone = Column(String(20), nullable=True, comment="手机号")
    id_card = Column(String(255), nullable=True, comment="身份证号（加密）")
    birthday = Column(Date, nullable=True, comment="出生日期")
    
    # 权限信息
    permission_level = Column(Integer, default=1, comment="权限级别：1=查看 2=操作 3=管理")
    
    # 微信信息
    wechat_openid = Column(String(64), nullable=True, comment="微信OpenID")
    
    status = Column(Integer, default=1, comment="状态：0=禁用 1=启用")
