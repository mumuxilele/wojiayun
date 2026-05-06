"""
财务管理API
收费项目、账单、缴费、发票
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

from db.base import get_db
from db.models.finance import FeeItem, Bill, Payment, Invoice
from utils.auth_util import OAuth2PasswordBearer
from utils.response_util import success_response, paginate_response, created_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class FeeItemCreate(BaseModel):
    fitem_name: str
    fcategory: str
    fcharge_type: str
    fec_id: str
    fproject_id: str
    fprice: Optional[float] = None


class BillCreate(BaseModel):
    ffee_item_id: str
    fowner_id: str
    froom_id: str
    fec_id: str
    fproject_id: str
    fbill_period_start: date
    fbill_period_end: date
    famount: float
    fdue_date: date


# ========== 收费项目 ==========

@router.get("/fee-items", summary="获取收费项目")
async def list_fee_items(
    fproject_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取收费项目列表"""
    items = db.query(FeeItem).filter(
        FeeItem.fproject_id == fproject_id,
        FeeItem.is_deleted == 0,
        FeeItem.fstatus == "active"
    ).all()
    result = [{"fid": i.fid, "fitem_name": i.fitem_name, "fcategory": i.fcategory, "fprice": i.fprice} for i in items]
    return success_response(data=result)


# ========== 账单管理 ==========

@router.get("/bills", summary="获取账单列表")
async def list_bills(
    fproject_id: str,
    fowner_id: Optional[str] = None,
    fstatus: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取账单列表"""
    query = db.query(Bill).filter(
        Bill.fproject_id == fproject_id,
        Bill.is_deleted == 0
    )
    if fowner_id:
        query = query.filter(Bill.fowner_id == fowner_id)
    if fstatus:
        query = query.filter(Bill.fstatus == fstatus)
    
    total = query.count()
    bills = query.order_by(Bill.fissue_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": b.fid,
        "fbill_no": b.fbill_no,
        "famount": b.famount,
        "fbalance": b.fbalance,
        "fstatus": b.fstatus,
        "fdue_date": b.fdue_date.strftime("%Y-%m-%d"),
        "fbill_period_start": b.fbill_period_start.strftime("%Y-%m-%d"),
        "fbill_period_end": b.fbill_period_end.strftime("%Y-%m-%d")
    } for b in bills]
    return paginate_response(items, total, page, page_size)


@router.post("/bills", summary="创建账单")
async def create_bill(
    data: BillCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建账单"""
    # 生成账单编号
    bill_no = f"BILL{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    bill = Bill(
        fid=generate_fid("bill"),
        ffee_item_id=data.ffee_item_id,
        fowner_id=data.fowner_id,
        froom_id=data.froom_id,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        fbill_no=bill_no,
        fbill_period_start=data.fbill_period_start,
        fbill_period_end=data.fbill_period_end,
        famount=data.famount,
        fbalance=data.famount,
        fdue_date=data.fdue_date,
        fissue_date=date.today(),
        fstatus="unpaid"
    )
    db.add(bill)
    db.commit()
    return created_response(data={"fid": bill.fid, "fbill_no": bill_no})


# ========== 缴费记录 ==========

@router.get("/payments", summary="获取缴费记录")
async def list_payments(
    fbill_id: Optional[str] = None,
    fowner_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取缴费记录"""
    query = db.query(Payment).filter(Payment.is_deleted == 0)
    if fbill_id:
        query = query.filter(Payment.fbill_id == fbill_id)
    if fowner_id:
        query = query.filter(Payment.fowner_id == fowner_id)
    
    total = query.count()
    payments = query.order_by(Payment.fpay_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": p.fid,
        "fpayment_no": p.fpayment_no,
        "fpayment_amount": p.fpayment_amount,
        "fpayment_method": p.fpayment_method,
        "fpay_time": p.fpay_time.strftime("%Y-%m-%d %H:%M:%S"),
        "fstatus": p.fstatus
    } for p in payments]
    return paginate_response(items, total, page, page_size)