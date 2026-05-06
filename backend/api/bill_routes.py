# api/bill_routes.py - 费用管理API
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from config.db_config import get_db
from service.bill_service import BillService

router = APIRouter(prefix="/api/bills", tags=["费用管理"])

FEC_ID = "default_fec"
FPROJECT_ID = "default_project"


@router.get("")
def list_bills(
    type: str = Query(default="", alias="type"),
    status: str = Query(default=""),
    keyword: str = Query(default=""),
    enterprise_id: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    svc = BillService(db)
    return svc.list_bills(FEC_ID, FPROJECT_ID, type, status, enterprise_id, keyword, page, page_size)


@router.post("")
def create_bill(body: dict, db: Session = Depends(get_db)):
    svc = BillService(db)
    return svc.create_bill(FEC_ID, FPROJECT_ID, **body)


@router.post("/{bill_id}/pay")
def record_payment(bill_id: str, body: dict, db: Session = Depends(get_db)):
    from decimal import Decimal
    svc = BillService(db)
    return svc.record_payment(
        FEC_ID, FPROJECT_ID, bill_id,
        amount=Decimal(str(body.get("amount", 0))),
        method=body.get("method", "微信支付"),
        payer_name=body.get("payer_name", ""),
        transaction_no=body.get("transaction_no", ""),
        remark=body.get("remark", "")
    )
