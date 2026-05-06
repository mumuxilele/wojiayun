"""
设备管理API
设备台账、维保计划、维保记录
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.base import get_db
from db.models.equipment import Equipment, EquipmentCategory, MaintenancePlan, MaintenanceRecord
from utils.auth_util import OAuth2PasswordBearer
from utils.response_util import success_response, paginate_response, created_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class EquipmentCreate(BaseModel):
    fequipment_name: str
    fcategory_id: str
    fec_id: str
    fproject_id: str
    fbrand: Optional[str] = None
    fmodel: Optional[str] = None
    finstall_location: Optional[str] = None


# ========== 设备台账 ==========

@router.get("", summary="获取设备列表")
async def list_equipment(
    fproject_id: str,
    fcategory_id: Optional[str] = None,
    fstatus: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取设备列表"""
    query = db.query(Equipment).filter(
        Equipment.fproject_id == fproject_id,
        Equipment.is_deleted == 0
    )
    if fcategory_id:
        query = query.filter(Equipment.fcategory_id == fcategory_id)
    if fstatus:
        query = query.filter(Equipment.fstatus == fstatus)
    
    total = query.count()
    items_data = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": e.fid,
        "fequipment_name": e.fequipment_name,
        "fequipment_code": e.fequipment_code,
        "fbrand": e.fbrand,
        "fmodel": e.fmodel,
        "fstatus": e.fstatus,
        "finstall_location": e.finstall_location
    } for e in items_data]
    return paginate_response(items, total, page, page_size)


@router.post("", summary="创建设备")
async def create_equipment(
    data: EquipmentCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建设备"""
    equipment = Equipment(
        fid=generate_fid("equip"),
        fequipment_name=data.fequipment_name,
        fcategory_id=data.fcategory_id,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        fbrand=data.fbrand,
        fmodel=data.fmodel,
        finstall_location=data.finstall_location,
        fstatus="normal"
    )
    db.add(equipment)
    db.commit()
    return created_response(data={"fid": equipment.fid})


# ========== 设备分类 ==========

@router.get("/categories", summary="获取设备分类")
async def list_categories(
    fec_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取设备分类"""
    categories = db.query(EquipmentCategory).filter(
        EquipmentCategory.fec_id == fec_id,
        EquipmentCategory.is_deleted == 0
    ).all()
    items = [{"fid": c.fid, "fcategory_name": c.fcategory_name} for c in categories]
    return success_response(data=items)


# ========== 维保记录 ==========

@router.get("/{equipment_id}/maintenance", summary="获取设备维保记录")
async def list_maintenance_records(
    equipment_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取设备维保记录"""
    records = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.fequipment_id == equipment_id,
        MaintenanceRecord.is_deleted == 0
    ).order_by(MaintenanceRecord.fstart_time.desc()).limit(20).all()
    items = [{
        "fid": r.fid,
        "ftype": r.ftype,
        "fwork_content": r.fwork_content,
        "fresult": r.fresult,
        "fstart_time": r.fstart_time.strftime("%Y-%m-%d %H:%M") if r.fstart_time else None,
        "fexecutor_name": r.fexecutor_name
    } for r in records]
    return success_response(data=items)