"""
企业管理API
企业、项目、楼栋、单元、房间管理
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.base import get_db
from db.models.enterprise import Enterprise, Project, Building, Unit, Room
from utils.auth_util import verify_token, OAuth2PasswordBearer
from utils.response_util import (
    success_response, paginate_response, 
    created_response, updated_response, 
    deleted_response, not_found_response
)
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class EnterpriseCreate(BaseModel):
    enterprise_name: str
    enterprise_code: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None


class ProjectCreate(BaseModel):
    project_name: str
    project_code: Optional[str] = None
    business_type: str
    fec_id: str
    total_area: Optional[float] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None


# ========== 企业管理 ==========

@router.get("/enterprises", summary="获取企业列表")
async def list_enterprises(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取所有企业"""
    enterprises = db.query(Enterprise).filter(Enterprise.is_deleted == 0).all()
    items = [{"fid": e.fid, "enterprise_name": e.enterprise_name, "enterprise_code": e.enterprise_code} for e in enterprises]
    return success_response(data=items)


@router.post("/enterprises", summary="创建企业")
async def create_enterprise(
    data: EnterpriseCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建企业"""
    enterprise = Enterprise(
        fid=generate_fid("ent"),
        enterprise_name=data.enterprise_name,
        enterprise_code=data.enterprise_code,
        contact_person=data.contact_person,
        contact_phone=data.contact_phone,
        address=data.address
    )
    db.add(enterprise)
    db.commit()
    return created_response(data={"fid": enterprise.fid})


# ========== 项目管理 ==========

@router.get("/projects", summary="获取项目列表")
async def list_projects(
    fec_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取项目列表"""
    query = db.query(Project).filter(Project.is_deleted == 0)
    if fec_id:
        query = query.filter(Project.fec_id == fec_id)
    
    total = query.count()
    projects = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": p.fid, 
        "project_name": p.project_name, 
        "business_type": p.business_type,
        "province": p.province,
        "city": p.city
    } for p in projects]
    return paginate_response(items, total, page, page_size)


@router.post("/projects", summary="创建项目")
async def create_project(
    data: ProjectCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建项目"""
    project = Project(
        fid=generate_fid("proj"),
        project_name=data.project_name,
        project_code=data.project_code,
        business_type=data.business_type,
        fec_id=data.fec_id,
        total_area=data.total_area,
        province=data.province,
        city=data.city,
        district=data.district,
        address=data.address
    )
    db.add(project)
    db.commit()
    return created_response(data={"fid": project.fid})


# ========== 楼栋管理 ==========

@router.get("/buildings", summary="获取楼栋列表")
async def list_buildings(
    fproject_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取项目下的楼栋"""
    buildings = db.query(Building).filter(
        Building.fproject_id == fproject_id,
        Building.is_deleted == 0
    ).all()
    items = [{"fid": b.fid, "building_name": b.building_name, "building_type": b.building_type} for b in buildings]
    return success_response(data=items)


# ========== 房间管理 ==========

@router.get("/rooms", summary="获取房间列表")
async def list_rooms(
    fbuilding_id: Optional[str] = None,
    funit_id: Optional[str] = None,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取房间列表"""
    query = db.query(Room).filter(Room.is_deleted == 0)
    if fbuilding_id:
        query = query.filter(Room.fbuilding_id == fbuilding_id)
    if funit_id:
        query = query.filter(Room.funit_id == funit_id)
    
    rooms = query.all()
    items = [{
        "fid": r.fid, 
        "room_no": r.room_no, 
        "room_area": r.room_area,
        "room_type": r.room_type
    } for r in rooms]
    return success_response(data=items)