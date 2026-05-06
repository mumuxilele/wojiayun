# service/staff_service.py - 员工管理业务
from typing import Dict
from sqlalchemy.orm import Session
from service.base_service import BaseService
from db.models import Staff
from utils.md5_fid_util import generate_fid
from utils.log_util import logger


class StaffService(BaseService):
    """员工管理服务"""

    def list_staff(self, fec_id: str, fproject_id: str,
                   department: str = "", keyword: str = "",
                   page: int = 1, page_size: int = 20) -> Dict:
        try:
            q = Staff.active_query(self.db).filter(
                Staff.fec_id == fec_id,
                Staff.fproject_id == fproject_id
            )
            if department:
                q = q.filter(Staff.department == department)
            if keyword:
                q = q.filter(
                    Staff.name.like(f"%{keyword}%") |
                    Staff.staff_no.like(f"%{keyword}%") |
                    Staff.phone.like(f"%{keyword}%")
                )
            total = q.count()
            items = q.order_by(Staff.create_time.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()
            return self.success({
                "total": total, "page": page, "page_size": page_size,
                "items": [self._to_dict(s) for s in items]
            })
        except Exception as e:
            logger.error(f"查询员工列表失败：{str(e)}", exc_info=True)
            return self.error(f"查询员工列表失败：{str(e)}")

    def create_staff(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        try:
            self.begin()
            fid = generate_fid()
            staff = Staff(fid=fid, fec_id=fec_id, fproject_id=fproject_id, **kwargs)
            self.db.add(staff)
            self.commit()
            self.db.refresh(staff)
            return self.success(self._to_dict(staff), "新增成功")
        except Exception as e:
            self.rollback()
            return self.error(f"新增员工失败：{str(e)}")

    def get_staff(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        try:
            s = Staff.active_query(self.db).filter(
                Staff.fid == fid, Staff.fec_id == fec_id,
                Staff.fproject_id == fproject_id
            ).first()
            if not s:
                return self.error("员工不存在", 404)
            return self.success(self._to_dict(s))
        except Exception as e:
            return self.error(f"查询员工详情失败：{str(e)}")

    @staticmethod
    def _to_dict(s: Staff) -> dict:
        return {
            "fid": s.fid, "staff_no": s.staff_no,
            "name": s.name, "phone": s.phone,
            "department": s.department, "position": s.position,
            "enterprise_id": s.enterprise_id, "status": s.status,
            "avatar_url": s.avatar_url, "hire_date": s.hire_date,
            "create_time": s.create_time.strftime("%Y-%m-%d %H:%M:%S") if s.create_time else "",
        }
