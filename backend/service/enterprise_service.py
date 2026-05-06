# service/enterprise_service.py - 园区/企业管理业务
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from service.base_service import BaseService
from db.models import Enterprise
from utils.md5_fid_util import generate_fid
from utils.log_util import logger


class EnterpriseService(BaseService):
    """园区/企业管理服务"""

    def list_enterprises(self, fec_id: str, fproject_id: str,
                         keyword: str = "", page: int = 1, page_size: int = 20) -> Dict:
        """获取园区列表"""
        try:
            q = Enterprise.active_query(self.db).filter(
                Enterprise.fec_id == fec_id,
                Enterprise.fproject_id == fproject_id
            )
            if keyword:
                q = q.filter(
                    Enterprise.name.like(f"%{keyword}%") |
                    Enterprise.address.like(f"%{keyword}%")
                )
            total = q.count()
            items = q.order_by(Enterprise.create_time.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()

            return self.success({
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [self._to_dict(e) for e in items]
            })
        except Exception as e:
            logger.error(f"查询园区列表失败：{str(e)}", exc_info=True)
            return self.error(f"查询园区列表失败：{str(e)}")

    def create_enterprise(self, fec_id: str, fproject_id: str,
                          name: str, address: str, type: str = "住宅",
                          contact_person: str = "", contact_phone: str = "",
                          total_area: int = 0, description: str = "") -> Dict:
        """新增园区"""
        try:
            self.begin()
            fid = generate_fid()
            ent = Enterprise(
                fid=fid, fec_id=fec_id, fproject_id=fproject_id,
                name=name, address=address, type=type,
                contact_person=contact_person, contact_phone=contact_phone,
                total_area=total_area, description=description
            )
            self.db.add(ent)
            self.commit()
            self.db.refresh(ent)
            logger.info(f"新增园区成功：fid={fid}, name={name}")
            return self.success(self._to_dict(ent), "新增成功")
        except Exception as e:
            self.rollback()
            logger.error(f"新增园区失败：{str(e)}", exc_info=True)
            return self.error(f"新增园区失败：{str(e)}")

    def update_enterprise(self, fec_id: str, fproject_id: str, fid: str, **kwargs) -> Dict:
        """更新园区信息"""
        try:
            self.begin()
            ent = Enterprise.active_query(self.db).filter(
                Enterprise.fid == fid,
                Enterprise.fec_id == fec_id,
                Enterprise.fproject_id == fproject_id
            ).first()
            if not ent:
                return self.error("园区不存在", 404)

            for key, value in kwargs.items():
                if hasattr(ent, key) and value is not None:
                    setattr(ent, key, value)
            self.commit()
            logger.info(f"更新园区成功：fid={fid}")
            return self.success(self._to_dict(ent), "更新成功")
        except Exception as e:
            self.rollback()
            return self.error(f"更新园区失败：{str(e)}")

    def delete_enterprise(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """软删除园区"""
        try:
            self.begin()
            ent = Enterprise.active_query(self.db).filter(
                Enterprise.fid == fid,
                Enterprise.fec_id == fec_id,
                Enterprise.fproject_id == fproject_id
            ).first()
            if not ent:
                return self.error("园区不存在", 404)

            ent.is_deleted = 1
            ent.delete_time = __import__('utils.time_util', fromlist=['now']).now()
            self.commit()
            return self.success({"fid": fid}, "删除成功")
        except Exception as e:
            self.rollback()
            return self.error(f"删除园区失败：{str(e)}")

    def get_enterprise(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """获取园区详情"""
        try:
            ent = Enterprise.active_query(self.db).filter(
                Enterprise.fid == fid,
                Enterprise.fec_id == fec_id,
                Enterprise.fproject_id == fproject_id
            ).first()
            if not ent:
                return self.error("园区不存在", 404)
            return self.success(self._to_dict(ent))
        except Exception as e:
            return self.error(f"查询园区详情失败：{str(e)}")

    @staticmethod
    def _to_dict(e: Enterprise) -> dict:
        return {
            "fid": e.fid, "fec_id": e.fec_id, "fproject_id": e.fproject_id,
            "name": e.name, "address": e.address, "type": e.type,
            "contact_person": e.contact_person, "contact_phone": e.contact_phone,
            "total_area": e.total_area, "description": e.description,
            "status": e.status,
            "create_time": e.create_time.strftime("%Y-%m-%d %H:%M:%S") if e.create_time else "",
            "update_time": e.update_time.strftime("%Y-%m-%d %H:%M:%S") if e.update_time else ""
        }
