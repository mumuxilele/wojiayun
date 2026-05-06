# api/building_routes.py - 楼栋管理API
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from config.db_config import get_db
from service.building_service import BuildingService

router = APIRouter(prefix="/api/buildings", tags=["楼栋管理"])

FEC_ID = "default_fec"
FPROJECT_ID = "default_project"


@router.get("")
def list_buildings(
    enterprise_id: str = Query(default=""),
    keyword: str = Query(default=""),
    type: str = Query(default="", alias="type"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    svc = BuildingService(db)
    return svc.list_buildings(FEC_ID, FPROJECT_ID, enterprise_id, keyword, type, page, page_size)


@router.get("/{fid}")
def get_building(fid: str, db: Session = Depends(get_db)):
    svc = BuildingService(db)
    return svc.get_building(FEC_ID, FPROJECT_ID, fid)


@router.post("")
def create_building(body: dict, db: Session = Depends(get_db)):
    svc = BuildingService(db)
    return svc.create_building(FEC_ID, FPROJECT_ID, **body)


@router.put("/{fid}")
def update_building(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = BuildingService(db)
    return svc.update_building(FEC_ID, FPROJECT_ID, fid, **body)


@router.delete("/{fid}")
def delete_building(fid: str, db: Session = Depends(get_db)):
    svc = BuildingService(db)
    return svc.delete_building(FEC_ID, FPROJECT_ID, fid)
