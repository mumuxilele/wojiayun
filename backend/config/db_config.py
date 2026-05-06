# config/db_config.py - 数据库连接配置（MySQL/SQLite双引擎）
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.env_config import DB_CONFIG, ENV
from utils.log_util import logger

DB_TYPE: str = DB_CONFIG.get("type", "mysql")

if DB_TYPE == "sqlite":
    _db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        f"data_{ENV}.db"
    )
    os.makedirs(os.path.dirname(_db_path), exist_ok=True)
    DB_URL = f"sqlite:///{_db_path}"
    _engine_kwargs = {"echo": False}
    _connect_args = {}
    logger.info(f"使用 SQLite 数据库: {_db_path}")
else:
    DB_URL = (
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        f"?charset=utf8mb4"
    )
    _engine_kwargs = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "echo": False,
    }
    _connect_args = {
        "connect_timeout": 5,
        "charset": "utf8mb4"
    }
    logger.info(f"使用 MySQL 数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")

# 创建数据库引擎
engine = create_engine(url=DB_URL, connect_args=_connect_args, **_engine_kwargs)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)


def get_db() -> Session:
    """获取数据库会话：自动创建、自动关闭"""
    db = SessionLocal()
    try:
        yield db
        logger.debug("数据库会话创建成功")
    except Exception as e:
        db.rollback()
        logger.error(f"数据库会话异常：{str(e)}", exc_info=True)
        raise
    finally:
        db.close()
        logger.debug("数据库会话已关闭")
