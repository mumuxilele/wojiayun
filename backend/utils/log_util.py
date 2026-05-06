# utils/log_util.py - 全局日志配置
import logging
import colorlog
from config.env_config import ENV, get_env

LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")

level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

logger = logging.getLogger("yuehai_property")
logger.setLevel(level_map.get(LOG_LEVEL, logging.DEBUG))
logger.handlers.clear()

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(level_map.get(LOG_LEVEL, logging.DEBUG))

if ENV == "prod":
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
else:
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        }
    )

console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 生产环境文件日志
if ENV == "prod":
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename="logs/yuehai.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level_map.get(LOG_LEVEL, logging.WARNING))
    logger.addHandler(file_handler)

__all__ = ["logger"]
