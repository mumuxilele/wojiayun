# api/admin_routes.py - 管理员认证与仪表盘API
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from config.db_config import get_db
from service.admin_service import AdminService

router = APIRouter(prefix="/api/admin", tags=["管理员"])

FEC_ID = "default_fec"
FPROJECT_ID = "default_project"


@router.post("/login")
def login(body: dict, db: Session = Depends(get_db)):
    svc = AdminService(db)
    return svc.login(body.get("username", ""), body.get("password", ""))


@router.post("/register")
def register(body: dict, db: Session = Depends(get_db)):
    svc = AdminService(db)
    return svc.create_admin(
        FEC_ID, FPROJECT_ID,
        username=body.get("username", ""),
        password=body.get("password", ""),
        name=body.get("name", ""),
        role=body.get("role", "管理员"),
        phone=body.get("phone", ""),
        enterprise_id=body.get("enterprise_id", "")
    )


@router.post("/change-password")
def change_password(body: dict, db: Session = Depends(get_db)):
    svc = AdminService(db)
    return svc.change_password(
        body.get("fid", ""),
        body.get("old_password", ""),
        body.get("new_password", "")
    )


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    svc = AdminService(db)
    return svc.get_dashboard_stats(FEC_ID, FPROJECT_ID)
