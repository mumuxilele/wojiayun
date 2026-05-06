"""
访客管理API
访客邀请、访客记录、黑名单
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from db.base import get_db
from db.models.visitor import Visitor, VisitorBlacklist
from utils.auth_util import OAuth2PasswordBearer
from utils.response_util import success_response, paginate_response, created_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class VisitorInvite(BaseModel):
    fvisitor_name: str
    fvisitor_phone: str
    fowner_id: str
    fowner_name: str
    fowner_phone: str
    froom_id: str
    fec_id: str
    fproject_id: str
    fvisit_purpose: Optional[str] = None
    fvisit_type: str = "personal"


# ========== 访客管理 ==========

@router.get("", summary="获取访客列表")
async def list_visitors(
    fproject_id: str,
    fstatus: Optional[str] = None,
    fowner_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取访客列表"""
    query = db.query(Visitor).filter(
        Visitor.fproject_id == fproject_id,
        Visitor.is_deleted == 0
    )
    if fstatus:
        query = query.filter(Visitor.fstatus == fstatus)
    if fowner_id:
        query = query.filter(Visitor.fowner_id == fowner_id)
    
    total = query.count()
    visitors = query.order_by(Visitor.create_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": v.fid,
        "fvisitor_name": v.fvisitor_name,
        "fvisitor_phone": v.fvisitor_phone,
        "fowner_name": v.fowner_name,
        "fvisit_purpose": v.fvisit_purpose,
        "fstatus": v.fstatus,
        "finvite_code": v.finvite_code,
        "fentry_time": v.fentry_time.strftime("%Y-%m-%d %H:%M") if v.fentry_time else None
    } for v in visitors]
    return paginate_response(items, total, page, page_size)


@router.post("/invite", summary="邀请访客")
async def invite_visitor(
    data: VisitorInvite,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """邀请访客"""
    # 生成邀请码
    import random
    import string
    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    visitor = Visitor(
        fid=generate_fid("vis"),
        fvisitor_name=data.fvisitor_name,
        fvisitor_phone=data.fvisitor_phone,
        fowner_id=data.fowner_id,
        fowner_name=data.fowner_name,
        fowner_phone=data.fowner_phone,
        froom_id=data.froom_id,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        fvisit_purpose=data.fvisit_purpose,
        fvisit_type=data.fvisit_type,
        fstatus="invited",
        finvite_code=invite_code,
        fis_appointment=1,
        fappointment_time=datetime.now()
    )
    db.add(visitor)
    db.commit()
    return created_response(data={
        "fid": visitor.fid,
        "finvite_code": invite_code
    }, message="访客邀请成功")


@router.post("/{visitor_id}/entry", summary="访客入场")
async def visitor_entry(
    visitor_id: str,
    fentry_gate: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """访客入场登记"""
    visitor = db.query(Visitor).filter(Visitor.fid == visitor_id, Visitor.is_deleted == 0).first()
    if not visitor:
        return {"code": 404, "message": "访客不存在"}
    
    visitor.fstatus = "visiting"
    visitor.fentry_time = datetime.now()
    visitor.fentry_gate = fentry_gate
    db.commit()
    return success_response(message="入场登记成功")


@router.post("/{visitor_id}/exit", summary="访客离场")
async def visitor_exit(
    visitor_id: str,
    fexit_gate: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """访客离场登记"""
    visitor = db.query(Visitor).filter(Visitor.fid == visitor_id, Visitor.is_deleted == 0).first()
    if not visitor:
        return {"code": 404, "message": "访客不存在"}
    
    visitor.fstatus = "left"
    visitor.fexit_time = datetime.now()
    visitor.fexit_gate = fexit_gate
    db.commit()
    return success_response(message="离场登记成功")


# ========== 访客黑名单 ==========

@router.get("/blacklist", summary="获取访客黑名单")
async def list_blacklist(
    fproject_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取访客黑名单"""
    blacklist = db.query(VisitorBlacklist).filter(
        VisitorBlacklist.fproject_id == fproject_id,
        VisitorBlacklist.is_deleted == 0,
        VisitorBlacklist.fstatus == "active"
    ).all()
    items = [{
        "fid": b.fid,
        "fperson_name": b.fperson_name,
        "fperson_phone": b.fperson_phone,
        "fblacklist_reason": b.fblacklist_reason,
        "fblacklist_time": b.fblacklist_time.strftime("%Y-%m-%d %H:%M")
    } for b in blacklist]
    return success_response(data=items)