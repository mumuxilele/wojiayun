# api/smart_work_order_routes.py - 智慧工单API路由
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from config.db_config import get_db
from service.smart_work_order_service import SmartWorkOrderService
from service.wo_template_service import WoTemplateService
from service.wo_rule_service import WoRuleService

router = APIRouter(prefix="/api/smart-wo", tags=["智慧工单"])

FEC_ID = "default_fec"
FPROJECT_ID = "default_project"


# ========== 认证中间件 ==========

async def get_current_user(request: Request):
    """
    从请求中提取当前用户信息。
    支持 access_token (query/header) 或 Authorization Bearer。
    开发模式下如果无 token 则返回默认用户。
    """
    token = (
        request.query_params.get("access_token")
        or request.headers.get("access_token")
        or request.headers.get("Authorization", "").replace("Bearer ", "")
    )
    if token:
        try:
            from utils.auth_util import get_user_from_token
            user = get_user_from_token(token)
            if user:
                return user
        except Exception:
            pass
    # 开发模式：无 token 时返回默认用户
    return {
        "user_id": "dev_admin",
        "username": "开发管理员",
        "fec_id": FEC_ID,
        "fproject_id": FPROJECT_ID,
        "role_ids": ["admin"]
    }


# ========== 工单管理 ==========

@router.get("/orders", summary="获取工单列表")
def list_orders(
    status: str = Query(default=""),
    wo_type: str = Query(default=""),
    category_id: str = Query(default=""),
    priority: str = Query(default=""),
    keyword: str = Query(default=""),
    source: str = Query(default=""),
    assignee_id: str = Query(default=""),
    is_overdue: int = Query(default=-1),
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    svc = SmartWorkOrderService(db)
    return svc.list_work_orders(FEC_ID, FPROJECT_ID, status, wo_type, category_id,
                                priority, keyword, source, assignee_id, is_overdue,
                                start_date, end_date, page, page_size)


@router.get("/orders/{fid}", summary="获取工单详情")
def get_order(fid: str, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.get_work_order(FEC_ID, FPROJECT_ID, fid)


@router.post("/orders", summary="创建工单")
def create_order(body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.create_work_order(FEC_ID, FPROJECT_ID, **body)


@router.post("/orders/{fid}/dispatch", summary="派单")
def dispatch_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.dispatch_work_order(FEC_ID, FPROJECT_ID, fid,
                                   body.get("assignee_id", ""),
                                   body.get("assignee_name", ""),
                                   body.get("operator_id", ""),
                                   body.get("operator_name", ""),
                                   body.get("opinion", ""),
                                   body.get("dispatch_type", "manual"))


@router.post("/orders/{fid}/accept", summary="接收工单")
def accept_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.accept_work_order(FEC_ID, FPROJECT_ID, fid,
                                 body.get("operator_id", ""),
                                 body.get("operator_name", ""))


@router.post("/orders/{fid}/start", summary="开始执行")
def start_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.start_work_order(FEC_ID, FPROJECT_ID, fid,
                                body.get("operator_id", ""),
                                body.get("operator_name", ""))


@router.post("/orders/{fid}/complete", summary="完成工单")
def complete_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.complete_work_order(FEC_ID, FPROJECT_ID, fid,
                                   body.get("result_summary", ""),
                                   body.get("image_urls"),
                                   body.get("operator_id", ""),
                                   body.get("operator_name", ""))


@router.post("/orders/{fid}/review", summary="审核工单")
def review_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.review_work_order(FEC_ID, FPROJECT_ID, fid,
                                 body.get("review_result", ""),
                                 body.get("review_opinion", ""),
                                 body.get("reviewer_id", ""),
                                 body.get("reviewer_name", ""))


@router.post("/orders/{fid}/cancel", summary="取消工单")
def cancel_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.cancel_work_order(FEC_ID, FPROJECT_ID, fid,
                                 body.get("reason", ""),
                                 body.get("operator_id", ""),
                                 body.get("operator_name", ""))


@router.post("/orders/{fid}/evaluate", summary="评价工单")
def evaluate_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.evaluate_work_order(FEC_ID, FPROJECT_ID, fid,
                                   body.get("score", 5),
                                   body.get("content", ""),
                                   body.get("evaluator_id", ""),
                                   body.get("evaluator_name", ""))


@router.post("/orders/{fid}/transfer", summary="转单")
def transfer_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.transfer_work_order(FEC_ID, FPROJECT_ID, fid,
                                   body.get("target_assignee_id", ""),
                                   body.get("target_assignee_name", ""),
                                   body.get("reason", ""),
                                   body.get("operator_id", ""),
                                   body.get("operator_name", ""))


@router.post("/orders/{fid}/remind", summary="催办")
def remind_order(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.remind_work_order(FEC_ID, FPROJECT_ID, fid,
                                 body.get("content", ""),
                                 body.get("reminder_user_id", ""),
                                 body.get("reminder_user_name", ""))


@router.post("/orders/{fid}/check-records", summary="保存检查记录")
def save_check_records(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.save_check_records(FEC_ID, FPROJECT_ID, fid,
                                  body.get("records", []),
                                  body.get("operator_id", ""),
                                  body.get("operator_name", ""))


@router.get("/orders/{fid}/logs", summary="获取工单操作日志")
def get_order_logs(fid: str, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.get_operation_logs(FEC_ID, FPROJECT_ID, fid)


@router.get("/orders/{fid}/flows", summary="获取工单流转记录")
def get_order_flows(fid: str, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.get_flow_instances(FEC_ID, FPROJECT_ID, fid)


@router.get("/orders/{fid}/check-records", summary="获取工单检查记录")
def get_check_records(fid: str, db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.get_check_records(FEC_ID, FPROJECT_ID, fid)


@router.get("/orders/{fid}/statistics", summary="工单统计")
def get_statistics(db: Session = Depends(get_db)):
    svc = SmartWorkOrderService(db)
    return svc.get_statistics(FEC_ID, FPROJECT_ID)


# ========== 工单模板 ==========

@router.get("/templates", summary="获取模板列表")
def list_templates(
    wo_type: str = Query(default=""),
    status: str = Query(default=""),
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    svc = WoTemplateService(db)
    return svc.list_templates(FEC_ID, FPROJECT_ID, wo_type, status, keyword, page, page_size)


@router.get("/templates/{fid}", summary="获取模板详情")
def get_template(fid: str, db: Session = Depends(get_db)):
    svc = WoTemplateService(db)
    return svc.get_template(FEC_ID, FPROJECT_ID, fid)


@router.post("/templates", summary="创建模板")
def create_template(body: dict, db: Session = Depends(get_db)):
    svc = WoTemplateService(db)
    return svc.create_template(FEC_ID, FPROJECT_ID, **body)


@router.put("/templates/{fid}", summary="更新模板")
def update_template(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = WoTemplateService(db)
    return svc.update_template(FEC_ID, FPROJECT_ID, fid, **body)


@router.delete("/templates/{fid}", summary="删除模板")
def delete_template(fid: str, db: Session = Depends(get_db)):
    svc = WoTemplateService(db)
    return svc.delete_template(FEC_ID, FPROJECT_ID, fid)


# ========== SLA规则 ==========

@router.get("/sla-rules", summary="获取SLA规则列表")
def list_sla_rules(db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.list_sla_rules(FEC_ID, FPROJECT_ID)


@router.post("/sla-rules", summary="创建SLA规则")
def create_sla_rule(body: dict, db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.create_sla_rule(FEC_ID, FPROJECT_ID, **body)


@router.put("/sla-rules/{fid}", summary="更新SLA规则")
def update_sla_rule(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.update_sla_rule(FEC_ID, FPROJECT_ID, fid, **body)


# ========== 派单规则 ==========

@router.get("/dispatch-rules", summary="获取派单规则列表")
def list_dispatch_rules(db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.list_dispatch_rules(FEC_ID, FPROJECT_ID)


@router.post("/dispatch-rules", summary="创建派单规则")
def create_dispatch_rule(body: dict, db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.create_dispatch_rule(FEC_ID, FPROJECT_ID, **body)


@router.put("/dispatch-rules/{fid}", summary="更新派单规则")
def update_dispatch_rule(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.update_dispatch_rule(FEC_ID, FPROJECT_ID, fid, **body)


@router.delete("/dispatch-rules/{fid}", summary="删除派单规则")
def delete_dispatch_rule(fid: str, db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.delete_dispatch_rule(FEC_ID, FPROJECT_ID, fid)


@router.post("/dispatch-rules/auto-dispatch", summary="智能派单匹配")
def auto_dispatch(body: dict, db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.auto_dispatch(FEC_ID, FPROJECT_ID,
                             body.get("category_id", ""),
                             body.get("location_type", ""),
                             body.get("priority", ""),
                             body.get("keyword", ""))


# ========== 工单分类 ==========

@router.get("/categories", summary="获取分类列表")
def list_categories(
    category_type: str = Query(default=""),
    parent_id: str = Query(default=None),
    db: Session = Depends(get_db)
):
    svc = WoRuleService(db)
    return svc.list_categories(FEC_ID, FPROJECT_ID, category_type, parent_id)


@router.post("/categories", summary="创建分类")
def create_category(body: dict, db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.create_category(FEC_ID, FPROJECT_ID, **body)


@router.put("/categories/{fid}", summary="更新分类")
def update_category(fid: str, body: dict, db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.update_category(FEC_ID, FPROJECT_ID, fid, **body)


@router.delete("/categories/{fid}", summary="删除分类")
def delete_category(fid: str, db: Session = Depends(get_db)):
    svc = WoRuleService(db)
    return svc.delete_category(FEC_ID, FPROJECT_ID, fid)


# ========== 定时任务（手动触发） ==========

@router.post("/scheduler/check-overdue", summary="手动触发SLA超期检测")
def manual_check_overdue(db: Session = Depends(get_db)):
    from service.wo_scheduler_service import WoSchedulerService
    svc = WoSchedulerService(db)
    return svc.check_overdue_orders(FEC_ID, FPROJECT_ID)


@router.post("/scheduler/generate-from-templates", summary="手动触发模板生成工单")
def manual_generate_from_templates(db: Session = Depends(get_db)):
    from service.wo_scheduler_service import WoSchedulerService
    svc = WoSchedulerService(db)
    return svc.generate_orders_from_templates(FEC_ID, FPROJECT_ID)
