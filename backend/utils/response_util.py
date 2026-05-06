"""
响应工具
统一API响应格式
"""
from typing import Any, Optional, Dict, List
from fastapi.responses import JSONResponse


def success_response(
    data: Any = None,
    message: str = "操作成功",
    code: int = 200
) -> Dict:
    """
    成功响应
    
    Args:
        data: 返回数据
        message: 提示消息
        code: 状态码
    
    Returns:
        Dict: 标准响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "success": True
    }


def error_response(
    message: str = "操作失败",
    code: int = 400,
    data: Any = None
) -> Dict:
    """
    错误响应
    
    Args:
        message: 错误消息
        code: 错误码
        data: 附加数据
    
    Returns:
        Dict: 标准响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "success": False
    }


def paginate_response(
    items: List,
    total: int,
    page: int = 1,
    page_size: int = 10,
    message: str = "查询成功"
) -> Dict:
    """
    分页响应
    
    Args:
        items: 数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页条数
        message: 提示消息
    
    Returns:
        Dict: 标准分页响应字典
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    return {
        "code": 200,
        "message": message,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "success": True
    }


def list_response(
    items: List,
    total: int = None,
    message: str = "查询成功"
) -> Dict:
    """
    列表响应（不分页）
    
    Args:
        items: 数据列表
        total: 总记录数（可选，默认为列表长度）
        message: 提示消息
    
    Returns:
        Dict: 标准列表响应字典
    """
    if total is None:
        total = len(items)
    
    return {
        "code": 200,
        "message": message,
        "data": {
            "items": items,
            "total": total
        },
        "success": True
    }


def created_response(
    data: Any = None,
    message: str = "创建成功",
    code: int = 201
) -> Dict:
    """
    创建成功响应
    
    Args:
        data: 返回数据
        message: 提示消息
        code: 状态码
    
    Returns:
        Dict: 标准响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "success": True
    }


def updated_response(
    data: Any = None,
    message: str = "更新成功"
) -> Dict:
    """
    更新成功响应
    
    Args:
        data: 返回数据
        message: 提示消息
    
    Returns:
        Dict: 标准响应字典
    """
    return {
        "code": 200,
        "message": message,
        "data": data,
        "success": True
    }


def deleted_response(
    message: str = "删除成功"
) -> Dict:
    """
    删除成功响应
    
    Args:
        message: 提示消息
    
    Returns:
        Dict: 标准响应字典
    """
    return {
        "code": 200,
        "message": message,
        "data": None,
        "success": True
    }


def not_found_response(
    message: str = "资源不存在"
) -> Dict:
    """
    资源不存在响应
    
    Args:
        message: 提示消息
    
    Returns:
        Dict: 标准响应字典
    """
    return {
        "code": 404,
        "message": message,
        "data": None,
        "success": False
    }


def unauthorized_response(
    message: str = "未授权访问"
) -> Dict:
    """
    未授权响应
    
    Args:
        message: 提示消息
    
    Returns:
        Dict: 标准响应字典
    """
    return {
        "code": 401,
        "message": message,
        "data": None,
        "success": False
    }


def forbidden_response(
    message: str = "禁止访问"
) -> Dict:
    """
    禁止访问响应
    
    Args:
        message: 提示消息
    
    Returns:
        Dict: 标准响应字典
    """
    return {
        "code": 403,
        "message": message,
        "data": None,
        "success": False
    }


def server_error_response(
    message: str = "服务器内部错误"
) -> Dict:
    """
    服务器错误响应
    
    Args:
        message: 提示消息
    
    Returns:
        Dict: 标准响应字典
    """
    return {
        "code": 500,
        "message": message,
        "data": None,
        "success": False
    }


__all__ = [
    "success_response",
    "error_response",
    "paginate_response",
    "list_response",
    "created_response",
    "updated_response",
    "deleted_response",
    "not_found_response",
    "unauthorized_response",
    "forbidden_response",
    "server_error_response",
]