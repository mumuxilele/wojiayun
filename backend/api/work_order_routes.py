# api/work_order_routes.py - 工单管理API
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from config.db_config import get_db
from service.work_order_service import WorkOrderService

router = APIRouter(prefix="/api/work-orders", tags=["工单管理"])

FEC_ID = "default_fec"
FPROJECT_ID = "default_project"


@router.get("")
def list_work_orders(
    status: str = Query(default=""),
    level: str = Query(default=""),
    keyword: str = Query(default=""),
    enterprise_id: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    svc = WorkOrderService(db)
    return svc.list_work_orders(FEC_ID, FPROJECT_ID, status, level, keyword, enterprise_id, page, page_size)


@router.get("/{fid}")
def get_work_order(fid: str, db: Session = Depends(get_db)):
    svc = WorkOrderService(db)
    return svc.get_work_order(FEC_ID, FPROJECT_ID, fid)


@router.post("")
def create_work_order(body: dict, db: Session = Depends(get_db)):
    svc = WorkOrderService(db)
    return svc.create_work_order(FEC_ID, FPROJECT_ID, **body)


@router.post("/{fid}/assign")
def assign_work_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = WorkOrderService(db)
    return svc.assign_work_order(FEC_ID, FPROJECT_ID, fid, body.get("assignee_id", ""), body.get("assignee_name", ""))


@router.post("/{fid}/complete")
def complete_work_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = WorkOrderService(db)
    return svc.complete_work_order(FEC_ID, FPROJECT_ID, fid, body.get("rating", 5))
