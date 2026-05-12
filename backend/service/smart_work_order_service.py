# service/smart_work_order_service.py - 智慧工单核心业务服务
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from service.base_service import BaseService
from db.models.smart_work_order import SmartWorkOrder
from db.models.wo_flow import WoFlowInstance, WoOperationLog, WoCheckRecord, WoReminder
from db.models.wo_rule import WoCategory, WoSlaRule, WoDispatchRule
from utils.md5_fid_util import generate_fid
from utils.log_util import logger
from utils.time_util import now, now_str


class SmartWorkOrderService(BaseService):
    """智慧工单核心服务"""

    # ========== 工单编号生成 ==========
    WO_TYPE_PREFIX = {
        "quality": "QI",       # 品质检查
        "equipment": "EQ",     # 设备巡查
        "comprehensive": "CI", # 综合巡查
        "repair": "RP",        # 报事报修
        "other": "OT",         # 其他
    }

    def _generate_wo_no(self, wo_type: str) -> str:
        """生成工单编号: 前缀 + 日期 + 4位序号"""
        prefix = self.WO_TYPE_PREFIX.get(wo_type, "WO")
        date_str = now().strftime("%Y%m%d")
        # 查询当天同类型最大序号
        like_pattern = f"{prefix}{date_str}%"
        max_no = self.db.query(func.max(SmartWorkOrder.fwo_no)).filter(
            SmartWorkOrder.fwo_no.like(like_pattern),
            SmartWorkOrder.is_deleted == 0
        ).scalar()
        seq = 1
        if max_no:
            try:
                seq = int(max_no[-4:]) + 1
            except (ValueError, IndexError):
                seq = 1
        return f"{prefix}{date_str}{seq:04d}"

    # ========== 工单 CRUD ==========

    def list_work_orders(
        self, fec_id: str, fproject_id: str,
        status: str = "", wo_type: str = "", category_id: str = "",
        priority: str = "", keyword: str = "", source: str = "",
        assignee_id: str = "", is_overdue: int = -1,
        start_date: str = "", end_date: str = "",
        page: int = 1, page_size: int = 20
    ) -> Dict:
        """获取工单列表(分页)"""
        try:
            q = SmartWorkOrder.active_query(self.db).filter(
                SmartWorkOrder.fec_id == fec_id,
                SmartWorkOrder.fproject_id == fproject_id
            )
            if status:
                q = q.filter(SmartWorkOrder.fstatus == status)
            if wo_type:
                q = q.filter(SmartWorkOrder.fwo_type == wo_type)
            if category_id:
                q = q.filter(SmartWorkOrder.fcategory_id == category_id)
            if priority:
                q = q.filter(SmartWorkOrder.fpriority == priority)
            if source:
                q = q.filter(SmartWorkOrder.fsource == source)
            if assignee_id:
                q = q.filter(SmartWorkOrder.fassignee_id == assignee_id)
            if is_overdue >= 0:
                q = q.filter(SmartWorkOrder.fis_overdue == is_overdue)
            if start_date:
                q = q.filter(SmartWorkOrder.create_time >= start_date)
            if end_date:
                q = q.filter(SmartWorkOrder.create_time <= end_date + " 23:59:59")
            if keyword:
                q = q.filter(
                    or_(
                        SmartWorkOrder.fwo_no.like(f"%{keyword}%"),
                        SmartWorkOrder.ftitle.like(f"%{keyword}%"),
                        SmartWorkOrder.fdescription.like(f"%{keyword}%"),
                    )
                )
            q = q.order_by(SmartWorkOrder.create_time.desc())
            total = q.count()
            items = q.offset((page - 1) * page_size).limit(page_size).all()
            return self.success({
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [self._to_dict(wo) for wo in items]
            })
        except Exception as e:
            logger.error(f"查询工单列表失败: {str(e)}", exc_info=True)
            return self.error(f"查询工单列表失败: {str(e)}")

    def get_work_order(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """获取工单详情"""
        try:
            wo = SmartWorkOrder.active_query(self.db).filter(
                SmartWorkOrder.fid == fid,
                SmartWorkOrder.fec_id == fec_id,
                SmartWorkOrder.fproject_id == fproject_id
            ).first()
            if not wo:
                return self.error("工单不存在", 404)
            data = self._to_dict(wo)
            # 附带流转记录
            data["flow_records"] = self._get_flow_records(fid)
            # 附带操作日志
            data["operation_logs"] = self._get_operation_logs(fid)
            # 附带检查记录
            data["check_records"] = self._get_check_records(fid)
            return self.success(data)
        except Exception as e:
            logger.error(f"查询工单详情失败: {str(e)}", exc_info=True)
            return self.error(f"查询工单详情失败: {str(e)}")

    def create_work_order(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        """创建工单"""
        try:
            self.begin()
            wo_type = kwargs.get("fwo_type", "repair")
            wo_no = self._generate_wo_no(wo_type)

            # 获取SLA规则
            priority = kwargs.get("fpriority", "medium")
            sla = self._get_sla_rule(fec_id, fproject_id, priority)

            wo = SmartWorkOrder(
                fid=generate_fid(),
                fec_id=fec_id,
                fproject_id=fproject_id,
                fwo_no=wo_no,
                ftitle=kwargs.get("ftitle", ""),
                fdescription=kwargs.get("fdescription", ""),
                fcategory_id=kwargs.get("fcategory_id", ""),
                fwo_type=wo_type,
                fsub_type=kwargs.get("fsub_type", ""),
                fsource=kwargs.get("fsource", "manual"),
                fsource_id=kwargs.get("fsource_id", ""),
                flocation_type=kwargs.get("flocation_type", "building"),
                fbuilding_id=kwargs.get("fbuilding_id", ""),
                ffloor=kwargs.get("ffloor", ""),
                froom_number=kwargs.get("froom_number", ""),
                fequipment_id=kwargs.get("fequipment_id", ""),
                flocation_detail=kwargs.get("flocation_detail", ""),
                fpriority=priority,
                fsla_level=sla["sla_level"] if sla else "L3",
                fstatus="pending_dispatch",
                ftemplate_id=kwargs.get("ftemplate_id", ""),
                fcontact_name=kwargs.get("fcontact_name", ""),
                fcontact_phone=kwargs.get("fcontact_phone", ""),
                fimage_urls=json.dumps(kwargs.get("fimage_urls", []), ensure_ascii=False),
                fvideo_urls=json.dumps(kwargs.get("fvideo_urls", []), ensure_ascii=False),
                fattachment_urls=json.dumps(kwargs.get("fattachment_urls", []), ensure_ascii=False),
                fextra_data=json.dumps(kwargs.get("fextra_data", {}), ensure_ascii=False) if kwargs.get("fextra_data") else None,
                fremark=kwargs.get("fremark", ""),
                fcreate_user_id=kwargs.get("fcreate_user_id", ""),
            )

            # 计算SLA截止时间
            if sla:
                wo.fsla_response_deadline = now() + timedelta(minutes=sla["response_minutes"])
                wo.fsla_complete_deadline = now() + timedelta(hours=sla["complete_hours"])

            self.db.add(wo)

            # 记录流转
            self._add_flow_instance(fec_id, fproject_id, wo.fid,
                                    from_node=None, to_node="pending_dispatch",
                                    from_status=None, to_status="pending_dispatch",
                                    operator_id=kwargs.get("fcreate_user_id", ""),
                                    operator_name=kwargs.get("fcreate_user_name", ""),
                                    action="create", opinion="创建工单")

            # 记录操作日志
            self._add_operation_log(fec_id, fproject_id, wo.fid,
                                    operator_id=kwargs.get("fcreate_user_id", ""),
                                    operator_name=kwargs.get("fcreate_user_name", ""),
                                    action="create", detail=f"创建工单: {wo_no}")

            self.commit()
            logger.info(f"创建工单成功: {wo_no}")
            return self.success(self._to_dict(wo), message="工单创建成功")
        except Exception as e:
            self.rollback()
            logger.error(f"创建工单失败: {str(e)}", exc_info=True)
            return self.error(f"创建工单失败: {str(e)}")

    def dispatch_work_order(self, fec_id: str, fproject_id: str, fid: str,
                            assignee_id: str, assignee_name: str,
                            operator_id: str = "", operator_name: str = "",
                            opinion: str = "", dispatch_type: str = "manual") -> Dict:
        """派单"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            if wo.fstatus != "pending_dispatch":
                return self.error(f"当前状态({wo.fstatus})不允许派单")

            self.begin()
            wo.fstatus = "dispatched"
            wo.fassignee_id = assignee_id
            wo.fassignee_name = assignee_name
            wo.fdispatch_type = dispatch_type
            wo.fdispatched_at = now()

            self._add_flow_instance(fec_id, fproject_id, fid,
                                    from_node="pending_dispatch", to_node="dispatched",
                                    from_status="pending_dispatch", to_status="dispatched",
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="dispatch", opinion=opinion or f"派单给 {assignee_name}")
            self._add_operation_log(fec_id, fproject_id, fid,
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="dispatch", detail=f"派单给 {assignee_name}")

            self.commit()
            return self.success(self._to_dict(wo), message="派单成功")
        except Exception as e:
            self.rollback()
            logger.error(f"派单失败: {str(e)}", exc_info=True)
            return self.error(f"派单失败: {str(e)}")

    def accept_work_order(self, fec_id: str, fproject_id: str, fid: str,
                          operator_id: str, operator_name: str) -> Dict:
        """接收工单"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            if wo.fstatus != "dispatched":
                return self.error(f"当前状态({wo.fstatus})不允许接收")

            self.begin()
            wo.fstatus = "accepted"
            wo.faccepted_at = now()

            self._add_flow_instance(fec_id, fproject_id, fid,
                                    from_node="dispatched", to_node="accepted",
                                    from_status="dispatched", to_status="accepted",
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="accept", opinion="接收工单")
            self._add_operation_log(fec_id, fproject_id, fid,
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="accept", detail="接收工单")

            self.commit()
            return self.success(self._to_dict(wo), message="接收成功")
        except Exception as e:
            self.rollback()
            logger.error(f"接收工单失败: {str(e)}", exc_info=True)
            return self.error(f"接收工单失败: {str(e)}")

    def start_work_order(self, fec_id: str, fproject_id: str, fid: str,
                         operator_id: str, operator_name: str) -> Dict:
        """开始执行"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            if wo.fstatus not in ("accepted", "dispatched"):
                return self.error(f"当前状态({wo.fstatus})不允许开始执行")

            self.begin()
            wo.fstatus = "in_progress"
            wo.factual_start_time = now()

            self._add_flow_instance(fec_id, fproject_id, fid,
                                    from_node=wo.fstatus, to_node="in_progress",
                                    from_status=wo.fstatus, to_status="in_progress",
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="start", opinion="开始执行")
            self._add_operation_log(fec_id, fproject_id, fid,
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="start", detail="开始执行工单")

            self.commit()
            return self.success(self._to_dict(wo), message="开始执行")
        except Exception as e:
            self.rollback()
            logger.error(f"开始执行失败: {str(e)}", exc_info=True)
            return self.error(f"开始执行失败: {str(e)}")

    def complete_work_order(self, fec_id: str, fproject_id: str, fid: str,
                            result_summary: str = "", image_urls: List = None,
                            operator_id: str = "", operator_name: str = "") -> Dict:
        """完成工单"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            if wo.fstatus != "in_progress":
                return self.error(f"当前状态({wo.fstatus})不允许完成")

            self.begin()
            wo.fstatus = "completed"
            wo.factual_end_time = now()
            wo.fresult_summary = result_summary
            if image_urls:
                wo.fimage_urls = json.dumps(image_urls, ensure_ascii=False)

            # 检查是否超期（统一用 naive datetime 比较）
            _now = datetime.now()
            _deadline = wo.fsla_complete_deadline.replace(tzinfo=None) if wo.fsla_complete_deadline.tzinfo else wo.fsla_complete_deadline
            if _deadline and _now > _deadline:
                wo.fis_overdue = 1
                wo.foverdue_minutes = int((_now - _deadline).total_seconds() / 60)
                wo.foverdue_type = "complete"

            self._add_flow_instance(fec_id, fproject_id, fid,
                                    from_node="in_progress", to_node="completed",
                                    from_status="in_progress", to_status="completed",
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="complete", opinion=result_summary)
            self._add_operation_log(fec_id, fproject_id, fid,
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="complete", detail=f"完成工单: {result_summary}")

            self.commit()
            return self.success(self._to_dict(wo), message="工单完成")
        except Exception as e:
            self.rollback()
            logger.error(f"完成工单失败: {str(e)}", exc_info=True)
            return self.error(f"完成工单失败: {str(e)}")

    def review_work_order(self, fec_id: str, fproject_id: str, fid: str,
                          review_result: str, review_opinion: str = "",
                          reviewer_id: str = "", reviewer_name: str = "") -> Dict:
        """审核工单"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            if wo.fstatus != "completed":
                return self.error(f"当前状态({wo.fstatus})不允许审核")

            self.begin()
            if review_result == "pass":
                wo.fstatus = "closed"
                wo.freview_result = "pass"
                wo.freviewed_at = now()
                wo.fclosed_at = now()
                target_node = "closed"
                target_status = "closed"
                action = "approve"
                msg = "审核通过，工单关闭"
            elif review_result == "reject":
                wo.fstatus = "in_progress"
                wo.freview_result = "reject"
                wo.freviewed_at = now()
                wo.factual_end_time = None
                target_node = "in_progress"
                target_status = "in_progress"
                action = "reject"
                msg = f"审核驳回: {review_opinion}"
            else:
                return self.error("审核结果无效，应为 pass 或 reject")

            wo.freviewer_id = reviewer_id
            wo.freviewer_name = reviewer_name
            wo.freview_opinion = review_opinion

            self._add_flow_instance(fec_id, fproject_id, fid,
                                    from_node="completed", to_node=target_node,
                                    from_status="completed", to_status=target_status,
                                    operator_id=reviewer_id, operator_name=reviewer_name,
                                    action=action, opinion=review_opinion)
            self._add_operation_log(fec_id, fproject_id, fid,
                                    operator_id=reviewer_id, operator_name=reviewer_name,
                                    action=action, detail=msg)

            self.commit()
            return self.success(self._to_dict(wo), message=msg)
        except Exception as e:
            self.rollback()
            logger.error(f"审核工单失败: {str(e)}", exc_info=True)
            return self.error(f"审核工单失败: {str(e)}")

    def cancel_work_order(self, fec_id: str, fproject_id: str, fid: str,
                          reason: str = "", operator_id: str = "", operator_name: str = "") -> Dict:
        """取消工单"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            if wo.fstatus in ("closed", "cancelled"):
                return self.error(f"当前状态({wo.fstatus})不允许取消")

            self.begin()
            old_status = wo.fstatus
            wo.fstatus = "cancelled"
            wo.fclosed_at = now()

            self._add_flow_instance(fec_id, fproject_id, fid,
                                    from_node=old_status, to_node="cancelled",
                                    from_status=old_status, to_status="cancelled",
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="cancel", opinion=reason)
            self._add_operation_log(fec_id, fproject_id, fid,
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="cancel", detail=f"取消工单: {reason}")

            self.commit()
            return self.success(self._to_dict(wo), message="工单已取消")
        except Exception as e:
            self.rollback()
            logger.error(f"取消工单失败: {str(e)}", exc_info=True)
            return self.error(f"取消工单失败: {str(e)}")

    def evaluate_work_order(self, fec_id: str, fproject_id: str, fid: str,
                            score: int, content: str = "",
                            evaluator_id: str = "", evaluator_name: str = "") -> Dict:
        """评价工单"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            if wo.fstatus != "closed":
                return self.error("只有已关闭的工单才能评价")

            self.begin()
            wo.fevaluation_score = max(1, min(5, score))
            wo.fevaluation_content = content
            wo.fevaluated_at = now()

            self._add_operation_log(fec_id, fproject_id, fid,
                                    operator_id=evaluator_id, operator_name=evaluator_name,
                                    action="evaluate", detail=f"评价工单: {score}分")

            self.commit()
            return self.success(self._to_dict(wo), message="评价成功")
        except Exception as e:
            self.rollback()
            logger.error(f"评价工单失败: {str(e)}", exc_info=True)
            return self.error(f"评价工单失败: {str(e)}")

    def transfer_work_order(self, fec_id: str, fproject_id: str, fid: str,
                            target_assignee_id: str, target_assignee_name: str,
                            reason: str = "", operator_id: str = "", operator_name: str = "") -> Dict:
        """转单"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            if wo.fstatus not in ("dispatched", "accepted", "in_progress"):
                return self.error(f"当前状态({wo.fstatus})不允许转单")

            self.begin()
            old_assignee = wo.fassignee_name
            wo.fassignee_id = target_assignee_id
            wo.fassignee_name = target_assignee_name

            self._add_flow_instance(fec_id, fproject_id, fid,
                                    from_node=wo.fstatus, to_node=wo.fstatus,
                                    from_status=wo.fstatus, to_status=wo.fstatus,
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="transfer", opinion=f"从 {old_assignee} 转给 {target_assignee_name}: {reason}")
            self._add_operation_log(fec_id, fproject_id, fid,
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="transfer", detail=f"转单: {old_assignee} → {target_assignee_name}")

            self.commit()
            return self.success(self._to_dict(wo), message="转单成功")
        except Exception as e:
            self.rollback()
            logger.error(f"转单失败: {str(e)}", exc_info=True)
            return self.error(f"转单失败: {str(e)}")

    def remind_work_order(self, fec_id: str, fproject_id: str, fid: str,
                          content: str = "", reminder_user_id: str = "",
                          reminder_user_name: str = "") -> Dict:
        """催办"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            if wo.fstatus not in ("dispatched", "accepted", "in_progress"):
                return self.error(f"当前状态({wo.fstatus})不允许催办")
            if not wo.fassignee_id:
                return self.error("工单未派单，无法催办")

            self.begin()
            reminder = WoReminder(
                fid=generate_fid(),
                fec_id=fec_id,
                fproject_id=fproject_id,
                fwo_id=fid,
                freminder_type="manual",
                freminder_channel="system",
                freminder_content=content or "请尽快处理此工单",
                freminder_user_id=reminder_user_id,
                freminder_user_name=reminder_user_name,
                ftarget_user_id=wo.fassignee_id,
                ftarget_user_name=wo.fassignee_name,
            )
            self.db.add(reminder)

            self._add_operation_log(fec_id, fproject_id, fid,
                                    operator_id=reminder_user_id, operator_name=reminder_user_name,
                                    action="remind", detail=f"催办 {wo.fassignee_name}: {content}")

            self.commit()
            return self.success(message="催办成功")
        except Exception as e:
            self.rollback()
            logger.error(f"催办失败: {str(e)}", exc_info=True)
            return self.error(f"催办失败: {str(e)}")

    # ========== 统计 ==========

    def get_statistics(self, fec_id: str, fproject_id: str) -> Dict:
        """工单统计"""
        try:
            base = SmartWorkOrder.active_query(self.db).filter(
                SmartWorkOrder.fec_id == fec_id,
                SmartWorkOrder.fproject_id == fproject_id
            )
            total = base.count()
            pending = base.filter(SmartWorkOrder.fstatus == "pending_dispatch").count()
            in_progress = base.filter(SmartWorkOrder.fstatus.in_(["dispatched", "accepted", "in_progress"])).count()
            completed = base.filter(SmartWorkOrder.fstatus == "completed").count()
            closed = base.filter(SmartWorkOrder.fstatus == "closed").count()
            overdue = base.filter(SmartWorkOrder.fis_overdue == 1).count()
            cancelled = base.filter(SmartWorkOrder.fstatus == "cancelled").count()

            # 按类型统计
            type_stats = self.db.query(
                SmartWorkOrder.fwo_type,
                func.count(SmartWorkOrder.fid)
            ).filter(
                SmartWorkOrder.fec_id == fec_id,
                SmartWorkOrder.fproject_id == fproject_id,
                SmartWorkOrder.is_deleted == 0
            ).group_by(SmartWorkOrder.fwo_type).all()

            # 按优先级统计
            priority_stats = self.db.query(
                SmartWorkOrder.fpriority,
                func.count(SmartWorkOrder.fid)
            ).filter(
                SmartWorkOrder.fec_id == fec_id,
                SmartWorkOrder.fproject_id == fproject_id,
                SmartWorkOrder.is_deleted == 0
            ).group_by(SmartWorkOrder.fpriority).all()

            return self.success({
                "total": total,
                "pending_dispatch": pending,
                "in_progress": in_progress,
                "completed": completed,
                "closed": closed,
                "overdue": overdue,
                "cancelled": cancelled,
                "completion_rate": round(closed / total * 100, 1) if total > 0 else 0,
                "overdue_rate": round(overdue / total * 100, 1) if total > 0 else 0,
                "by_type": {t: c for t, c in type_stats},
                "by_priority": {p: c for p, c in priority_stats},
            })
        except Exception as e:
            logger.error(f"工单统计失败: {str(e)}", exc_info=True)
            return self.error(f"工单统计失败: {str(e)}")

    # ========== 检查记录 ==========

    def save_check_records(self, fec_id: str, fproject_id: str, fwo_id: str,
                           records: List[Dict], operator_id: str = "",
                           operator_name: str = "") -> Dict:
        """保存检查记录"""
        try:
            self.begin()
            for r in records:
                cr = WoCheckRecord(
                    fid=generate_fid(),
                    fec_id=fec_id,
                    fproject_id=fproject_id,
                    fwo_id=fwo_id,
                    ftemplate_item_id=r.get("ftemplate_item_id", ""),
                    fitem_name=r.get("fitem_name", ""),
                    fitem_type=r.get("fitem_type", "check"),
                    fcheck_result=r.get("fcheck_result", "pass"),
                    fscore=r.get("fscore"),
                    fcheck_value=r.get("fcheck_value", ""),
                    fphoto_urls=json.dumps(r.get("fphoto_urls", []), ensure_ascii=False),
                    fremark=r.get("fremark", ""),
                    finspector_id=operator_id,
                    finspector_name=operator_name,
                    fcheck_time=now(),
                )
                self.db.add(cr)

            self._add_operation_log(fec_id, fproject_id, fwo_id,
                                    operator_id=operator_id, operator_name=operator_name,
                                    action="check", detail=f"提交检查记录 {len(records)} 项")
            self.commit()
            return self.success(message="检查记录保存成功")
        except Exception as e:
            self.rollback()
            logger.error(f"保存检查记录失败: {str(e)}", exc_info=True)
            return self.error(f"保存检查记录失败: {str(e)}")

    # ========== 内部方法 ==========

    def _get_active_order(self, fec_id: str, fproject_id: str, fid: str):
        return SmartWorkOrder.active_query(self.db).filter(
            SmartWorkOrder.fid == fid,
            SmartWorkOrder.fec_id == fec_id,
            SmartWorkOrder.fproject_id == fproject_id
        ).first()

    def _get_sla_rule(self, fec_id: str, fproject_id: str, priority: str) -> Optional[Dict]:
        """获取SLA规则"""
        rule = self.db.query(WoSlaRule).filter(
            WoSlaRule.fec_id == fec_id,
            WoSlaRule.fproject_id == fproject_id,
            WoSlaRule.fpriority == priority,
            WoSlaRule.fis_enabled == 1,
            WoSlaRule.is_deleted == 0
        ).first()
        if rule:
            return {
                "sla_level": rule.fsla_level,
                "response_minutes": rule.fresponse_minutes,
                "complete_hours": rule.fcomplete_hours,
            }
        # 默认SLA
        defaults = {"urgent": ("L1", 15, 2), "high": ("L2", 30, 4),
                     "medium": ("L3", 60, 8), "low": ("L4", 120, 24)}
        if priority in defaults:
            return {"sla_level": defaults[priority][0],
                    "response_minutes": defaults[priority][1],
                    "complete_hours": defaults[priority][2]}
        return {"sla_level": "L3", "response_minutes": 60, "complete_hours": 8}

    def _add_flow_instance(self, fec_id, fproject_id, fwo_id,
                           from_node, to_node, from_status, to_status,
                           operator_id, operator_name, action, opinion):
        fi = WoFlowInstance(
            fid=generate_fid(), fec_id=fec_id, fproject_id=fproject_id,
            fwo_id=fwo_id, ffrom_node=from_node, fto_node=to_node,
            ffrom_status=from_status, fto_status=to_status,
            foperator_id=operator_id, foperator_name=operator_name,
            faction=action, fopinion=opinion,
        )
        self.db.add(fi)

    def _add_operation_log(self, fec_id, fproject_id, fwo_id,
                           operator_id, operator_name, action, detail,
                           operator_type="admin", extra_data=None):
        log = WoOperationLog(
            fid=generate_fid(), fec_id=fec_id, fproject_id=fproject_id,
            fwo_id=fwo_id, foperator_id=operator_id, foperator_name=operator_name,
            foperator_type=operator_type, faction=action, fdetail=detail,
            fextra_data=json.dumps(extra_data, ensure_ascii=False) if extra_data else None,
        )
        self.db.add(log)

    def _get_flow_records(self, fwo_id: str) -> List[Dict]:
        records = self.db.query(WoFlowInstance).filter(
            WoFlowInstance.fwo_id == fwo_id,
            WoFlowInstance.is_deleted == 0
        ).order_by(WoFlowInstance.create_time.asc()).all()
        return [{
            "fid": r.fid, "from_node": r.ffrom_node, "to_node": r.fto_node,
            "from_status": r.ffrom_status, "to_status": r.fto_status,
            "operator_name": r.foperator_name, "action": r.faction,
            "opinion": r.fopinion, "create_time": r.create_time.strftime("%Y-%m-%d %H:%M:%S") if r.create_time else "",
        } for r in records]

    def _get_operation_logs(self, fwo_id: str) -> List[Dict]:
        logs = self.db.query(WoOperationLog).filter(
            WoOperationLog.fwo_id == fwo_id,
            WoOperationLog.is_deleted == 0
        ).order_by(WoOperationLog.create_time.desc()).all()
        return [{
            "fid": l.fid, "operator_name": l.foperator_name,
            "action": l.faction, "detail": l.fdetail,
            "create_time": l.create_time.strftime("%Y-%m-%d %H:%M:%S") if l.create_time else "",
        } for l in logs]

    def _get_check_records(self, fwo_id: str) -> List[Dict]:
        records = self.db.query(WoCheckRecord).filter(
            WoCheckRecord.fwo_id == fwo_id,
            WoCheckRecord.is_deleted == 0
        ).order_by(WoCheckRecord.create_time.asc()).all()
        return [{
            "fid": r.fid, "item_name": r.fitem_name, "check_result": r.fcheck_result,
            "score": r.fscore, "remark": r.fremark,
            "photo_urls": json.loads(r.fphoto_urls) if r.fphoto_urls else [],
            "inspector_name": r.finspector_name,
            "check_time": r.fcheck_time.strftime("%Y-%m-%d %H:%M:%S") if r.fcheck_time else "",
        } for r in records]

    # ========== 公开查询接口 ==========

    def get_operation_logs(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """获取工单操作日志"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            return self.success(self._get_operation_logs(fid))
        except Exception as e:
            logger.error(f"查询操作日志失败: {str(e)}", exc_info=True)
            return self.error(f"查询操作日志失败: {str(e)}")

    def get_flow_instances(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """获取工单流转记录"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            return self.success(self._get_flow_records(fid))
        except Exception as e:
            logger.error(f"查询流转记录失败: {str(e)}", exc_info=True)
            return self.error(f"查询流转记录失败: {str(e)}")

    def get_check_records(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """获取工单检查记录"""
        try:
            wo = self._get_active_order(fec_id, fproject_id, fid)
            if not wo:
                return self.error("工单不存在", 404)
            return self.success(self._get_check_records(fid))
        except Exception as e:
            logger.error(f"查询检查记录失败: {str(e)}", exc_info=True)
            return self.error(f"查询检查记录失败: {str(e)}")

    @staticmethod
    def _to_dict(wo: SmartWorkOrder) -> dict:
        return {
            "fid": wo.fid, "wo_no": wo.fwo_no, "title": wo.ftitle,
            "description": wo.fdescription,
            "category_id": wo.fcategory_id, "wo_type": wo.fwo_type, "sub_type": wo.fsub_type,
            "source": wo.fsource, "source_id": wo.fsource_id,
            "location_type": wo.flocation_type, "building_id": wo.fbuilding_id,
            "floor": wo.ffloor, "room_number": wo.froom_number,
            "equipment_id": wo.fequipment_id, "location_detail": wo.flocation_detail,
            "priority": wo.fpriority, "sla_level": wo.fsla_level,
            "status": wo.fstatus,
            "contact_name": wo.fcontact_name, "contact_phone": wo.fcontact_phone,
            "template_id": wo.ftemplate_id,
            "reporter_id": wo.freporter_id, "reporter_name": wo.freporter_name,
            "assignee_id": wo.fassignee_id, "assignee_name": wo.fassignee_name,
            "dispatch_type": wo.fdispatch_type,
            "sla_response_deadline": wo.fsla_response_deadline.strftime("%Y-%m-%d %H:%M:%S") if wo.fsla_response_deadline else "",
            "sla_complete_deadline": wo.fsla_complete_deadline.strftime("%Y-%m-%d %H:%M:%S") if wo.fsla_complete_deadline else "",
            "dispatched_at": wo.fdispatched_at.strftime("%Y-%m-%d %H:%M:%S") if wo.fdispatched_at else "",
            "accepted_at": wo.faccepted_at.strftime("%Y-%m-%d %H:%M:%S") if wo.faccepted_at else "",
            "actual_start_time": wo.factual_start_time.strftime("%Y-%m-%d %H:%M:%S") if wo.factual_start_time else "",
            "actual_end_time": wo.factual_end_time.strftime("%Y-%m-%d %H:%M:%S") if wo.factual_end_time else "",
            "result_summary": wo.fresult_summary,
            "reviewer_name": wo.freviewer_name, "review_result": wo.freview_result,
            "review_opinion": wo.freview_opinion,
            "evaluation_score": wo.fevaluation_score, "evaluation_content": wo.fevaluation_content,
            "is_overdue": wo.fis_overdue, "overdue_minutes": wo.foverdue_minutes,
            "image_urls": json.loads(wo.fimage_urls) if wo.fimage_urls else [],
            "create_time": wo.create_time.strftime("%Y-%m-%d %H:%M:%S") if wo.create_time else "",
            "update_time": wo.update_time.strftime("%Y-%m-%d %H:%M:%S") if wo.update_time else "",
        }
