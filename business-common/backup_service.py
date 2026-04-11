"""
数据备份服务模块 V33.0
功能:
  - 数据库全量备份
  - 数据库增量备份
  - 数据恢复
  - 备份管理

依赖:
  - MySQL mysqldump 命令
  - 文件系统存储
"""

import os
import sys
import json
import logging
import hashlib
import subprocess
import shutil
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)


class BackupService(BaseService):
    """数据备份服务"""

    SERVICE_NAME = 'BackupService'

    # 备份类型
    BACKUP_TYPE_FULL = 'full'       # 全量备份
    BACKUP_TYPE_INCREMENTAL = 'incremental'  # 增量备份

    # 备份状态
    STATUS_PENDING = 'pending'      # 等待中
    STATUS_RUNNING = 'running'      # 执行中
    STATUS_COMPLETED = 'completed'  # 已完成
    STATUS_FAILED = 'failed'        # 失败
    STATUS_CANCELLED = 'cancelled'  # 已取消

    # 备份配置
    BACKUP_DIR = os.environ.get('BACKUP_DIR', '/var/backup/mysql')
    ENCRYPTION_KEY = os.environ.get('BACKUP_ENCRYPTION_KEY', '')
    MAX_BACKUP_RETENTION = 30  # 保留最近30天备份

    # MySQL配置
    MYSQL_HOST = os.environ.get('DB_HOST', '47.98.238.209')
    MYSQL_PORT = os.environ.get('DB_PORT', '3306')
    MYSQL_USER = os.environ.get('DB_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('DB_PASSWORD', '')
    MYSQL_DATABASE = os.environ.get('DB_NAME', 'visit_system')

    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            # 检查备份目录
            base['backup_dir_exists'] = os.path.exists(self.BACKUP_DIR)
            base['backup_dir_writable'] = os.access(self.BACKUP_DIR, os.W_OK) if base['backup_dir_exists'] else False
            
            # 获取备份列表
            backups = self.list_backups(limit=1)
            base['last_backup'] = backups[0] if backups else None
            
        except Exception as e:
            base['error'] = str(e)
        return base

    # ============ 备份操作 ============

    def create_backup(self, backup_type: str = BACKUP_TYPE_FULL,
                     tables: List[str] = None, compress: bool = True,
                     encryption: bool = False, description: str = None) -> Dict[str, Any]:
        """
        创建数据库备份

        Args:
            backup_type: 备份类型 (full/incremental)
            tables: 指定要备份的表（可选）
            compress: 是否压缩
            encryption: 是否加密
            description: 备份描述

        Returns:
            Dict: 备份结果
        """
        try:
            # 生成备份ID和时间戳
            backup_id = self._generate_backup_id()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 确定备份文件名
            suffix = '.sql'
            if compress:
                suffix += '.gz'
            backup_filename = f"{backup_type}_{timestamp}_{backup_id}{suffix}"
            backup_path = os.path.join(self.BACKUP_DIR, backup_filename)

            # 确保备份目录存在
            os.makedirs(self.BACKUP_DIR, exist_ok=True)

            # 记录备份开始
            self._log_backup(backup_id, backup_type, 'running', backup_path, description)

            # 执行备份命令
            result = self._execute_backup(
                backup_path,
                backup_type,
                tables,
                compress
            )

            if not result['success']:
                self._log_backup(backup_id, backup_type, 'failed', None, result.get('error'))
                return result

            # 计算文件大小和校验和
            file_size = os.path.getsize(backup_path)
            checksum = self._calculate_checksum(backup_path)

            # 记录备份完成
            self._log_backup(
                backup_id,
                backup_type,
                'completed',
                backup_path,
                f"file_size={file_size}, checksum={checksum}"
            )

            # 清理过期备份
            self._cleanup_old_backups()

            logger.info(f"备份成功: backup_id={backup_id}, path={backup_path}, size={file_size}")

            return {
                'success': True,
                'msg': '备份创建成功',
                'backup_id': backup_id,
                'backup_path': backup_path,
                'file_size': file_size,
                'checksum': checksum,
                'backup_type': backup_type
            }

        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return {'success': False, 'msg': f'备份失败: {str(e)}'}

    def restore_backup(self, backup_id: str = None, backup_path: str = None,
                      tables: List[str] = None, force: bool = False) -> Dict[str, Any]:
        """
        恢复数据库备份

        Args:
            backup_id: 备份ID
            backup_path: 备份文件路径
            tables: 指定要恢复的表（可选）
            force: 是否强制恢复

        Returns:
            Dict: 恢复结果
        """
        try:
            # 获取备份文件路径
            if backup_id:
                backup_info = self.get_backup(backup_id)
                if not backup_info:
                    return {'success': False, 'msg': '备份记录不存在'}
                backup_path = backup_info.get('backup_path')

            if not backup_path or not os.path.exists(backup_path):
                return {'success': False, 'msg': '备份文件不存在'}

            # 安全检查
            if not force:
                # 检查备份文件完整性
                if not self._verify_backup(backup_path):
                    return {'success': False, 'msg': '备份文件损坏'}

            # 执行恢复前检查
            check_result = self._pre_restore_check()
            if not check_result['safe'] and not force:
                return {
                    'success': False,
                    'msg': f"恢复风险: {check_result['reason']}",
                    'warnings': check_result.get('warnings', [])
                }

            # 创建恢复前备份（防止数据丢失）
            pre_backup = self.create_backup(
                backup_type=self.BACKUP_TYPE_FULL,
                description=f'恢复前自动备份 (restore_id={backup_id})'
            )
            if not pre_backup['success']:
                logger.warning(f"恢复前备份创建失败: {pre_backup['msg']}")

            # 执行恢复命令
            result = self._execute_restore(backup_path, tables)

            if result['success']:
                logger.info(f"数据恢复成功: backup_id={backup_id}, path={backup_path}")
            else:
                logger.error(f"数据恢复失败: backup_id={backup_id}, error={result.get('msg')}")

            return result

        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return {'success': False, 'msg': f'恢复失败: {str(e)}'}

    def get_backup(self, backup_id: str) -> Optional[Dict]:
        """
        获取备份详情

        Args:
            backup_id: 备份ID

        Returns:
            Dict: 备份详情
        """
        try:
            # 从数据库获取备份记录
            backup = db.get_one(
                "SELECT * FROM business_backups WHERE backup_id=%s AND deleted=0",
                [backup_id]
            )
            return backup
        except Exception as e:
            logger.error(f"获取备份详情失败: {e}")
            return None

    def list_backups(self, backup_type: str = None, status: str = None,
                   date_from: str = None, date_to: str = None,
                   limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        获取备份列表

        Args:
            backup_type: 备份类型
            status: 备份状态
            date_from: 开始日期
            date_to: 结束日期
            limit: 返回数量
            offset: 偏移量

        Returns:
            List[Dict]: 备份列表
        """
        try:
            where_clauses = ["deleted=0"]
            params = []

            if backup_type:
                where_clauses.append("backup_type=%s")
                params.append(backup_type)

            if status:
                where_clauses.append("status=%s")
                params.append(status)

            if date_from:
                where_clauses.append("created_at >= %s")
                params.append(date_from)

            if date_to:
                where_clauses.append("created_at <= %s")
                params.append(date_to + ' 23:59:59')

            where_sql = " AND ".join(where_clauses)

            sql = f"""
                SELECT * FROM business_backups
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])

            backups = db.get_all(sql, params) or []
            
            # 格式化文件大小
            for backup in backups:
                if backup.get('file_size'):
                    backup['file_size_formatted'] = self._format_size(backup['file_size'])

            return backups

        except Exception as e:
            logger.error(f"获取备份列表失败: {e}")
            return []

    def delete_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        删除备份

        Args:
            backup_id: 备份ID

        Returns:
            Dict: 删除结果
        """
        try:
            backup = self.get_backup(backup_id)
            if not backup:
                return {'success': False, 'msg': '备份不存在'}

            # 删除物理文件
            backup_path = backup.get('backup_path')
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
                logger.info(f"删除备份文件: {backup_path}")

            # 更新数据库记录
            db.execute(
                "UPDATE business_backups SET deleted=1 WHERE backup_id=%s",
                [backup_id]
            )

            return {'success': True, 'msg': '备份删除成功'}

        except Exception as e:
            logger.error(f"删除备份失败: {e}")
            return {'success': False, 'msg': f'删除失败: {str(e)}'}

    def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        验证备份文件完整性

        Args:
            backup_id: 备份ID

        Returns:
            Dict: 验证结果
        """
        try:
            backup = self.get_backup(backup_id)
            if not backup:
                return {'success': False, 'msg': '备份不存在'}

            backup_path = backup.get('backup_path')
            if not backup_path or not os.path.exists(backup_path):
                return {'success': False, 'msg': '备份文件不存在'}

            # 验证文件大小
            actual_size = os.path.getsize(backup_path)
            expected_size = backup.get('file_size', 0)

            size_match = actual_size == expected_size

            # 验证校验和
            actual_checksum = self._calculate_checksum(backup_path)
            expected_checksum = backup.get('checksum', '')

            checksum_match = actual_checksum == expected_checksum

            # 验证SQL文件内容
            sql_valid = self._verify_backup(backup_path)

            return {
                'success': True,
                'backup_id': backup_id,
                'size_match': size_match,
                'checksum_match': checksum_match,
                'sql_valid': sql_valid,
                'is_valid': size_match and checksum_match and sql_valid,
                'details': {
                    'actual_size': actual_size,
                    'expected_size': expected_size,
                    'actual_checksum': actual_checksum,
                    'expected_checksum': expected_checksum
                }
            }

        except Exception as e:
            logger.error(f"验证备份失败: {e}")
            return {'success': False, 'msg': f'验证失败: {str(e)}'}

    # ============ 定时任务接口 ============

    def scheduled_full_backup(self) -> Dict[str, Any]:
        """
        定时全量备份（每日凌晨2点执行）
        """
        logger.info("开始执行定时全量备份")
        return self.create_backup(
            backup_type=self.BACKUP_TYPE_FULL,
            description='定时全量备份'
        )

    def scheduled_incremental_backup(self) -> Dict[str, Any]:
        """
        定时增量备份（每小时执行）
        """
        logger.info("开始执行定时增量备份")
        return self.create_backup(
            backup_type=self.BACKUP_TYPE_INCREMENTAL,
            description='定时增量备份'
        )

    # ============ 内部方法 ============

    def _generate_backup_id(self) -> str:
        """生成备份ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        import uuid
        return f"BK{timestamp}{uuid.uuid4().hex[:8].upper()}"

    def _log_backup(self, backup_id: str, backup_type: str, status: str,
                   backup_path: str = None, details: str = None):
        """记录备份日志"""
        try:
            sql = """
                INSERT INTO business_backups
                (backup_id, backup_type, status, backup_path, file_size, details)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                status=%s, updated_at=NOW(), details=%s
            """
            db.execute(sql, [
                backup_id, backup_type, status, backup_path, 0, details,
                status, details
            ])
        except Exception as e:
            logger.warning(f"记录备份日志失败: {e}")

    def _execute_backup(self, backup_path: str, backup_type: str,
                       tables: List[str] = None, compress: bool = True) -> Dict[str, Any]:
        """执行备份命令"""
        try:
            # 构建mysqldump命令
            cmd = [
                'mysqldump',
                f'--host={self.MYSQL_HOST}',
                f'--port={self.MYSQL_PORT}',
                f'--user={self.MYSQL_USER}',
                f'--password={self.MYSQL_PASSWORD}',
                '--single-transaction',
                '--quick',
                '--lock-tables=false',
                '--routines',
                '--triggers',
                '--events',
            ]

            # 如果是全量备份，包含所有表；否则只备份数据变更
            if backup_type == self.BACKUP_TYPE_FULL:
                cmd.append('--all-databases')
            else:
                cmd.append(self.MYSQL_DATABASE)
                if tables:
                    cmd.extend(tables)

            # 重定向输出
            if backup_path.endswith('.gz'):
                # 使用gzip压缩
                sql_file = backup_path[:-3]
                cmd_str = ' '.join(cmd)
                full_cmd = f"({cmd_str}) | gzip > {backup_path}"
            else:
                cmd_str = ' '.join(cmd)
                full_cmd = f"{cmd_str} > {backup_path}"

            # 执行命令
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            if result.returncode != 0:
                return {
                    'success': False,
                    'msg': f"备份命令执行失败: {result.stderr}"
                }

            return {'success': True}

        except subprocess.TimeoutExpired:
            return {'success': False, 'msg': '备份超时'}
        except Exception as e:
            return {'success': False, 'msg': str(e)}

    def _execute_restore(self, backup_path: str, tables: List[str] = None) -> Dict[str, Any]:
        """执行恢复命令"""
        try:
            # 如果是压缩文件，先解压
            if backup_path.endswith('.gz'):
                import gzip
                sql_file = backup_path[:-3]
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(sql_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path = sql_file

            # 构建mysql命令
            cmd = [
                'mysql',
                f'--host={self.MYSQL_HOST}',
                f'--port={self.MYSQL_PORT}',
                f'--user={self.MYSQL_USER}',
                f'--password={self.MYSQL_PASSWORD}',
            ]

            if tables:
                # 只恢复指定表
                cmd.append(self.MYSQL_DATABASE)
                cmd_str = ' '.join(cmd)
                for table in tables:
                    table_cmd = f"{cmd_str} -e 'source {backup_path}'"
            else:
                # 恢复整个数据库
                cmd.append(self.MYSQL_DATABASE)
                cmd_str = ' '.join(cmd)
                table_cmd = f"{cmd_str} < {backup_path}"

            # 执行命令
            result = subprocess.run(
                table_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            if result.returncode != 0:
                return {
                    'success': False,
                    'msg': f"恢复命令执行失败: {result.stderr}"
                }

            return {'success': True, 'msg': '数据恢复成功'}

        except subprocess.TimeoutExpired:
            return {'success': False, 'msg': '恢复超时'}
        except Exception as e:
            return {'success': False, 'msg': str(e)}

    def _calculate_checksum(self, file_path: str) -> str:
        """计算文件MD5校验和"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()

    def _verify_backup(self, backup_path: str) -> bool:
        """验证SQL备份文件"""
        try:
            if backup_path.endswith('.gz'):
                import gzip
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    content = f.read(1000)
            else:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)

            # 检查是否包含MySQLDump头部
            return 'MySQL dump' in content or 'mysqldump' in content
        except Exception as e:
            logger.warning(f"验证备份文件失败: {e}")
            return False

    def _pre_restore_check(self) -> Dict:
        """恢复前检查"""
        warnings = []

        # 检查数据库连接
        try:
            db.get_one("SELECT 1")
        except Exception as e:
            return {'safe': False, 'reason': f'数据库连接失败: {e}'}

        # 检查磁盘空间
        import shutil
        disk_usage = shutil.disk_usage(self.BACKUP_DIR)
        if disk_usage.free < 1024 * 1024 * 1024:  # 小于1GB
            warnings.append('磁盘空间不足')

        return {'safe': True, 'warnings': warnings}

    def _cleanup_old_backups(self):
        """清理过期备份"""
        try:
            # 获取超过保留期限的备份
            cutoff_date = (datetime.now() - timedelta(days=self.MAX_BACKUP_RETENTION)).strftime('%Y-%m-%d')
            
            old_backups = self.list_backups(
                date_to=cutoff_date,
                status=self.STATUS_COMPLETED,
                limit=100
            )

            for backup in old_backups:
                self.delete_backup(backup['backup_id'])
                logger.info(f"清理过期备份: {backup['backup_id']}")

        except Exception as e:
            logger.warning(f"清理过期备份失败: {e}")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f}TB"


# 单例实例
backup_service = BackupService()
