# utils/time_util.py - 时间工具
import datetime

_UTC_OFFSET = datetime.timedelta(hours=8)


def now():
    """获取当前时间（上海时区）"""
    return datetime.datetime.now(datetime.timezone.utc) + _UTC_OFFSET


def now_str() -> str:
    """获取当前时间字符串：YYYY-MM-DD HH:MM:SS"""
    return now().strftime("%Y-%m-%d %H:%M:%S")


def format_time(dt: datetime.datetime) -> str:
    """格式化datetime为字符串"""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")
