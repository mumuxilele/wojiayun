# service/admin_service.py - 管理员认证与统计服务
from typing import Dict, Optional
from sqlalchemy.orm import Session
from service.base_service import BaseService
from db.models import AdminUser, Enterprise, WorkOrder, Bill, Staff
from utils.md5_fid_util import generate_fid
from utils.log_util import logger
from utils.time_util import now_str
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminService(BaseService):
    """管理员认证与管理服务"""

    # ── 认证相关 ──

    def login(self, username: str, password: str) -> Dict:
        """管理员登录"""
        try:
            user = AdminUser.active_query(self.db).filter(
                AdminUser.username == username
            ).first()
            if not user:
                return self.error("用户名或密码错误", 401)
            if not pwd_context.verify(password, user.password_hash):
                return self.error("用户名或密码错误", 401)
            if user.status != "启用":
                return self.error("账号已被禁用", 403)

            # 更新登录信息
            user.last_login_at = now_str()
            user.login_count = (user.login_count or 0) + 1
            self.db.commit()

            return self.success({
                "fid": user.fid, "username": user.username,
                "name": user.name, "role": user.role,
                "enterprise_id": user.enterprise_id
            }, "登录成功")
        except Exception as e:
            logger.error(f"登录失败：{str(e)}", exc_info=True)
            return self.error(f"登录失败：{str(e)}")

    def create_admin(self, fec_id: str, fproject_id: str,
                     username: str, password: str, name: str,
                     role: str = "管理员", phone: str = "",
                     enterprise_id: str = "") -> Dict:
        """创建管理员账号"""
        try:
            # 检查用户名重复
            exist = AdminUser.active_query(self.db).filter(
                AdminUser.username == username
            ).first()
            if exist:
                return self.error("用户名已存在", 409)

            self.begin()
            fid = generate_fid()
            admin = AdminUser(
                fid=fid, fec_id=fec_id, fproject_id=fproject_id,
                username=username,
                password_hash=pwd_context.hash(password),
                name=name, role=role, phone=phone,
                enterprise_id=enterprise_id
            )
            self.db.add(admin)
            self.commit()
            self.db.refresh(admin)
            return self.success({
                "fid": admin.fid, "username": admin.username,
                "name": admin.name, "role": admin.role
            }, "创建成功")
        except Exception as e:
            self.rollback()
            return self.error(f"创建管理员失败：{str(e)}")

    def change_password(self, fid: str, old_password: str, new_password: str) -> Dict:
        """修改密码"""
        try:
            user = AdminUser.active_query(self.db).filter(AdminUser.fid == fid).first()
            if not user:
                return self.error("用户不存在", 404)
            if not pwd_context.verify(old_password, user.password_hash):
                return self.error("原密码错误", 400)

            self.begin()
            user.password_hash = pwd_context.hash(new_password)
            self.commit()
            return self.success(message="密码修改成功")
        except Exception as e:
            self.rollback()
            return self.error(f"修改密码失败：{str(e)}")

    # ── 仪表盘统计 ──

    def get_dashboard_stats(self, fec_id: str, fproject_id: str) -> Dict:
        """获取管理仪表盘统计数据"""
        try:
            enterprises = Enterprise.active_query(self.db).filter(
                Enterprise.fec_id == fec_id, Enterprise.fproject_id == fproject_id
            ).count()

            pending_orders = WorkOrder.active_query(self.db).filter(
                WorkOrder.fec_id == fec_id, WorkOrder.fproject_id == fproject_id,
                WorkOrder.status == "待派单"
            ).count()

            processing_orders = WorkOrder.active_query(self.db).filter(
                WorkOrder.fec_id == fec_id, WorkOrder.fproject_id == fproject_id,
                WorkOrder.status == "处理中"
            ).count()

            today_total = WorkOrder.active_query(self.db).filter(
                WorkOrder.fec_id == fec_id, WorkOrder.fproject_id == fproject_id
            ).count()

            staff_count = Staff.active_query(self.db).filter(
                Staff.fec_id == fec_id, Staff.fproject_id == fproject_id
            ).count()

            # 欠费统计
            from sqlalchemy import func
            result = self.db.query(
                func.count(Bill.fid),
                func.coalesce(func.sum(Bill.amount - Bill.paid_amount), 0)
            ).filter(
                Bill.fec_id == fec_id, Bill.fproject_id == fproject_id,
                Bill.is_deleted == 0, Bill.status != "已缴"
            ).first()

            return self.success({
                "enterprises": enterprises,
                "pending_orders": pending_orders,
                "processing_orders": processing_orders,
                "today_total": today_total,
                "staff_count": staff_count,
                "overdue_count": result[0] if result else 0,
                "overdue_amount": float(result[1]) if result else 0,
            })
        except Exception as e:
            logger.error(f"获取仪表盘数据失败：{str(e)}", exc_info=True)
            return self.error(f"获取仪表盘数据失败：{str(e)}")
