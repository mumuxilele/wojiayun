# config/env_config.py - 环境变量加载工具
import os
from dotenv import load_dotenv
from typing import Optional

# 加载环境变量：优先从系统环境变量获取ENV，默认dev
ENV: str = os.getenv("ENV", "dev")
_BACKEND_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BACKEND_ROOT, f".env.{ENV}"), override=True)


def get_env(key: str, default: Optional[str] = None) -> str:
    """
    获取环境变量，无值则抛出异常（必传）或返回默认值（可选）
    :param key: 环境变量键
    :param default: 默认值
    :return: 环境变量值
    """
    value: Optional[str] = os.getenv(key, default)
    if value is None:
        raise ValueError(f"环境变量 {key} 未配置，请检查 .env.{ENV} 文件")
    return value


# 数据库配置（统一导出，其他模块仅可导入此字典）
DB_CONFIG = {
    "type": get_env("DB_TYPE", "sqlite"),
    "host": get_env("DB_HOST", "127.0.0.1"),
    "port": get_env("DB_PORT", "3306"),
    "user": get_env("DB_USER", "root"),
    "password": get_env("DB_PASSWORD", ""),
    "database": get_env("DB_DATABASE", "yuehai_property"),
}

# 时区配置
TZ_CONFIG: str = get_env("TZ", "Asia/Shanghai")

# JWT密钥
SECRET_KEY: str = get_env("SECRET_KEY")

# API端口
API_PORT: int = int(get_env("API_PORT", "8000"))
