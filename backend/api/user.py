"""
用户管理API
用户CRUD、角色分配、权限管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.base import get_db
from db.models.user import User, Role, Permission, UserRole, RolePermission
from utils.auth_util import verify_token, hash_password, OAuth2PasswordBearer
from utils.response_util import (
    success_response, error_response, 
    paginate_response, created_response, 
    updated_response, deleted_response, not_found_response
)
from utils.md5_fid_util import generate_fid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ========== Pydantic Models ==========

class UserCreate(BaseModel):
    """用户创建"""
    username: str
    password: str
    real_name: str
    phone: str
    department: Optional[str] = None
    position: Optional[str] = None
    fec_id: str
    fproject_id: Optional[str] = None
    role_ids: Optional[List[str]] = []


class UserUpdate(BaseModel):
    """用户更新"""
    real_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    fproject_id: Optional[str] = None
    fstatus: Optional[str] = None


class RoleCreate(BaseModel):
    """角色创建"""
    role_name: str
    role_code: str
    description: Optional[str] = None
    permission_ids: Optional[List[str]] = []


# ========== 用户管理 ==========

@router.get("", summary="获取用户列表")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    username: Optional[str] = None,
    real_name: Optional[str] = None,
    department: Optional[str] = None,
    fstatus: Optional[str] = None,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取用户列表（分页）"""
    query = db.query(User).filter(User.is_deleted == 0)
    
    if username:
        query = query.filter(User.username.like(f"%{username}%"))
    if real_name:
        query = query.filter(User.real_name.like(f"%{real_name}%"))
    if department:
        query = query.filter(User.department == department)
    if fstatus:
        query = query.filter(User.fstatus == fstatus)
    
    total = query.count()
    users = query.order_by(User.create_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for user in users:
        # 获取用户角色
        roles = db.query(Role).join(UserRole).filter(UserRole.fuser_id == user.fid).all()
        items.append({
            "fid": user.fid,
            "username": user.username,
            "real_name": user.real_name,
            "phone": user.phone,
            "department": user.department,
            "position": user.position,
            "fstatus": user.fstatus,
            "fec_id": user.fec_id,
            "fproject_id": user.fproject_id,
            "create_time": user.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "roles": [{"fid": r.fid, "role_name": r.role_name} for r in roles]
        })
    
    return paginate_response(items, total, page, page_size)


@router.post("", summary="创建用户")
async def create_user(
    user_data: UserCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建新用户"""
    # 检查用户名是否已存在
    existing = db.query(User).filter(
        User.username == user_data.username,
        User.is_deleted == 0
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    user = User(
        fid=generate_fid("user"),
        username=user_data.username,
        password=hash_password(user_data.password),
        real_name=user_data.real_name,
        phone=user_data.phone,
        department=user_data.department,
        position=user_data.position,
        fec_id=user_data.fec_id,
        fproject_id=user_data.fproject_id,
        fstatus="active"
    )
    db.add(user)
    
    # 分配角色
    if user_data.role_ids:
        for role_id in user_data.role_ids:
            user_role = UserRole(
                fid=generate_fid("ur"),
                fuser_id=user.fid,
                frole_id=role_id,
                fec_id=user_data.fec_id
            )
            db.add(user_role)
    
    db.commit()
    db.refresh(user)
    
    return created_response(data={"fid": user.fid}, message="用户创建成功")


@router.get("/{user_id}", summary="获取用户详情")
async def get_user(
    user_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取用户详情"""
    user = db.query(User).filter(User.fid == user_id, User.is_deleted == 0).first()
    if not user:
        return not_found_response("用户不存在")
    
    # 获取用户角色
    roles = db.query(Role).join(UserRole).filter(UserRole.fuser_id == user.fid).all()
    
    return success_response(data={
        "fid": user.fid,
        "username": user.username,
        "real_name": user.real_name,
        "phone": user.phone,
        "department": user.department,
        "position": user.position,
        "fstatus": user.fstatus,
        "fec_id": user.fec_id,
        "fproject_id": user.fproject_id,
        "create_time": user.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "roles": [{"fid": r.fid, "role_name": r.role_name, "role_code": r.role_code} for r in roles]
    })


@router.put("/{user_id}", summary="更新用户")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    user = db.query(User).filter(User.fid == user_id, User.is_deleted == 0).first()
    if not user:
        return not_found_response("用户不存在")
    
    # 更新字段
    if user_data.real_name is not None:
        user.real_name = user_data.real_name
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.department is not None:
        user.department = user_data.department
    if user_data.position is not None:
        user.position = user_data.position
    if user_data.fproject_id is not None:
        user.fproject_id = user_data.fproject_id
    if user_data.fstatus is not None:
        user.fstatus = user_data.fstatus
    
    user.update_time = datetime.now()
    db.commit()
    
    return updated_response(message="用户更新成功")


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """软删除用户"""
    user = db.query(User).filter(User.fid == user_id, User.is_deleted == 0).first()
    if not user:
        return not_found_response("用户不存在")
    
    user.is_deleted = 1
    user.delete_time = datetime.now()
    db.commit()
    
    return deleted_response()


@router.post("/{user_id}/roles", summary="分配角色")
async def assign_roles(
    user_id: str,
    role_ids: List[str],
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """为用户分配角色"""
    user = db.query(User).filter(User.fid == user_id, User.is_deleted == 0).first()
    if not user:
        return not_found_response("用户不存在")
    
    # 删除原有角色
    db.query(UserRole).filter(UserRole.fuser_id == user_id).delete()
    
    # 添加新角色
    for role_id in role_ids:
        user_role = UserRole(
            fid=generate_fid("ur"),
            fuser_id=user_id,
            frole_id=role_id,
            fec_id=user.fec_id
        )
        db.add(user_role)
    
    db.commit()
    return success_response(message="角色分配成功")


# ========== 角色管理 ==========

@router.get("/roles", summary="获取角色列表")
async def list_roles(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取所有角色"""
    roles = db.query(Role).filter(Role.is_deleted == 0).all()
    items = [{"fid": r.fid, "role_name": r.role_name, "role_code": r.role_code, "description": r.description} for r in roles]
    return success_response(data=items)


@router.post("/roles", summary="创建角色")
async def create_role(
    role_data: RoleCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """创建角色"""
    role = Role(
        fid=generate_fid("role"),
        role_name=role_data.role_name,
        role_code=role_data.role_code,
        description=role_data.description,
        fec_id=""  # TODO: 从token获取
    )
    db.add(role)
    
    # 分配权限
    if role_data.permission_ids:
        for perm_id in role_data.permission_ids:
            rp = RolePermission(
                fid=generate_fid("rp"),
                frole_id=role.fid,
                fpermission_id=perm_id,
                fec_id=role.fec_id
            )
            db.add(rp)
    
    db.commit()
    return created_response(data={"fid": role.fid}, message="角色创建成功")


# ========== 权限管理 ==========

@router.get("/permissions", summary="获取权限列表")
async def list_permissions(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取所有权限"""
    permissions = db.query(Permission).filter(Permission.is_deleted == 0).all()
    items = [{"fid": p.fid, "perm_name": p.perm_name, "perm_code": p.perm_code, "resource": p.resource} for p in permissions]
    return success_response(data=items)
