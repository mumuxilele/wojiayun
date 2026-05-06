"""
业主管理API
业主、租户、家庭成员管理
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.base import get_db
from db.models.owner import Owner, Tenant, FamilyMember
from utils.auth_util import OAuth2PasswordBearer
from utils.response_util import success_response, paginate_response, created_response, not_found_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class OwnerCreate(BaseModel):
    owner_name: str
    owner_phone: str
    froom_id: str
    fec_id: str
    fproject_id: str
    owner_role: str = "owner"
    id_card: Optional[str] = None
    vip_level: str = "normal"


# ========== 业主管理 ==========

@router.get("", summary="获取业主列表")
async def list_owners(
    fproject_id: Optional[str] = None,
    owner_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取业主列表"""
    query = db.query(Owner).filter(Owner.is_deleted == 0)
    if fproject_id:
        query = query.filter(Owner.fproject_id == fproject_id)
    if owner_name:
        query = query.filter(Owner.owner_name.like(f"%{owner_name}%"))
    
    total = query.count()
    owners = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": o.fid,
        "owner_name": o.owner_name,
        "owner_phone": o.owner_phone,
        "owner_role": o.owner_role,
        "vip_level": o.vip_level,
        "froom_id": o.froom_id
    } for o in owners]
    return paginate_response(items, total, page, page_size)


@router.post("", summary="创建业主")
async def create_owner(
    data: OwnerCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建业主"""
    owner = Owner(
        fid=generate_fid("owner"),
        owner_name=data.owner_name,
        owner_phone=data.owner_phone,
        froom_id=data.froom_id,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        owner_role=data.owner_role,
        id_card=data.id_card,
        vip_level=data.vip_level
    )
    db.add(owner)
    db.commit()
    return created_response(data={"fid": owner.fid})


@router.get("/{owner_id}", summary="获取业主详情")
async def get_owner(
    owner_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取业主详情"""
    owner = db.query(Owner).filter(Owner.fid == owner_id, Owner.is_deleted == 0).first()
    if not owner:
        return not_found_response("业主不存在")
    
    return success_response(data={
        "fid": owner.fid,
        "owner_name": owner.owner_name,
        "owner_phone": owner.owner_phone,
        "owner_role": owner.owner_role,
        "vip_level": owner.vip_level,
        "id_card": owner.id_card,
        "froom_id": owner.froom_id
    })


# ========== 租户管理 ==========

@router.get("/tenants", summary="获取租户列表")
async def list_tenants(
    fproject_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取租户列表"""
    tenants = db.query(Tenant).filter(
        Tenant.fproject_id == fproject_id,
        Tenant.is_deleted == 0
    ).all()
    items = [{
        "fid": t.fid,
        "tenant_name": t.tenant_name,
        "tenant_phone": t.tenant_phone,
        "froom_id": t.froom_id
    } for t in tenants]
    return success_response(data=items)