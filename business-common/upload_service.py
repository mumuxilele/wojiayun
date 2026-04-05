"""
统一文件上传服务 V5.0
支持: 本地存储、文件类型校验、大小限制、魔数校验
支持三端共用
"""
import os
import uuid
import logging
import base64
from datetime import datetime

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    'upload_dir': 'uploads',
    'max_size_mb': 5,
    'max_files': 9,
    'allowed_image_exts': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'},
    'allowed_doc_exts': {'pdf', 'doc', 'docx', 'xls', 'xlsx'},
    # 文件头魔数
    'magic_map': {
        b'\xff\xd8\xff': ['jpg', 'jpeg'],
        b'\x89PNG': ['png'],
        b'GIF8': ['gif'],
        b'RIFF': ['webp'],
        b'BM': ['bmp'],
        b'%PDF': ['pdf'],
    }
}


class UploadService:
    """统一上传服务"""
    
    def __init__(self, config=None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.upload_dir = self.config['upload_dir']
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir, exist_ok=True)
    
    def upload_base64(self, file_data, ext=None, allowed_exts=None):
        """
        上传Base64文件
        
        Args:
            file_data: Base64编码的文件数据(可含data:image/xxx;base64,前缀)
            ext: 文件扩展名(不传则自动检测)
            allowed_exts: 允许的扩展名列表(不传则使用默认图片扩展名)
            
        Returns:
            dict: {'success': True, 'url': '/uploads/xxx.jpg', 'filename': 'xxx.jpg'}
                  或 {'success': False, 'msg': '错误信息'}
        """
        if not file_data:
            return {'success': False, 'msg': '没有文件数据'}
        
        # 分离data URL前缀和实际数据
        raw = file_data
        if ',' in file_data:
            header, raw = file_data.split(',', 1)
            # 尝试从header推断扩展名
            if not ext:
                if 'image/png' in header:
                    ext = 'png'
                elif 'image/gif' in header:
                    ext = 'gif'
                elif 'image/webp' in header:
                    ext = 'webp'
                elif 'image/jpeg' in header or 'image/jpg' in header:
                    ext = 'jpg'
                else:
                    ext = 'jpg'
        
        if not ext:
            ext = 'jpg'
        ext = ext.lower().lstrip('.')
        
        # 扩展名白名单
        allowed = allowed_exts or self.config['allowed_image_exts']
        if ext not in allowed:
            return {'success': False, 'msg': f'不支持的文件类型，仅允许：{", ".join(allowed)}'}
        
        # 解码
        try:
            decoded = base64.b64decode(raw)
        except Exception as e:
            return {'success': False, 'msg': f'文件解码失败: {str(e)}'}
        
        # 大小校验
        max_bytes = self.config['max_size_mb'] * 1024 * 1024
        if len(decoded) > max_bytes:
            return {'success': False, 'msg': f'文件超过{self.config["max_size_mb"]}MB限制'}
        
        # 魔数校验
        valid_magic = False
        for magic, exts in self.config['magic_map'].items():
            if decoded[:len(magic)] == magic and ext in exts:
                valid_magic = True
                break
        
        if not valid_magic and ext in self.config['magic_map'].values():
            # 如果该类型有魔数校验要求但不匹配
            all_checkable_exts = set()
            for exts in self.config['magic_map'].values():
                all_checkable_exts.update(exts)
            if ext in all_checkable_exts:
                return {'success': False, 'msg': '文件内容与扩展名不匹配'}
        
        # 生成安全文件名
        filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:12]}.{ext}"
        filepath = os.path.join(self.upload_dir, filename)
        
        # 写入文件
        try:
            with open(filepath, 'wb') as f:
                f.write(decoded)
        except Exception as e:
            logger.error(f"文件写入失败: {e}")
            return {'success': False, 'msg': '文件保存失败'}
        
        url = f"/uploads/{filename}"
        return {'success': True, 'url': url, 'filename': filename, 'size': len(decoded)}
    
    def upload_base64_batch(self, files_data, allowed_exts=None):
        """
        批量上传Base64文件
        
        Args:
            files_data: Base64文件数据列表
            allowed_exts: 允许的扩展名列表
            
        Returns:
            dict: {'success': True, 'items': [...], 'failed': 0}
        """
        max_files = self.config['max_files']
        if not isinstance(files_data, list):
            return {'success': False, 'msg': '文件列表格式错误'}
        if len(files_data) > max_files:
            return {'success': False, 'msg': f'最多上传{max_files}个文件'}
        
        results = []
        failed = 0
        for fd in files_data:
            if isinstance(fd, str) and fd:
                r = self.upload_base64(fd, allowed_exts=allowed_exts)
                if r.get('success'):
                    results.append({'url': r['url'], 'filename': r['filename']})
                else:
                    failed += 1
            else:
                failed += 1
        
        return {
            'success': True,
            'items': results,
            'failed': failed,
            'total': len(files_data),
            'success_count': len(results)
        }
    
    def delete_file(self, filename):
        """删除上传的文件"""
        if not filename:
            return False
        # 防止路径遍历
        safe_name = os.path.basename(filename)
        filepath = os.path.join(self.upload_dir, safe_name)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except:
                return False
        return False


# Flask路由工厂
def create_upload_routes(app, service=None, route_prefix='/api/upload'):
    """为Flask应用创建上传路由"""
    if service is None:
        service = UploadService()
    
    @app.route(f'{route_prefix}', methods=['POST'])
    def upload_file():
        from flask import request, jsonify
        data = request.get_json() or {}
        file_data = data.get('file')
        ext = data.get('ext')
        result = service.upload_base64(file_data, ext)
        return jsonify(result)
    
    @app.route(f'{route_prefix}/batch', methods=['POST'])
    def upload_batch():
        from flask import request, jsonify
        data = request.get_json() or {}
        files = data.get('files', [])
        result = service.upload_base64_batch(files)
        return jsonify(result)
    
    @app.route('/uploads/<filename>')
    def serve_file(filename):
        from flask import send_from_directory
        return send_from_directory(service.upload_dir, filename)
    
    return service
