# service/building_service.py - 楼栋管理业务
from typing import Dict
from sqlalchemy.orm import Session
from service.base_service import BaseService
from db.models import Building
from utils.md5_fid_util import generate_fid
from utils.log_util import logger


class BuildingService(BaseService):
    """楼栋管理服务"""

    def list_buildings(self, fec_id: str, fproject_id: str,
                       enterprise_id: str = "", keyword: str = "",
                       btype: str = "", page: int = 1, page_size: int = 20) -> Dict:
        try:
            q = Building.active_query(self.db).filter(
                Building.fec_id == fec_id,
                Building.fproject_id == fproject_id
            )
            if enterprise_id:
                q = q.filter(Building.enterprise_id == enterprise_id)
            if btype:
                q = q.filter(Building.type == btype)
            if keyword:
                q = q.filter(Building.name.like(f"%{keyword}%"))

            total = q.count()
            items = q.order_by(Building.create_time.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()

            return self.success({
                "total": total, "page": page, "page_size": page_size,
                "items": [self._to_dict(b) for b in items]
            })
        except Exception as e:
            logger.error(f"查询楼栋列表失败：{str(e)}", exc_info=True)
            return self.error(f"查询楼栋列表失败：{str(e)}")

    def create_building(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        try:
            self.begin()
            fid = generate_fid()
            bld = Building(fid=fid, fec_id=fec_id, fproject_id=fproject_id, **kwargs)
            self.db.add(bld)
            self.commit()
            self.db.refresh(bld)
            logger.info(f"新增楼栋成功：fid={fid}")
            return self.success(self._to_dict(bld), "新增成功")
        except Exception as e:
            self.rollback()
            return self.error(f"新增楼栋失败：{str(e)}")

    def update_building(self, fec_id: str, fproject_id: str, fid: str, **kwargs) -> Dict:
        try:
            self.begin()
            bld = Building.active_query(self.db).filter(
                Building.fid == fid, Building.fec_id == fec_id,
                Building.fproject_id == fproject_id
            ).first()
            if not bld:
                return self.error("楼栋不存在", 404)
            for key, value in kwargs.items():
                if hasattr(bld, key) and value is not None:
                    setattr(bld, key, value)
            self.commit()
            return self.success(self._to_dict(bld), "更新成功")
        except Exception as e:
            self.rollback()
            return self.error(f"更新楼栋失败：{str(e)}")

    def delete_building(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        try:
            self.begin()
            bld = Building.active_query(self.db).filter(
                Building.fid == fid, Building.fec_id == fec_id,
                Building.fproject_id == fproject_id
            ).first()
            if not bld:
                return self.error("楼栋不存在", 404)
            bld.is_deleted = 1
            bld.delete_time = __import__('utils.time_util', fromlist=['now']).now()
            self.commit()
            return self.success({"fid": fid}, "删除成功")
        except Exception as e:
            self.rollback()
            return self.error(f"删除楼栋失败：{str(e)}")

    def get_building(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        try:
            bld = Building.active_query(self.db).filter(
                Building.fid == fid, Building.fec_id == fec_id,
                Building.fproject_id == fproject_id
            ).first()
            if not bld:
                return self.error("楼栋不存在", 404)
            return self.success(self._to_dict(bld))
        except Exception as e:
            return self.error(f"查询楼栋详情失败：{str(e)}")

    @staticmethod
    def _to_dict(b: Building) -> dict:
        return {
            "fid": b.fid, "enterprise_id": b.enterprise_id,
            "name": b.name, "type": b.type,
            "floors": b.floors, "units": b.units,
            "occupied_units": b.occupied_units,
            "build_year": b.build_year, "elevators": b.elevators,
            "area_per_floor": b.area_per_floor, "status": b.status,
            "create_time": b.create_time.strftime("%Y-%m-%d %H:%M:%S") if b.create_time else "",
        }
