# utils/md5_fid_util.py - MD5 & FID 生成工具
import hashlib
import uuid
import os
from typing import Optional
from utils.log_util import logger


def generate_random_md5() -> str:
    """生成随机32位MD5值（用于非文件场景的唯一标识）"""
    random_str = str(uuid.uuid4()) + str(os.urandom(16))
    md5_obj = hashlib.md5(random_str.encode("utf-8"))
    return md5_obj.hexdigest()


def calculate_file_md5(file_path: str) -> Optional[str]:
    """计算文件真实MD5值（用于文件校验、去重）"""
    if not os.path.exists(file_path):
        logger.error(f"文件不存在，无法计算MD5：{file_path}")
        return None
    try:
        md5_obj = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                md5_obj.update(chunk)
        return md5_obj.hexdigest()
    except Exception as e:
        logger.error(f"计算文件MD5失败：{str(e)}", exc_info=True)
        return None


def generate_fid() -> str:
    """生成全局唯一主键fid（64位）"""
    uuid_md5 = generate_random_md5()
    random_md5 = generate_random_md5()
    return uuid_md5 + random_md5
