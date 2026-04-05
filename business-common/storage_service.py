"""
统一存储服务 V14.0
支持: 本地存储（默认）/ 阿里云OSS / AWS S3

通过环境变量 STORAGE_BACKEND 切换:
  - 不设置或 'local' -> 本地文件系统
  - 'oss' -> 阿里云OSS
  - 's3' -> AWS S3兼容

配置示例:
  STORAGE_BACKEND=local
  STORAGE_LOCAL_DIR=./uploads

  STORAGE_BACKEND=oss
  OSS_ACCESS_KEY_ID=xxx
  OSS_ACCESS_KEY_SECRET=xxx
  OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
  OSS_BUCKET_NAME=my-bucket
"""
import os
import uuid
import base64
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local')
DEFAULT_CONFIG = {
    'upload_dir': 'uploads',
    'max_size_mb': 5,
    'max_files': 9,
    'allowed_image_exts': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'},
    'allowed_doc_exts': {'pdf', 'doc', 'docx', 'xls', 'xlsx'},
    'magic_map': {
        b'\xff\xd8\xff': ['jpg', 'jpeg'],
        b'\x89PNG': ['png'],
        b'GIF8': ['gif'],
        b'RIFF': ['webp'],
        b'BM': ['bmp'],
        b'%PDF': ['pdf'],
    }
}


class LocalStorageBackend:
    """本地文件系统存储"""
    def __init__(self, config=None):
        self.upload_dir = config.get('upload_dir', 'uploads') if config else 'uploads'
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir, exist_ok=True)

    def save(self, filename, data_bytes):
        filepath = os.path.join(self.upload_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(data_bytes)
        return f"/uploads/{filename}"

    def delete(self, filename):
        safe_name = os.path.basename(filename)
        filepath = os.path.join(self.upload_dir, safe_name)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def exists(self, filename):
        return os.path.exists(os.path.join(self.upload_dir, os.path.basename(filename)))

    def get_url(self, filename):
        return f"/uploads/{filename}"


class AliyunOSSBackend:
    """阿里云OSS存储（预留，需安装oss2）"""
    def __init__(self, config=None):
        try:
            import oss2
            auth = oss2.Auth(
                os.environ['OSS_ACCESS_KEY_ID'],
                os.environ['OSS_ACCESS_KEY_SECRET']
            )
            self.bucket = oss2.Bucket(
                auth,
                os.environ.get('OSS_ENDPOINT', 'oss-cn-hangzhou.aliyuncs.com'),
                os.environ['OSS_BUCKET_NAME']
            )
            self._available = True
            logger.info("阿里云OSS存储已连接")
        except ImportError:
            logger.warning("oss2未安装，OSS存储不可用")
            self._available = False
        except Exception as e:
            logger.warning(f"OSS连接失败: {e}")
            self._available = False

    def save(self, filename, data_bytes):
        if not self._available:
            raise RuntimeError("OSS不可用")
        from io import BytesIO
        self.bucket.put_object(filename, BytesIO(data_bytes))
        return self.get_url(filename)

    def delete(self, filename):
        if not self._available:
            return False
        try:
            self.bucket.delete_object(filename)
            return True
        except Exception:
            return False

    def exists(self, filename):
        if not self._available:
            return False
        try:
            return self.bucket.object_exists(filename)
        except Exception:
            return False

    def get_url(self, filename):
        bucket_name = os.environ.get('OSS_BUCKET_NAME', '')
        endpoint = os.environ.get('OSS_ENDPOINT', 'oss-cn-hangzhou.aliyuncs.com')
        if os.environ.get('OSS_PUBLIC_READ') == '1':
            return f"https://{bucket_name}.{endpoint}/{filename}"
        else:
            import oss2
            return self.bucket.sign_url('GET', filename, 3600)


class S3Backend:
    """S3兼容存储（预留，需安装boto3）"""
    def __init__(self, config=None):
        try:
            import boto3
            self.client = boto3.client(
                's3',
                endpoint_url=os.environ.get('S3_ENDPOINT'),
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                region_name=os.environ.get('S3_REGION', 'us-east-1')
            )
            self.bucket_name = os.environ['S3_BUCKET_NAME']
            self._available = True
            logger.info("S3存储已连接")
        except ImportError:
            logger.warning("boto3未安装，S3存储不可用")
            self._available = False
        except Exception as e:
            logger.warning(f"S3连接失败: {e}")
            self._available = False

    def save(self, filename, data_bytes):
        if not self._available:
            raise RuntimeError("S3不可用")
        from io import BytesIO
        self.client.upload_fileobj(BytesIO(data_bytes), self.bucket_name, filename)
        return self.get_url(filename)

    def delete(self, filename):
        if not self._available:
            return False
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=filename)
            return True
        except Exception:
            return False

    def exists(self, filename):
        if not self._available:
            return False
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=filename)
            return True
        except Exception:
            return False

    def get_url(self, filename):
        endpoint = os.environ.get('S3_ENDPOINT', 'https://s3.amazonaws.com')
        return f"{endpoint}/{os.environ.get('S3_BUCKET_NAME', '')}/{filename}"


def _create_backend():
    config = {'upload_dir': os.environ.get('STORAGE_LOCAL_DIR', 'uploads')}
    if STORAGE_BACKEND == 'oss':
        return AliyunOSSBackend(config)
    elif STORAGE_BACKEND == 's3':
        return S3Backend(config)
    else:
        return LocalStorageBackend(config)

_backend = _create_backend()


class StorageService:
    """统一存储服务"""

    @staticmethod
    def upload_base64(file_data, ext=None, allowed_exts=None):
        if not file_data:
            return {'success': False, 'msg': '没有文件数据'}

        raw = file_data
        if ',' in file_data:
            header, raw = file_data.split(',', 1)
            if not ext:
                if 'image/png' in header: ext = 'png'
                elif 'image/gif' in header: ext = 'gif'
                elif 'image/webp' in header: ext = 'webp'
                elif 'image/jpeg' in header or 'image/jpg' in header: ext = 'jpg'
                else: ext = 'jpg'

        if not ext: ext = 'jpg'
        ext = ext.lower().lstrip('.')

        allowed = allowed_exts or DEFAULT_CONFIG['allowed_image_exts']
        if ext not in allowed:
            return {'success': False, 'msg': f'不支持的文件类型，仅允许：{", ".join(allowed)}'}

        try:
            decoded = base64.b64decode(raw)
        except Exception as e:
            return {'success': False, 'msg': f'文件解码失败: {str(e)}'}

        max_bytes = DEFAULT_CONFIG['max_size_mb'] * 1024 * 1024
        if len(decoded) > max_bytes:
            return {'success': False, 'msg': f'文件超过{DEFAULT_CONFIG["max_size_mb"]}MB限制'}

        valid_magic = False
        for magic, exts in DEFAULT_CONFIG['magic_map'].items():
            if decoded[:len(magic)] == magic and ext in exts:
                valid_magic = True
                break
        if not valid_magic and ext in [e for exts in DEFAULT_CONFIG['magic_map'].values() for e in exts]:
            return {'success': False, 'msg': '文件内容与扩展名不匹配'}

        date_dir = datetime.now().strftime('%Y%m')
        filename = f"{date_dir}/{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:12]}.{ext}"

        try:
            url = _backend.save(filename, decoded)
            return {'success': True, 'url': url, 'filename': filename, 'size': len(decoded)}
        except Exception as e:
            logger.error(f"文件保存失败: {e}")
            return {'success': False, 'msg': '文件保存失败'}

    @staticmethod
    def upload_base64_batch(files_data, allowed_exts=None):
        max_files = DEFAULT_CONFIG['max_files']
        if not isinstance(files_data, list):
            return {'success': False, 'msg': '文件列表格式错误'}
        if len(files_data) > max_files:
            return {'success': False, 'msg': f'最多上传{max_files}个文件'}

        results = []
        failed = 0
        for fd in files_data:
            if isinstance(fd, str) and fd:
                r = StorageService.upload_base64(fd, allowed_exts=allowed_exts)
                if r.get('success'):
                    results.append({'url': r['url'], 'filename': r['filename']})
                else:
                    failed += 1
            else:
                failed += 1

        return {'success': True, 'items': results, 'failed': failed,
                'total': len(files_data), 'success_count': len(results)}

    @staticmethod
    def delete_file(filename):
        if not filename: return False
        try: return _backend.delete(filename)
        except Exception: return False

    @staticmethod
    def get_backend_type():
        return STORAGE_BACKEND
