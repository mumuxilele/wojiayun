# service/__init__.py - 业务层统一导出
from service.enterprise_service import EnterpriseService
from service.building_service import BuildingService
from service.resident_service import ResidentService
from service.staff_service import StaffService
from service.work_order_service import WorkOrderService
from service.bill_service import BillService
from service.admin_service import AdminService

__all__ = [
    "EnterpriseService", "BuildingService", "ResidentService",
    "StaffService", "WorkOrderService", "BillService", "AdminService"
]
