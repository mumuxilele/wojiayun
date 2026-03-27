"""
数据库操作模块
"""
import pymysql
from .config import DB_CONFIG

def get_db():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def get_one(sql, params=None):
    """查询单条记录"""
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchone()
    finally:
        db.close()

def get_all(sql, params=None):
    """查询多条记录"""
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        db.close()

def execute(sql, params=None):
    """执行增删改"""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(sql, params or ())
        db.commit()
        return cursor.lastrowid
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_total(sql, params=None):
    """获取总数"""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchone()[0]
    finally:
        db.close()
