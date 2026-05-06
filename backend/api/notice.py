"""
通知公告API
公告发布、阅读记录
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

from db.base import get_db
from db.models.notice import Notice, NoticeRead
from utils.auth_util import OAuth2PasswordBearer, verify_token
from utils.response_util import success_response, paginate_response, created_response, updated_response
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class NoticeCreate(BaseModel):
    ftitle: str
    fcontent: str
    fnotice_type: str = "notice"
    fimportance: str = "normal"
    faudience_type: str = "all"
    fec_id: str
    fproject_id: Optional[str] = None
    feffective_start: Optional[date] = None
    feffective_end: Optional[date] = None


# ========== 通知公告 ==========

@router.get("", summary="获取公告列表")
async def list_notices(
    fproject_id: Optional[str] = None,
    fnotice_type: Optional[str] = None,
    fstatus: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取公告列表"""
    query = db.query(Notice).filter(Notice.is_deleted == 0, Notice.fstatus == "published")
    
    if fproject_id:
        query = query.filter(Notice.fproject_id == fproject_id)
    if fnotice_type:
        query = query.filter(Notice.fnotice_type == fnotice_type)
    
    # 按置顶和发布时间排序
    query = query.order_by(Notice.fistop.desc(), Notice.fpublish_time.desc())
    
    total = query.count()
    notices = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [{
        "fid": n.fid,
        "ftitle": n.ftitle,
        "fnotice_type": n.fnotice_type,
        "fimportance": n.fimportance,
        "fistop": n.fistop,
        "fpublish_time": n.fpublish_time.strftime("%Y-%m-%d %H:%M") if n.fpublish_time else None,
        "fread_count": n.fread_count,
        "fpublisher_name": n.fpublisher_name
    } for n in notices]
    return paginate_response(items, total, page, page_size)


@router.post("", summary="创建公告")
async def create_notice(
    data: NoticeCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建公告"""
    # 从token获取用户信息
    payload = verify_token(token)
    user_id = payload.get("user_id") if payload else None
    
    notice = Notice(
        fid=generate_fid("notice"),
        ftitle=data.ftitle,
        fcontent=data.fcontent,
        fnotice_type=data.fnotice_type,
        fimportance=data.fimportance,
        faudience_type=data.faudience_type,
        fec_id=data.fec_id,
        fproject_id=data.fproject_id,
        feffective_start=data.feffective_start,
        feffective_end=data.feffective_end,
        fstatus="draft",
        fpublisher_id=user_id
    )
    db.add(notice)
    db.commit()
    return created_response(data={"fid": notice.fid})


@router.put("/{notice_id}/publish", summary="发布公告")
async def publish_notice(
    notice_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """发布公告"""
    notice = db.query(Notice).filter(Notice.fid == notice_id, Notice.is_deleted == 0).first()
    if not notice:
        return {"code": 404, "message": "公告不存在"}
    
    notice.fstatus = "published"
    notice.fpublish_time = datetime.now()
    db.commit()
    return updated_response(message="公告发布成功")


@router.put("/{notice_id}/revoke", summary="撤回公告")
async def revoke_notice(
    notice_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """撤回公告"""
    notice = db.query(Notice).filter(Notice.fid == notice_id, Notice.is_deleted == 0).first()
    if not notice:
        return {"code": 404, "message": "公告不存在"}
    
    notice.fstatus = "revoked"
    notice.funpublish_time = datetime.now()
    db.commit()
    return updated_response(message="公告已撤回")


@router.get("/{notice_id}", summary="获取公告详情")
async def get_notice(
    notice_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取公告详情"""
    notice = db.query(Notice).filter(Notice.fid == notice_id, Notice.is_deleted == 0).first()
    if not notice:
        return {"code": 404, "message": "公告不存在"}
    
    return success_response(data={
        "fid": notice.fid,
        "ftitle": notice.ftitle,
        "fcontent": notice.fcontent,
        "fnotice_type": notice.fnotice_type,
        "fimportance": notice.fimportance,
        "faudience_type": notice.faudience_type,
        "fstatus": notice.fstatus,
        "fistop": notice.fistop,
        "fpublish_time": notice.fpublish_time.strftime("%Y-%m-%d %H:%M:%S") if notice.fpublish_time else None,
        "fread_count": notice.fread_count,
        "flike_count": notice.flike_count,
        "fpublisher_name": notice.fpublisher_name,
        "fattachment_urls": notice.fattachment_urls,
        "fcover_url": notice.fcover_url
    })


@router.post("/{notice_id}/read", summary="标记已读")
async def mark_read(
    notice_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """标记公告已读"""
    payload = verify_token(token)
    if not payload:
        return {"code": 401, "message": "Token无效"}
    
    user_id = payload.get("user_id")
    
    # 检查是否已读
    existing = db.query(NoticeRead).filter(
        NoticeRead.fnotice_id == notice_id,
        NoticeRead.freader_id == user_id,
        NoticeRead.is_deleted == 0
    ).first()
    
    if existing:
        return success_response(message="已标记已读")
    
    # 创建阅读记录
    read_record = NoticeRead(
        fid=generate_fid("nr"),
        fnotice_id=notice_id,
        freader_id=user_id,
        freader_type="staff",
        fread_time=datetime.now(),
        fec_id=payload.get("fec_id", ""),
        fproject_id=payload.get("fproject_id", "")
    )
    db.add(read_record)
    
    # 更新阅读数
    notice = db.query(Notice).filter(Notice.fid == notice_id).first()
    if notice:
        notice.fread_count = (notice.fread_count or 0) + 1
    
    db.commit()
    return success_response(message="已标记已读")


@router.post("/{notice_id}/like", summary="点赞公告")
async def like_notice(
    notice_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """点赞公告"""
    payload = verify_token(token)
    if not payload:
        return {"code": 401, "message": "Token无效"}
    
    user_id = payload.get("user_id")
    
    # 检查是否已点赞
    read_record = db.query(NoticeRead).filter(
        NoticeRead.fnotice_id == notice_id,
        NoticeRead.freader_id == user_id,
        NoticeRead.is_deleted == 0
    ).first()
    
    if read_record and read_record.fliked == 1:
        return success_response(message="已点赞")
    
    if read_record:
        read_record.fliked = 1
        read_record.flike_time = datetime.now()
    else:
        read_record = NoticeRead(
            fid=generate_fid("nr"),
            fnotice_id=notice_id,
            freader_id=user_id,
            freader_type="staff",
            fread_time=datetime.now(),
            fliked=1,
            flike_time=datetime.now(),
            fec_id=payload.get("fec_id", ""),
            fproject_id=payload.get("fproject_id", "")
        )
        db.add(read_record)
    
    # 更新点赞数
    notice = db.query(Notice).filter(Notice.fid == notice_id).first()
    if notice:
        notice.flike_count = (notice.flike_count or 0) + 1
    
    db.commit()
    return success_response(message="点赞成功")