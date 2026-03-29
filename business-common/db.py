"""
数据库操作模块 - 连接池版本
优化: 使用 DBUtils 连接池，避免每次请求新建/关闭连接，提升并发性能
"""
import pymysql
import logging
from .config import DB_CONFIG

logger = logging.getLogger(__name__)

# ============ 连接池初始化 ============
_pool = None

def _get_pool():
    """懒初始化连接池"""
    global _pool
    if _pool is None:
        try:
            from dbutils.pooled_db import PooledDB
            _pool = PooledDB(
                creator=pymysql,
                maxconnections=20,    # 最大连接数
                mincached=2,          # 初始化时，连接池中至少创建的空闲连接
                maxcached=10,         # 连接池中最多闲置的连接数
                maxshared=0,          # 连接池中最多共享的连接数（0表示不共享）
                blocking=True,        # 连接池满后是否阻塞等待
                ping=1,               # 检测连接是否有效
                **DB_CONFIG
            )
            logger.info("数据库连接池初始化成功")
        except ImportError:
            # 如果没有 dbutils，fallback 到直接连接模式
            logger.warning("dbutils 未安装，使用直接连接模式（建议 pip install dbutils）")
            _pool = None
    return _pool


def get_db():
    """获取数据库连接（优先使用连接池）"""
    pool = _get_pool()
    if pool:
        return pool.connection()
    # fallback: 直接连接
    return pymysql.connect(**DB_CONFIG)


# ============ 查询操作 ============

def get_one(sql, params=None):
    """查询单条记录，返回 dict 或 None"""
    conn = get_db()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"[DB get_one] 异常: {e} | SQL: {sql[:200]}")
        raise
    finally:
        conn.close()


def get_all(sql, params=None):
    """查询多条记录，返回 list[dict]"""
    conn = get_db()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"[DB get_all] 异常: {e} | SQL: {sql[:200]}")
        raise
    finally:
        conn.close()


def execute(sql, params=None):
    """执行增删改，返回 lastrowid"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB execute] 异常: {e} | SQL: {sql[:200]}")
        raise
    finally:
        conn.close()


def execute_many(sql, params_list):
    """批量执行，返回影响行数"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.executemany(sql, params_list)
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB execute_many] 异常: {e} | SQL: {sql[:200]}")
        raise
    finally:
        conn.close()


def get_total(sql, params=None):
    """获取 COUNT 查询结果"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            row = cursor.fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.error(f"[DB get_total] 异常: {e} | SQL: {sql[:200]}")
        return 0
    finally:
        conn.close()


def transaction(operations):
    """
    事务执行多条SQL
    operations: list of (sql, params) 元组
    """
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            for sql, params in operations:
                cursor.execute(sql, params or ())
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB transaction] 异常: {e}")
        raise
    finally:
        conn.close()
