"""
装修管理API
装修申请、装修巡查
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

from db.base import get_db
from db.models.decoration import DecorationApplication, DecorationInspection
from utils.auth_util import OAuth2PasswordBearer
from utils.response_util import success_response, paginate_response, created_response, updated_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class DecorationApplicationCreate(BaseModel):
    fowner_id: str
    fowner_name: str
    fowner_phone: str
    froom_id: str
    fec_id: str
    fproject_id: str
    fdecoration_type: str
    fdecoration_content: str
    fstart_date: date
    fend_date: date


# ========== 装修申请 ==========

@router.get("", summary="获取装修申请列表")
async def list_decorations(
    fproject_id: str,
    fstatus: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取装修申请列表"""
    query = db.query(DecorationApplication).filter(
        DecorationApplication.fproject_id == fproject_id,
        DecorationApplication.is_deleted == 0
    )
    if fstatus:
        query = query.filter(DecorationApplication.fstatus == fstatus)
    
    total = query.count()
    applications = query.order_by(DecorationApplication.create_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": a.fid,
        "fowner_name": a.fowner_name,
        "froom_id": a.froom_id,
        "fdecoration_type": a.fdecoration_type,
        "fstatus": a.fstatus,
        "fstart_date": a.fstart_date.strftime("%Y-%m-%d"),
        "fend_date": a.fend_date.strftime("%Y-%m-%d")
    } for a in applications]
    return paginate_response(items, total, page, page_size)


@router.post("", summary="创建装修申请")
async def create_decoration(
    data: DecorationApplicationCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建装修申请"""
    application = DecorationApplication(
        fid=generate_fid("deco"),
        fowner_id=data.fowner_id,
        fowner_name=data.fowner_name,
        fowner_phone=data.fowner_phone,
        froom_id=data.froom_id,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        fdecoration_type=data.fdecoration_type,
        fdecoration_content=data.fdecoration_content,
        fstart_date=data.fstart_date,
        fend_date=data.fend_date,
        fstatus="pending",
        fissue_date=date.today()
    )
    db.add(application)
    db.commit()
    return created_response(data={"fid": application.fid})


@router.put("/{application_id}/approve", summary="审批装修申请")
async def approve_decoration(
    application_id: str,
    fapprove_opinion: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """审批装修申请"""
    application = db.query(DecorationApplication).filter(
        DecorationApplication.fid == application_id,
        DecorationApplication.is_deleted == 0
    ).first()
    if not application:
        return {"code": 404, "message": "申请不存在"}
    
    application.fstatus = "approved"
    application.fapprove_opinion = fapprove_opinion
    application.fapprove_time = datetime.now()
    db.commit()
    return updated_response(message="审批通过")


# ========== 装修巡查 ==========

@router.get("/{application_id}/inspections", summary="获取装修巡查记录")
async def list_inspections(
    application_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取装修巡查记录"""
    inspections = db.query(DecorationInspection).filter(
        DecorationInspection.fapplication_id == application_id,
        DecorationInspection.is_deleted == 0
    ).order_by(DecorationInspection.finspection_date.desc()).all()
    items = [{
        "fid": i.fid,
        "finspection_type": i.finspection_type,
        "finspection_date": i.finspection_date.strftime("%Y-%m-%d"),
        "fresult": i.fresult,
        "finspector_name": i.finspector_name
    } for i in inspections]
    return success_response(data=items)