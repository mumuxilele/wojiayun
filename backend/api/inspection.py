"""
品质管理API
巡检任务、巡检记录、PCAR
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

from db.base import get_db
from db.models.inspection import InspectionTask, InspectionRecord, PCAR
from utils.auth_util import OAuth2PasswordBearer
from utils.response_util import success_response, paginate_response, created_response, updated_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class InspectionTaskCreate(BaseModel):
    ftask_name: str
    ftask_type: str
    fcheck_items: str
    fec_id: str
    fproject_id: str
    fstart_date: date
    fend_date: Optional[date] = None


class InspectionRecordCreate(BaseModel):
    ftask_id: Optional[str] = None
    finspection_type: str
    flocation: str
    fec_id: str
    fproject_id: str
    finspector_id: str
    finspector_name: str
    fresult: str
    fissue_desc: Optional[str] = None


# ========== 巡检任务 ==========

@router.get("/tasks", summary="获取巡检任务列表")
async def list_tasks(
    fproject_id: str,
    fstatus: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取巡检任务列表"""
    query = db.query(InspectionTask).filter(
        InspectionTask.fproject_id == fproject_id,
        InspectionTask.is_deleted == 0
    )
    if fstatus:
        query = query.filter(InspectionTask.fstatus == fstatus)
    
    total = query.count()
    tasks = query.order_by(InspectionTask.create_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": t.fid,
        "ftask_name": t.ftask_name,
        "ftask_type": t.ftask_type,
        "fstatus": t.fstatus,
        "ftotal_count": t.ftotal_count,
        "fcompleted_count": t.fcompleted_count,
        "fstart_date": t.fstart_date.strftime("%Y-%m-%d")
    } for t in tasks]
    return paginate_response(items, total, page, page_size)


@router.post("/tasks", summary="创建巡检任务")
async def create_task(
    data: InspectionTaskCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建巡检任务"""
    task = InspectionTask(
        fid=generate_fid("itask"),
        ftask_name=data.ftask_name,
        ftask_type=data.ftask_type,
        fcheck_items=data.fcheck_items,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        fstart_date=data.fstart_date,
        fend_date=data.fend_date,
        fstatus="active"
    )
    db.add(task)
    db.commit()
    return created_response(data={"fid": task.fid})


# ========== 巡检记录 ==========

@router.get("/records", summary="获取巡检记录列表")
async def list_records(
    fproject_id: str,
    ftask_id: Optional[str] = None,
    fresult: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取巡检记录列表"""
    query = db.query(InspectionRecord).filter(
        InspectionRecord.fproject_id == fproject_id,
        InspectionRecord.is_deleted == 0
    )
    if ftask_id:
        query = query.filter(InspectionRecord.ftask_id == ftask_id)
    if fresult:
        query = query.filter(InspectionRecord.fresult == fresult)
    
    total = query.count()
    records = query.order_by(InspectionRecord.finspection_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": r.fid,
        "flocation": r.flocation,
        "fresult": r.fresult,
        "fscore": r.fscore,
        "fissue_count": r.fissue_count,
        "finspector_name": r.finspector_name,
        "finspection_time": r.finspection_time.strftime("%Y-%m-%d %H:%M")
    } for r in records]
    return paginate_response(items, total, page, page_size)


@router.post("/records", summary="创建巡检记录")
async def create_record(
    data: InspectionRecordCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建巡检记录"""
    record = InspectionRecord(
        fid=generate_fid("irec"),
        ftask_id=data.ftask_id,
        finspection_type=data.finspection_type,
        flocation=data.flocation,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        finspector_id=data.finspector_id,
        finspector_name=data.finspector_name,
        fresult=data.fresult,
        fissue_desc=data.fissue_desc,
        finspection_date=date.today(),
        finspection_time=datetime.now(),
        frectify_status="none" if data.fresult == "pass" else "pending"
    )
    db.add(record)
    db.commit()
    return created_response(data={"fid": record.fid})


# ========== PCAR ==========

@router.get("/pcar", summary="获取PCAR列表")
async def list_pcar(
    fproject_id: str,
    frectify_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取PCAR列表"""
    query = db.query(PCAR).filter(
        PCAR.fproject_id == fproject_id,
        PCAR.is_deleted == 0
    )
    if frectify_status:
        query = query.filter(PCAR.frectify_status == frectify_status)
    
    total = query.count()
    pcars = query.order_by(PCAR.create_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": p.fid,
        "fissue_no": p.fissue_no,
        "fissue_type": p.fissue_type,
        "fissue_level": p.fissue_level,
        "fissue_desc": p.fissue_desc,
        "frectify_status": p.frectify_status,
        "frectify_deadline": p.frectify_deadline.strftime("%Y-%m-%d")
    } for p in pcars]
    return paginate_response(items, total, page, page_size)