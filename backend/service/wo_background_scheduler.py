# service/wo_background_scheduler.py - 后台定时任务调度器
"""
使用 threading + schedule 实现轻量级定时任务。
在 FastAPI startup 事件中启动后台线程。
"""
import threading
import time
import logging
from config.db_config import SessionLocal
from service.wo_scheduler_service import WoSchedulerService
from utils.log_util import logger

FEC_ID = "default_fec"
FPROJECT_ID = "default_project"

# 任务执行间隔（秒）
OVERDUE_CHECK_INTERVAL = 300      # SLA超期检测: 每5分钟
TEMPLATE_GENERATE_INTERVAL = 3600  # 模板生成工单: 每1小时

_scheduler_running = False


def _run_overdue_check():
    """SLA超期检测任务"""
    try:
        db = SessionLocal()
        try:
            svc = WoSchedulerService(db)
            result = svc.check_overdue_orders(FEC_ID, FPROJECT_ID)
            if result.get("code") == 200:
                data = result["data"]
                if data.get("overdue", 0) > 0:
                    logger.info(f"[定时任务] SLA超期检测: 发现{data['overdue']}个超期, 升级{data.get('escalated', 0)}个")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[定时任务] SLA超期检测异常: {str(e)}", exc_info=True)


def _run_template_generate():
    """模板自动生成工单任务"""
    try:
        db = SessionLocal()
        try:
            svc = WoSchedulerService(db)
            result = svc.generate_orders_from_templates(FEC_ID, FPROJECT_ID)
            if result.get("code") == 200:
                data = result["data"]
                if data.get("generated", 0) > 0:
                    logger.info(f"[定时任务] 模板生成工单: 生成{data['generated']}个")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[定时任务] 模板生成工单异常: {str(e)}", exc_info=True)


def _scheduler_loop():
    """调度器主循环"""
    global _scheduler_running
    logger.info("[定时任务] 智慧工单后台调度器已启动")

    last_overdue_check = 0
    last_template_generate = 0

    while _scheduler_running:
        try:
            current = time.time()

            # SLA超期检测
            if current - last_overdue_check >= OVERDUE_CHECK_INTERVAL:
                _run_overdue_check()
                last_overdue_check = current

            # 模板自动生成
            if current - last_template_generate >= TEMPLATE_GENERATE_INTERVAL:
                _run_template_generate()
                last_template_generate = current

            # 休眠避免CPU空转
            time.sleep(30)
        except Exception as e:
            logger.error(f"[定时任务] 调度器循环异常: {str(e)}", exc_info=True)
            time.sleep(60)

    logger.info("[定时任务] 智慧工单后台调度器已停止")


def start_scheduler():
    """启动后台调度器"""
    global _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True
    thread = threading.Thread(target=_scheduler_loop, daemon=True, name="wo-scheduler")
    thread.start()


def stop_scheduler():
    """停止后台调度器"""
    global _scheduler_running
    _scheduler_running = False
