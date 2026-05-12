# service/wo_scheduler_service.py - 智慧工单定时任务服务
"""
定时任务:
1. SLA超期自动检测与升级
2. 模板自动生成周期工单
"""
import json
from typing import Dict, List
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from service.base_service import BaseService
from db.models.smart_work_order import SmartWorkOrder
from db.models.wo_flow import WoReminder
from db.models.wo_rule import WoSlaRule
from db.models.wo_template import WoTemplate
from utils.md5_fid_util import generate_fid
from utils.log_util import logger
from utils.time_util import now, now_str


class WoSchedulerService(BaseService):
    """智慧工单定时任务服务"""

    # ========== SLA超期检测与升级 ==========

    def check_overdue_orders(self, fec_id: str, fproject_id: str) -> Dict:
        """
        扫描所有进行中的工单，检测是否超期:
        - 响应超期: 派单后超过响应时限未接单
        - 完成超期: 接单/开始后超过完成时限未完成
        超期工单标记并触发升级通知
        """
        try:
            active_statuses = ["pending_dispatch", "dispatched", "accepted", "in_progress"]
            orders = SmartWorkOrder.active_query(self.db).filter(
                SmartWorkOrder.fec_id == fec_id,
                SmartWorkOrder.fproject_id == fproject_id,
                SmartWorkOrder.fstatus.in_(active_statuses),
                SmartWorkOrder.fis_overdue == 0
            ).all()

            current = now()
            overdue_count = 0
            escalate_count = 0

            for wo in orders:
                is_overdue = False
                overdue_type = ""
                overdue_minutes = 0

                # 响应超期检测: 派单后超过响应时限
                if wo.fsla_response_deadline and wo.fstatus in ["pending_dispatch", "dispatched"]:
                    if current > wo.fsla_response_deadline:
                        is_overdue = True
                        overdue_type = "response"
                        overdue_minutes = int((current - wo.fsla_response_deadline).total_seconds() / 60)

                # 完成超期检测: 开始后超过完成时限
                if wo.fsla_complete_deadline and wo.fstatus in ["accepted", "in_progress"]:
                    if current > wo.fsla_complete_deadline:
                        is_overdue = True
                        overdue_type = "complete"
                        overdue_minutes = int((current - wo.fsla_complete_deadline).total_seconds() / 60)

                if is_overdue:
                    wo.fis_overdue = 1
                    wo.foverdue_minutes = overdue_minutes
                    wo.foverdue_type = overdue_type
                    overdue_count += 1

                    # 触发升级通知
                    escalated = self._escalate_overdue(wo, overdue_type, overdue_minutes)
                    if escalated:
                        escalate_count += 1

            if overdue_count > 0:
                self.db.commit()
                logger.info(f"SLA超期检测完成: {overdue_count}个超期, {escalate_count}个升级")

            return self.success({
                "checked": len(orders),
                "overdue": overdue_count,
                "escalated": escalate_count,
            })
        except Exception as e:
            self.db.rollback()
            logger.error(f"SLA超期检测失败: {str(e)}", exc_info=True)
            return self.error(f"SLA超期检测失败: {str(e)}")

    def _escalate_overdue(self, wo, overdue_type: str, overdue_minutes: int) -> bool:
        """对超期工单触发升级通知"""
        try:
            # 查询SLA规则获取升级配置
            sla = self.db.query(WoSlaRule).filter(
                WoSlaRule.fec_id == wo.fec_id,
                WoSlaRule.fproject_id == wo.fproject_id,
                WoSlaRule.fpriority == wo.fpriority,
                WoSlaRule.fis_enabled == 1,
                WoSlaRule.is_deleted == 0
            ).first()

            if not sla or not sla.fescalate_minutes:
                return False

            # 检查是否达到升级时间阈值
            if overdue_minutes < sla.fescalate_minutes:
                return False

            # 检查已升级次数
            existing_reminders = self.db.query(WoReminder).filter(
                WoReminder.fwo_id == wo.fid,
                WoReminder.freminder_type == "system",
                WoReminder.is_deleted == 0
            ).count()

            if existing_reminders >= (sla.fescalate_count or 3):
                return False

            # 创建升级催办记录
            reminder = WoReminder(
                fid=generate_fid(),
                fec_id=wo.fec_id,
                fproject_id=wo.fproject_id,
                fwo_id=wo.fid,
                freminder_type="system",
                freminder_channel="system",
                freminder_content=f"工单{wo.fwo_no}已{overdue_type}超期{overdue_minutes}分钟，请及时处理",
                freminder_user_id="system",
                freminder_user_name="系统自动",
                ftarget_user_id=wo.fassignee_id or "",
                ftarget_user_name=wo.fassignee_name or "",
            )
            self.db.add(reminder)

            # 如果配置了升级通知人，也通知
            if sla.fescalate_to:
                escalate_reminder = WoReminder(
                    fid=generate_fid(),
                    fec_id=wo.fec_id,
                    fproject_id=wo.fproject_id,
                    fwo_id=wo.fid,
                    freminder_type="system",
                    freminder_channel="system",
                    freminder_content=f"工单{wo.fwo_no}超期升级通知: 已超期{overdue_minutes}分钟，执行人{wo.fassignee_name or '未指派'}未处理",
                    freminder_user_id="system",
                    freminder_user_name="系统自动",
                    ftarget_user_id=sla.fescalate_to,
                    ftarget_user_name="升级通知人",
                )
                self.db.add(escalate_reminder)

            return True
        except Exception as e:
            logger.warning(f"升级通知创建失败: {str(e)}")
            return False

    # ========== 模板自动生成工单 ==========

    def generate_orders_from_templates(self, fec_id: str, fproject_id: str) -> Dict:
        """
        扫描所有启用的周期模板，按周期自动生成工单。
        每个模板每天最多生成一次。
        """
        try:
            templates = WoTemplate.active_query(self.db).filter(
                WoTemplate.fec_id == fec_id,
                WoTemplate.fproject_id == fproject_id,
                WoTemplate.fstatus == "active",
                WoTemplate.fwo_type.in_(["quality", "equipment", "comprehensive"]),
            ).all()

            current = now()
            generated = 0
            skipped = 0

            for tpl in templates:
                # 检查今天是否已生成
                if not self._should_generate_today(tpl, current):
                    skipped += 1
                    continue

                # 检查执行时间是否已到
                exec_time = tpl.fexec_time or "08:00"
                if current.time() < datetime.strptime(exec_time, "%H:%M").time():
                    skipped += 1
                    continue

                # 生成工单
                from service.smart_work_order_service import SmartWorkOrderService
                wo_svc = SmartWorkOrderService(self.db)

                result = wo_svc.create_work_order(
                    fec_id=fec_id,
                    fproject_id=fproject_id,
                    ftitle=f"[自动] {tpl.ftemplate_name} - {current.strftime('%m-%d')}",
                    fdescription=tpl.fdescription or f"由模板'{tpl.ftemplate_name}'自动生成",
                    fwo_type=tpl.fwo_type,
                    fcategory_id=tpl.fcategory_id or "",
                    fsource="system",
                    fsource_id=tpl.fid,
                    fpriority=tpl.fpriority or "medium",
                    fsla_level=tpl.fsla_level or "L3",
                    ftemplate_id=tpl.fid,
                    fcreate_user_id="system",
                    fcreate_user_name="系统自动",
                )

                if result.get("code") == 200:
                    generated += 1
                    # 更新模板最后生成时间
                    tpl.flast_generate_time = current
                    logger.info(f"模板自动生成工单: {tpl.ftemplate_name} -> {result['data'].get('wo_no', '')}")
                else:
                    logger.warning(f"模板生成工单失败: {tpl.ftemplate_name} - {result.get('message', '')}")

            self.db.commit()
            logger.info(f"模板生成工单完成: 检查{len(templates)}个, 生成{generated}个, 跳过{skipped}个")

            return self.success({
                "checked": len(templates),
                "generated": generated,
                "skipped": skipped,
            })
        except Exception as e:
            self.db.rollback()
            logger.error(f"模板生成工单失败: {str(e)}", exc_info=True)
            return self.error(f"模板生成工单失败: {str(e)}")

    def _should_generate_today(self, tpl: WoTemplate, current: datetime) -> bool:
        """判断模板今天是否应该生成工单"""
        # 如果今天已经生成过，跳过
        if tpl.flast_generate_time and tpl.flast_generate_time.date() == current.date():
            return False

        cycle_type = tpl.fcycle_type or "daily"
        cycle_value = tpl.fcycle_value or 1

        if cycle_type == "daily":
            return True
        elif cycle_type == "weekly":
            if tpl.fcycle_config:
                try:
                    config = json.loads(tpl.fcycle_config)
                    weekdays = config.get("weekdays", [0])
                    return current.weekday() in weekdays
                except (json.JSONDecodeError, TypeError):
                    return current.weekday() == 0
            return current.weekday() == 0
        elif cycle_type == "monthly":
            if tpl.fcycle_config:
                try:
                    config = json.loads(tpl.fcycle_config)
                    days = config.get("days", [1])
                    return current.day in days
                except (json.JSONDecodeError, TypeError):
                    return current.day == 1
            return current.day == 1
        elif cycle_type == "quarterly":
            return current.day == 1 and current.month in [1, 4, 7, 10]
        elif cycle_type == "custom":
            if tpl.flast_generate_time:
                days_since = (current.date() - tpl.flast_generate_time.date()).days
                return days_since >= cycle_value
            return True

        return False
