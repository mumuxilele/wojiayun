"""
认证API
登录、登出、token刷新
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from db.base import get_db
from db.models.user import User
from utils.auth_util import verify_password, generate_token, verify_token
from utils.response_util import success_response, error_response, unauthorized_response
from utils.md5_fid_util import generate_fid

router = APIRouter()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    real_name: str
    fec_id: str
    fproject_id: Optional[str] = None


class UserInfo(BaseModel):
    """用户信息"""
    user_id: str
    username: str
    real_name: str
    phone: str
    department: str
    position: str
    fec_id: str
    fproject_id: Optional[str] = None


@router.post("/login", summary="用户登录")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录
    
    - 验证用户名密码
    - 生成JWT token
    - 返回用户信息和token
    """
    # 查询用户
    user = db.query(User).filter(
        User.username == request.username,
        User.is_deleted == 0
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 检查用户状态
    if user.fstatus != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 生成token
    access_token = generate_token(
        user_id=user.fid,
        username=user.username,
        fec_id=user.fec_id,
        fproject_id=user.fproject_id
    )
    
    return success_response(data={
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.fid,
        "username": user.username,
        "real_name": user.real_name,
        "fec_id": user.fec_id,
        "fproject_id": user.fproject_id
    }, message="登录成功")


@router.post("/logout", summary="用户登出")
async def logout(token: str = Depends(oauth2_scheme)):
    """
    用户登出
    
    - 客户端清除token即可
    - 服务端可扩展token黑名单
    """
    return success_response(message="登出成功")


@router.post("/refresh", summary="刷新token")
async def refresh_token(token: str = Depends(oauth2_scheme)):
    """
    刷新token
    
    - 在token未过期的情况下延长有效期
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token无效或已过期"
        )
    
    # 生成新token
    new_token = generate_token(
        user_id=payload.get("user_id"),
        username=payload.get("username"),
        fec_id=payload.get("fec_id"),
        fproject_id=payload.get("fproject_id"),
        role_ids=payload.get("role_ids")
    )
    
    return success_response(data={
        "access_token": new_token,
        "token_type": "bearer"
    }, message="Token刷新成功")


@router.get("/me", summary="获取当前用户信息")
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    获取当前登录用户信息
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token无效或已过期"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.fid == user_id, User.is_deleted == 0).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return success_response(data={
        "user_id": user.fid,
        "username": user.username,
        "real_name": user.real_name,
        "phone": user.phone,
        "department": user.department,
        "position": user.position,
        "fec_id": user.fec_id,
        "fproject_id": user.fproject_id
    })


@router.put("/password", summary="修改密码")
async def change_password(
    old_password: str,
    new_password: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    修改密码
    
    - 需要验证旧密码
    - 新密码加密存储
    """
    from utils.auth_util import hash_password
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token无效或已过期"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.fid == user_id, User.is_deleted == 0).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 验证旧密码
    if not verify_password(old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    # 更新密码
    user.password = hash_password(new_password)
    db.commit()
    
    return success_response(message="密码修改成功")
