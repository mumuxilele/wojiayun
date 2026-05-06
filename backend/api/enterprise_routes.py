# api/enterprise_routes.py - 园区管理API
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from config.db_config import get_db
from service.enterprise_service import EnterpriseService

router = APIRouter(prefix="/api/enterprises", tags=["园区管理"])

FEC_ID = "default_fec"
FPROJECT_ID = "default_project"


@router.get("")
def list_enterprises(
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    svc = EnterpriseService(db)
    return svc.list_enterprises(FEC_ID, FPROJECT_ID, keyword, page, page_size)


@router.get("/{fid}")
def get_enterprise(fid: str, db: Session = Depends(get_db)):
    svc = EnterpriseService(db)
    return svc.get_enterprise(FEC_ID, FPROJECT_ID, fid)


@router.post("")
def create_enterprise(body: dict, db: Session = Depends(get_db)):
    svc = EnterpriseService(db)
    return svc.create_enterprise(FEC_ID, FPROJECT_ID, **body)


@router.put("/{fid}")
def update_enterprise(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = EnterpriseService(db)
    return svc.update_enterprise(FEC_ID, FPROJECT_ID, fid, **body)


@router.delete("/{fid}")
def delete_enterprise(fid: str, db: Session = Depends(get_db)):
    svc = EnterpriseService(db)
    return svc.delete_enterprise(FEC_ID, FPROJECT_ID, fid)
