# api/staff_routes.py - 员工管理API
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from config.db_config import get_db
from service.staff_service import StaffService

router = APIRouter(prefix="/api/staff", tags=["员工管理"])

FEC_ID = "default_fec"
FPROJECT_ID = "default_project"


@router.get("")
def list_staff(
    department: str = Query(default=""),
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    svc = StaffService(db)
    return svc.list_staff(FEC_ID, FPROJECT_ID, department, keyword, page, page_size)


@router.get("/{fid}")
def get_staff(fid: str, db: Session = Depends(get_db)):
    svc = StaffService(db)
    return svc.get_staff(FEC_ID, FPROJECT_ID, fid)


@router.post("")
def create_staff(body: dict, db: Session = Depends(get_db)):
    svc = StaffService(db)
    return svc.create_staff(FEC_ID, FPROJECT_ID, **body)
