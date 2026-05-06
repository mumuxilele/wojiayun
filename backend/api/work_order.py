"""
工单管理API
工单创建、处理、评价
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.base import get_db
from db.models.work_order import WorkOrder, WorkOrderCategory, WorkOrderLog, WorkOrderRating
from utils.auth_util import OAuth2PasswordBearer
from utils.response_util import success_response, paginate_response, created_response, updated_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class WorkOrderCreate(BaseModel):
    fcategory_id: str
    ftitle: str
    fcontent: str
    fec_id: str
    fproject_id: str
    fowner_id: Optional[str] = None
    froom_id: Optional[str] = None
    sla_level: str = "L2"
    business_type: str = "free"


# ========== 工单管理 ==========

@router.get("", summary="获取工单列表")
async def list_work_orders(
    fproject_id: str,
    fstatus: Optional[str] = None,
    fcategory_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取工单列表"""
    query = db.query(WorkOrder).filter(
        WorkOrder.fproject_id == fproject_id,
        WorkOrder.is_deleted == 0
    )
    if fstatus:
        query = query.filter(WorkOrder.fstatus == fstatus)
    if fcategory_id:
        query = query.filter(WorkOrder.fcategory_id == fcategory_id)
    
    total = query.count()
    orders = query.order_by(WorkOrder.create_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": o.fid,
        "ftitle": o.ftitle,
        "fcategory_id": o.fcategory_id,
        "fstatus": o.fstatus,
        "sla_level": o.sla_level,
        "sla_status": o.sla_status,
        "create_time": o.create_time.strftime("%Y-%m-%d %H:%M:%S")
    } for o in orders]
    return paginate_response(items, total, page, page_size)


@router.post("", summary="创建工单")
async def create_work_order(
    data: WorkOrderCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建工单"""
    order = WorkOrder(
        fid=generate_fid("wo"),
        fcategory_id=data.fcategory_id,
        ftitle=data.ftitle,
        fcontent=data.fcontent,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        fowner_id=data.fowner_id,
        froom_id=data.froom_id,
        sla_level=data.sla_level,
        business_type=data.business_type,
        fstatus="pending"
    )
    db.add(order)
    db.commit()
    return created_response(data={"fid": order.fid}, message="工单创建成功")


@router.put("/{order_id}/assign", summary="分配工单")
async def assign_work_order(
    order_id: str,
    fhandler_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """分配工单给处理人"""
    order = db.query(WorkOrder).filter(WorkOrder.fid == order_id, WorkOrder.is_deleted == 0).first()
    if not order:
        return {"code": 404, "message": "工单不存在"}
    
    order.fhandler_id = fhandler_id
    order.fstatus = "assigned"
    order.fassign_time = datetime.now()
    db.commit()
    return updated_response(message="工单分配成功")


@router.put("/{order_id}/complete", summary="完成工单")
async def complete_work_order(
    order_id: str,
    fresult: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """完成工单"""
    order = db.query(WorkOrder).filter(WorkOrder.fid == order_id, WorkOrder.is_deleted == 0).first()
    if not order:
        return {"code": 404, "message": "工单不存在"}
    
    order.fresult = fresult
    order.fstatus = "completed"
    order.fcomplete_time = datetime.now()
    db.commit()
    return updated_response(message="工单完成")


# ========== 工单分类 ==========

@router.get("/categories", summary="获取工单分类")
async def list_categories(
    fproject_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取工单分类"""
    categories = db.query(WorkOrderCategory).filter(
        WorkOrderCategory.fproject_id == fproject_id,
        WorkOrderCategory.is_deleted == 0
    ).all()
    items = [{"fid": c.fid, "fcategory_name": c.fcategory_name, "fcategory_type": c.fcategory_type} for c in categories]
    return success_response(data=items)