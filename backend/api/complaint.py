"""
投诉管理API
投诉记录、处理流程
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from db.base import get_db
from db.models.complaint import Complaint, ComplaintLog
from utils.auth_util import OAuth2PasswordBearer
from utils.response_util import success_response, paginate_response, created_response, updated_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class ComplaintCreate(BaseModel):
    fcomplainant_name: str
    fcomplainant_phone: str
    fcomplainant_type: str
    fcomplaint_type: str
    ftitle: str
    fcontent: str
    fec_id: str
    fproject_id: str
    froom_id: Optional[str] = None


# ========== 投诉管理 ==========

@router.get("", summary="获取投诉列表")
async def list_complaints(
    fproject_id: str,
    fstatus: Optional[str] = None,
    fcomplaint_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取投诉列表"""
    query = db.query(Complaint).filter(
        Complaint.fproject_id == fproject_id,
        Complaint.is_deleted == 0
    )
    if fstatus:
        query = query.filter(Complaint.fstatus == fstatus)
    if fcomplaint_type:
        query = query.filter(Complaint.fcomplaint_type == fcomplaint_type)
    
    total = query.count()
    complaints = query.order_by(Complaint.fcomplaint_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": c.fid,
        "ftitle": c.ftitle,
        "fcomplaint_type": c.fcomplaint_type,
        "fstatus": c.fstatus,
        "fcomplainant_name": c.fcomplainant_name,
        "fcomplaint_time": c.fcomplaint_time.strftime("%Y-%m-%d %H:%M:%S")
    } for c in complaints]
    return paginate_response(items, total, page, page_size)


@router.post("", summary="创建投诉")
async def create_complaint(
    data: ComplaintCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建投诉"""
    complaint = Complaint(
        fid=generate_fid("comp"),
        fcomplainant_name=data.fcomplainant_name,
        fcomplainant_phone=data.fcomplainant_phone,
        fcomplainant_type=data.fcomplainant_type,
        fcomplaint_type=data.fcomplaint_type,
        ftitle=data.ftitle,
        fcontent=data.fcontent,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        froom_id=data.froom_id,
        fstatus="pending",
        fcomplaint_time=datetime.now(),
        fsource="app"
    )
    db.add(complaint)
    db.commit()
    return created_response(data={"fid": complaint.fid})


@router.put("/{complaint_id}/assign", summary="分配投诉")
async def assign_complaint(
    complaint_id: str,
    fhandler_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """分配投诉给处理人"""
    complaint = db.query(Complaint).filter(Complaint.fid == complaint_id, Complaint.is_deleted == 0).first()
    if not complaint:
        return {"code": 404, "message": "投诉不存在"}
    
    complaint.fhandler_id = fhandler_id
    complaint.fstatus = "processing"
    complaint.fassign_time = datetime.now()
    db.commit()
    return updated_response(message="投诉分配成功")


@router.put("/{complaint_id}/complete", summary="完成投诉处理")
async def complete_complaint(
    complaint_id: str,
    fresult: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """完成投诉处理"""
    complaint = db.query(Complaint).filter(Complaint.fid == complaint_id, Complaint.is_deleted == 0).first()
    if not complaint:
        return {"code": 404, "message": "投诉不存在"}
    
    complaint.fresult = fresult
    complaint.fstatus = "completed"
    complaint.fcomplete_time = datetime.now()
    db.commit()
    return updated_response(message="投诉处理完成")