# api/resident_routes.py - 住户管理API
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from config.db_config import get_db
from service.resident_service import ResidentService

router = APIRouter(prefix="/api/residents", tags=["住户管理"])

FEC_ID = "default_fec"
FPROJECT_ID = "default_project"


@router.get("")
def list_residents(
    enterprise_id: str = Query(default=""),
    building_id: str = Query(default=""),
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    svc = ResidentService(db)
    return svc.list_residents(FEC_ID, FPROJECT_ID, enterprise_id, building_id, keyword, page, page_size)


@router.get("/{fid}")
def get_resident(fid: str, db: Session = Depends(get_db)):
    svc = ResidentService(db)
    return svc.get_resident(FEC_ID, FPROJECT_ID, fid)


@router.post("")
def create_resident(body: dict, db: Session = Depends(get_db)):
    svc = ResidentService(db)
    return svc.create_resident(FEC_ID, FPROJECT_ID, **body)
