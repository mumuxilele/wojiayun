# main.py - 粤海物业管理系统 · FastAPI 入口
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.base import Base
from config.db_config import engine
from config.env_config import API_PORT
from utils.log_util import logger
from api import (
    enterprise_router, building_router, resident_router,
    staff_router, work_order_router, bill_router, admin_router,
    smart_work_order_router
)

# 创建FastAPI应用
app = FastAPI(
    title="粤海物业管理系统",
    description="Python + MySQL 后端服务 · 遵循 V2.0 企业级开发规范",
    version="2.0.0"
)

# CORS 配置（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(enterprise_router)
app.include_router(building_router)
app.include_router(resident_router)
app.include_router(staff_router)
app.include_router(work_order_router)
app.include_router(bill_router)
app.include_router(admin_router)
app.include_router(smart_work_order_router)


@app.on_event("startup")
def startup():
    """应用启动：创建数据库表 + 启动定时任务"""
    logger.info("粤海物业管理系统启动中...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表初始化完成")
    except Exception as e:
        logger.warning(f"数据库表初始化跳过（可能已存在）：{str(e)}")

    # 启动智慧工单后台定时任务
    try:
        from service.wo_background_scheduler import start_scheduler
        start_scheduler()
        logger.info("智慧工单定时任务已启动")
    except Exception as e:
        logger.warning(f"智慧工单定时任务启动失败: {str(e)}")


@app.on_event("shutdown")
def shutdown():
    """应用关闭：停止定时任务"""
    try:
        from service.wo_background_scheduler import stop_scheduler
        stop_scheduler()
        logger.info("智慧工单定时任务已停止")
    except Exception:
        pass


@app.get("/")
def root():
    return {
        "service": "粤海物业管理系统 API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "running"
    }


if __name__ == "__main__":
    logger.info(f"启动API服务：http://0.0.0.0:{API_PORT}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=API_PORT,
        reload=True,
        log_level="info"
    )
