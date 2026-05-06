# db/models/equipment.py - 设备管理表模型
from sqlalchemy import Column, String, Text
from db.base import BaseModel


class Equipment(BaseModel):
    """设备管理表 · t_equipment_info"""
    __tablename__ = "t_equipment_info"
    __table_args__ = {"comment": "设备管理表"}

    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")

    enterprise_id = Column(String(64), nullable=False, comment="园区ID")
    building_id = Column(String(64), nullable=True, comment="楼栋ID")
    name = Column(String(128), nullable=False, comment="设备名称")
    code = Column(String(64), nullable=False, comment="设备编号")
    type = Column(String(32), nullable=False, comment="设备类型：电梯/空调/消防/配电/给排水/门禁/其他")
    location = Column(String(256), nullable=True, comment="安装位置")
    brand = Column(String(64), nullable=True, comment="品牌")
    model = Column(String(64), nullable=True, comment="型号")
    install_date = Column(String(16), nullable=True, comment="安装日期")
    last_check_date = Column(String(16), nullable=True, comment="最近巡检日期")
    next_check_date = Column(String(16), nullable=True, comment="下次巡检日期")
    status = Column(String(16), default="正常", comment="状态：正常/故障/维修中/已报废")
    fault_count = Column(String(8), default="0", comment="累计故障次数")
    description = Column(Text, nullable=True, comment="备注")
