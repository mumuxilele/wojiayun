# api/__init__.py - API路由统一导出
from api.enterprise_routes import router as enterprise_router
from api.building_routes import router as building_router
from api.resident_routes import router as resident_router
from api.staff_routes import router as staff_router
from api.work_order_routes import router as work_order_router
from api.bill_routes import router as bill_router
from api.admin_routes import router as admin_router

__all__ = [
    "enterprise_router", "building_router", "resident_router",
    "staff_router", "work_order_router", "bill_router", "admin_router"
]
