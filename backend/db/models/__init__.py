# db/models/__init__.py - 模型统一导出
# === 核心模块 ===
from db.models.enterprise import Enterprise
from db.models.building import Building
from db.models.resident import Resident
from db.models.staff import Staff
from db.models.work_order import WorkOrder
from db.models.bill import Bill
from db.models.repair import Repair
from db.models.complaint import Complaint
from db.models.visit import Visit
from db.models.notice import Notice
from db.models.payment import Payment
from db.models.equipment import Equipment
from db.models.admin_user import AdminUser

# === 扩展模块（legacy，多类单文件） ===
from db.models.decoration import DecorationApplication, DecorationInspection
from db.models.finance import FeeItem, Payment as FinancePayment, Invoice
from db.models.inspection import InspectionTask, InspectionRecord, PCAR
from db.models.owner import Owner, Tenant, FamilyMember
from db.models.safety import SafetyIncident, SafetyHazard
from db.models.user import User, Role, Permission, UserRole, RolePermission
from db.models.visitor import Visitor, VisitorBlacklist

__all__ = [
    "Enterprise", "Building", "Resident", "Staff",
    "WorkOrder", "Bill", "Repair", "Complaint",
    "Visit", "Notice", "Payment", "Equipment", "AdminUser",
    "DecorationApplication", "DecorationInspection",
    "FeeItem", "FinancePayment", "Invoice",
    "InspectionTask", "InspectionRecord", "PCAR",
    "Owner", "Tenant", "FamilyMember",
    "SafetyIncident", "SafetyHazard",
    "User", "Role", "Permission", "UserRole", "RolePermission",
    "Visitor", "VisitorBlacklist"
]
