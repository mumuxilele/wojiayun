# service/resident_service.py - 住户管理业务
from typing import Dict
from sqlalchemy.orm import Session
from service.base_service import BaseService
from db.models import Resident
from utils.md5_fid_util import generate_fid
from utils.log_util import logger


class ResidentService(BaseService):
    """住户管理服务"""

    def list_residents(self, fec_id: str, fproject_id: str,
                       enterprise_id: str = "", building_id: str = "",
                       keyword: str = "", page: int = 1, page_size: int = 20) -> Dict:
        try:
            q = Resident.active_query(self.db).filter(
                Resident.fec_id == fec_id,
                Resident.fproject_id == fproject_id
            )
            if enterprise_id:
                q = q.filter(Resident.enterprise_id == enterprise_id)
            if building_id:
                q = q.filter(Resident.building_id == building_id)
            if keyword:
                q = q.filter(
                    Resident.name.like(f"%{keyword}%") |
                    Resident.phone.like(f"%{keyword}%") |
                    Resident.room_number.like(f"%{keyword}%")
                )
            total = q.count()
            items = q.order_by(Resident.create_time.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()
            return self.success({
                "total": total, "page": page, "page_size": page_size,
                "items": [self._to_dict(r) for r in items]
            })
        except Exception as e:
            logger.error(f"查询住户列表失败：{str(e)}", exc_info=True)
            return self.error(f"查询住户列表失败：{str(e)}")

    def create_resident(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        try:
            self.begin()
            fid = generate_fid()
            resident = Resident(fid=fid, fec_id=fec_id, fproject_id=fproject_id, **kwargs)
            self.db.add(resident)
            self.commit()
            self.db.refresh(resident)
            return self.success(self._to_dict(resident), "新增成功")
        except Exception as e:
            self.rollback()
            return self.error(f"新增住户失败：{str(e)}")

    def get_resident(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        try:
            r = Resident.active_query(self.db).filter(
                Resident.fid == fid, Resident.fec_id == fec_id,
                Resident.fproject_id == fproject_id
            ).first()
            if not r:
                return self.error("住户不存在", 404)
            return self.success(self._to_dict(r))
        except Exception as e:
            return self.error(f"查询住户详情失败：{str(e)}")

    @staticmethod
    def _to_dict(r: Resident) -> dict:
        return {
            "fid": r.fid, "enterprise_id": r.enterprise_id,
            "building_id": r.building_id, "room_number": r.room_number,
            "name": r.name, "phone": r.phone, "type": r.type,
            "check_in_date": r.check_in_date, "area": r.area,
            "member_count": r.member_count, "tags": r.tags,
            "create_time": r.create_time.strftime("%Y-%m-%d %H:%M:%S") if r.create_time else "",
        }
