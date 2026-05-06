"""
安全管理API
安全事件、安全隐患
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from db.base import get_db
from db.models.safety import SafetyIncident, SafetyHazard
from utils.auth_util import OAuth2PasswordBearer
from utils.response_util import success_response, paginate_response, created_response, updated_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class SafetyIncidentCreate(BaseModel):
    fincident_name: str
    fincident_type: str
    fincident_level: str
    foccur_location: str
    fincident_desc: str
    fec_id: str
    fproject_id: str
    foccur_time: datetime


class SafetyHazardCreate(BaseModel):
    fhazard_name: str
    fhazard_type: str
    fhazard_level: str
    fdiscover_location: str
    fhazard_desc: str
    frectify_requirement: str
    frectify_deadline: str
    fec_id: str
    fproject_id: str
    fdiscoverer_id: str
    fdiscoverer_name: str


# ========== 安全事件 ==========

@router.get("/incidents", summary="获取安全事件列表")
async def list_incidents(
    fproject_id: str,
    fstatus: Optional[str] = None,
    fincident_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取安全事件列表"""
    query = db.query(SafetyIncident).filter(
        SafetyIncident.fproject_id == fproject_id,
        SafetyIncident.is_deleted == 0
    )
    if fstatus:
        query = query.filter(SafetyIncident.fstatus == fstatus)
    if fincident_type:
        query = query.filter(SafetyIncident.fincident_type == fincident_type)
    
    total = query.count()
    incidents = query.order_by(SafetyIncident.foccur_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": i.fid,
        "fincident_no": i.fincident_no,
        "fincident_name": i.fincident_name,
        "fincident_type": i.fincident_type,
        "fincident_level": i.fincident_level,
        "fstatus": i.fstatus,
        "foccur_time": i.foccur_time.strftime("%Y-%m-%d %H:%M"),
        "foccur_location": i.foccur_location
    } for i in incidents]
    return paginate_response(items, total, page, page_size)


@router.post("/incidents", summary="创建安全事件")
async def create_incident(
    data: SafetyIncidentCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建安全事件"""
    # 生成事件编号
    incident_no = f"INC{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    incident = SafetyIncident(
        fid=generate_fid("inc"),
        fincident_no=incident_no,
        fincident_name=data.fincident_name,
        fincident_type=data.fincident_type,
        fincident_level=data.fincident_level,
        foccur_location=data.foccur_location,
        fincident_desc=data.fincident_desc,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        foccur_time=data.foccur_time,
        fstatus="processing"
    )
    db.add(incident)
    db.commit()
    return created_response(data={"fid": incident.fid, "fincident_no": incident_no})


@router.put("/incidents/{incident_id}/complete", summary="完成安全事件处理")
async def complete_incident(
    incident_id: str,
    fhandle_desc: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """完成安全事件处理"""
    incident = db.query(SafetyIncident).filter(
        SafetyIncident.fid == incident_id,
        SafetyIncident.is_deleted == 0
    ).first()
    if not incident:
        return {"code": 404, "message": "事件不存在"}
    
    incident.fhandle_desc = fhandle_desc
    incident.fstatus = "completed"
    incident.fhandle_time = datetime.now()
    db.commit()
    return updated_response(message="事件处理完成")


# ========== 安全隐患 ==========

@router.get("/hazards", summary="获取安全隐患列表")
async def list_hazards(
    fproject_id: str,
    frectify_status: Optional[str] = None,
    fhazard_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取安全隐患列表"""
    query = db.query(SafetyHazard).filter(
        SafetyHazard.fproject_id == fproject_id,
        SafetyHazard.is_deleted == 0
    )
    if frectify_status:
        query = query.filter(SafetyHazard.frectify_status == frectify_status)
    if fhazard_type:
        query = query.filter(SafetyHazard.fhazard_type == fhazard_type)
    
    total = query.count()
    hazards = query.order_by(SafetyHazard.fdiscover_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": h.fid,
        "fhazard_no": h.fhazard_no,
        "fhazard_name": h.fhazard_name,
        "fhazard_type": h.fhazard_type,
        "fhazard_level": h.fhazard_level,
        "frectify_status": h.frectify_status,
        "fdiscover_time": h.fdiscover_time.strftime("%Y-%m-%d %H:%M"),
        "frectify_deadline": h.frectify_deadline.strftime("%Y-%m-%d")
    } for h in hazards]
    return paginate_response(items, total, page, page_size)


@router.post("/hazards", summary="创建安全隐患")
async def create_hazard(
    data: SafetyHazardCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建安全隐患"""
    # 生成隐患编号
    hazard_no = f"HZD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    from datetime import date
    hazard = SafetyHazard(
        fid=generate_fid("hzd"),
        fhazard_no=hazard_no,
        fhazard_name=data.fhazard_name,
        fhazard_type=data.fhazard_type,
        fhazard_level=data.fhazard_level,
        fdiscover_location=data.fdiscover_location,
        fhazard_desc=data.fhazard_desc,
        frectify_requirement=data.frectify_requirement,
        frectify_deadline=date.fromisoformat(data.frectify_deadline),
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        fdiscoverer_id=data.fdiscoverer_id,
        fdiscoverer_name=data.fdiscoverer_name,
        fdiscover_time=datetime.now(),
        frectify_status="pending"
    )
    db.add(hazard)
    db.commit()
    return created_response(data={"fid": hazard.fid, "fhazard_no": hazard_no})


@router.put("/hazards/{hazard_id}/rectify", summary="整改安全隐患")
async def rectify_hazard(
    hazard_id: str,
    frectify_desc: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """整改安全隐患"""
    hazard = db.query(SafetyHazard).filter(
        SafetyHazard.fid == hazard_id,
        SafetyHazard.is_deleted == 0
    ).first()
    if not hazard:
        return {"code": 404, "message": "隐患不存在"}
    
    hazard.frectify_desc = frectify_desc
    hazard.frectify_status = "completed"
    hazard.frectify_time = datetime.now()
    db.commit()
    return updated_response(message="整改完成")