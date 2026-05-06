"""
认证工具
JWT生成与验证、密码加密与校验
"""
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config.env_config import JWT_CONFIG


def generate_token(
    user_id: str,
    username: str,
    fec_id: str,
    fproject_id: str = None,
    role_ids: list = None,
    expires_hours: int = None
) -> str:
    """
    生成JWT token
    
    Args:
        user_id: 用户ID
        username: 用户名
        fec_id: 企业ID
        fproject_id: 项目ID（可选）
        role_ids: 角色ID列表（可选）
        expires_hours: 过期时间（小时，可选，默认使用配置）
    
    Returns:
        str: JWT token
    """
    if expires_hours is None:
        expires_hours = JWT_CONFIG.get("expires_hours", 24)
    
    payload = {
        "user_id": user_id,
        "username": username,
        "fec_id": fec_id,
        "fproject_id": fproject_id,
        "role_ids": role_ids or [],
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        "iat": datetime.utcnow()
    }
    
    secret = JWT_CONFIG.get("secret", "your-secret-key")
    algorithm = JWT_CONFIG.get("algorithm", "HS256")
    
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证JWT token
    
    Args:
        token: JWT token
    
    Returns:
        Dict: 解析后的payload，None表示验证失败
    """
    try:
        secret = JWT_CONFIG.get("secret", "your-secret-key")
        algorithm = JWT_CONFIG.get("algorithm", "HS256")
        
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        # Token已过期
        return None
    except jwt.InvalidTokenError:
        # Token无效
        return None


def refresh_token(token: str) -> Optional[str]:
    """
    刷新token（在未过期的情况下延长有效期）
    
    Args:
        token: 原token
    
    Returns:
        str: 新token，None表示原token无效
    """
    payload = verify_token(token)
    if payload is None:
        return None
    
    # 使用原payload信息生成新token
    return generate_token(
        user_id=payload.get("user_id"),
        username=payload.get("username"),
        fec_id=payload.get("fec_id"),
        fproject_id=payload.get("fproject_id"),
        role_ids=payload.get("role_ids")
    )


def hash_password(password: str) -> str:
    """
    密码加密
    
    Args:
        password: 原密码
    
    Returns:
        str: 加密后的密码
    """
    # bcrypt自动处理salt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    校验密码
    
    Args:
        password: 原密码
        hashed_password: 加密后的密码
    
    Returns:
        bool: 是否匹配
    """
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    从token中提取用户信息
    
    Args:
        token: JWT token
    
    Returns:
        Dict: 用户信息字典
    """
    payload = verify_token(token)
    if payload is None:
        return None
    
    return {
        "user_id": payload.get("user_id"),
        "username": payload.get("username"),
        "fec_id": payload.get("fec_id"),
        "fproject_id": payload.get("fproject_id"),
        "role_ids": payload.get("role_ids", [])
    }


__all__ = [
    "generate_token",
    "verify_token",
    "refresh_token",
    "hash_password",
    "verify_password",
    "get_user_from_token",
]