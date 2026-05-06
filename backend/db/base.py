# db/base.py - 全局ORM基类
from sqlalchemy import Column, DateTime, SmallInteger
from sqlalchemy.orm import Query, Session
from sqlalchemy.ext.declarative import declarative_base
import datetime

# 设置时区为中国上海
_UTC_OFFSET = datetime.timedelta(hours=8)


def _now():
    return datetime.datetime.now(datetime.timezone.utc) + _UTC_OFFSET


# 基础基类
Base = declarative_base()


class BaseModel(Base):
    """业务基类：包含软删除、时间字段，所有业务模型继承此类"""
    __abstract__ = True

    create_time = Column(DateTime, nullable=False, default=_now, comment="创建时间")
    update_time = Column(DateTime, nullable=False, default=_now, onupdate=_now, comment="更新时间")
    delete_time = Column(DateTime, nullable=True, comment="删除时间")
    is_deleted = Column(SmallInteger, default=0, comment="软删除标记：0=未删 1=已删")

    @classmethod
    def active_query(cls, db: Session) -> Query:
        """获取自动过滤已删除数据的查询"""
        return db.query(cls).filter(cls.is_deleted == 0)
