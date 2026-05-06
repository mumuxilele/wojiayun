# service/work_order_service.py - 工单管理业务
from typing import Dict
from sqlalchemy.orm import Session
from service.base_service import BaseService
from db.models import WorkOrder
from utils.md5_fid_util import generate_fid
from utils.log_util import logger
from utils.time_util import now_str


class WorkOrderService(BaseService):
    """工单管理服务"""

    def list_work_orders(self, fec_id: str, fproject_id: str,
                         status: str = "", level: str = "",
                         keyword: str = "", enterprise_id: str = "",
                         page: int = 1, page_size: int = 20) -> Dict:
        try:
            q = WorkOrder.active_query(self.db).filter(
                WorkOrder.fec_id == fec_id,
                WorkOrder.fproject_id == fproject_id
            )
            if status:
                q = q.filter(WorkOrder.status == status)
            if level:
                q = q.filter(WorkOrder.level == level)
            if enterprise_id:
                q = q.filter(WorkOrder.enterprise_id == enterprise_id)
            if keyword:
                q = q.filter(
                    WorkOrder.order_no.like(f"%{keyword}%") |
                    WorkOrder.title.like(f"%{keyword}%")
                )
            total = q.count()
            items = q.order_by(WorkOrder.create_time.desc()) \
                .offset((page - 1) * page_size).limit(page_size).all()
            return self.success({
                "total": total, "page": page, "page_size": page_size,
                "items": [self._to_dict(w) for w in items]
            })
        except Exception as e:
            logger.error(f"查询工单列表失败：{str(e)}", exc_info=True)
            return self.error(f"查询工单列表失败：{str(e)}")

    def create_work_order(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        try:
            self.begin()
            fid = generate_fid()
            order_no = f"WO{now_str().replace('-','').replace(':','').replace(' ','')[:12]}"
            wo = WorkOrder(fid=fid, fec_id=fec_id, fproject_id=fproject_id,
                           order_no=order_no, **kwargs)
            self.db.add(wo)
            self.commit()
            self.db.refresh(wo)
            logger.info(f"创建工单成功：order_no={order_no}")
            return self.success(self._to_dict(wo), "创建成功")
        except Exception as e:
            self.rollback()
            return self.error(f"创建工单失败：{str(e)}")

    def assign_work_order(self, fec_id: str, fproject_id: str,
                          fid: str, assignee_id: str, assignee_name: str) -> Dict:
        """派单"""
        try:
            self.begin()
            wo = WorkOrder.active_query(self.db).filter(
                WorkOrder.fid == fid, WorkOrder.fec_id == fec_id,
                WorkOrder.fproject_id == fproject_id
            ).first()
            if not wo:
                return self.error("工单不存在", 404)
            wo.assignee_id = assignee_id
            wo.assignee_name = assignee_name
            wo.status = "处理中"
            self.commit()
            return self.success(self._to_dict(wo), "派单成功")
        except Exception as e:
            self.rollback()
            return self.error(f"派单失败：{str(e)}")

    def complete_work_order(self, fec_id: str, fproject_id: str,
                            fid: str, rating: int = 5) -> Dict:
        """完成工单"""
        try:
            self.begin()
            wo = WorkOrder.active_query(self.db).filter(
                WorkOrder.fid == fid, WorkOrder.fec_id == fec_id,
                WorkOrder.fproject_id == fproject_id
            ).first()
            if not wo:
                return self.error("工单不存在", 404)
            wo.status = "已完成"
            wo.completed_at = now_str()
            wo.rating = rating
            self.commit()
            return self.success(self._to_dict(wo), "完成成功")
        except Exception as e:
            self.rollback()
            return self.error(f"完成工单失败：{str(e)}")

    def get_work_order(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        try:
            wo = WorkOrder.active_query(self.db).filter(
                WorkOrder.fid == fid, WorkOrder.fec_id == fec_id,
                WorkOrder.fproject_id == fproject_id
            ).first()
            if not wo:
                return self.error("工单不存在", 404)
            return self.success(self._to_dict(wo))
        except Exception as e:
            return self.error(f"查询工单详情失败：{str(e)}")

    @staticmethod
    def _to_dict(w: WorkOrder) -> dict:
        return {
            "fid": w.fid, "order_no": w.order_no,
            "enterprise_id": w.enterprise_id, "building_id": w.building_id,
            "room_number": w.room_number, "type": w.type,
            "title": w.title, "description": w.description,
            "level": w.level, "status": w.status,
            "reporter_name": w.reporter_name, "reporter_phone": w.reporter_phone,
            "assignee_id": w.assignee_id, "assignee_name": w.assignee_name,
            "completed_at": w.completed_at, "rating": w.rating,
            "create_time": w.create_time.strftime("%Y-%m-%d %H:%M:%S") if w.create_time else "",
        }
