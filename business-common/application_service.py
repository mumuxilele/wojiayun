"""
企业应用配置服务 V45.0 + V29.0 申请服务
用于管理企业开放平台的AppKey/AppSecret配置 + 申请类型管理
"""
import logging
from typing import Optional, Dict, Any, List
from . import db

logger = logging.getLogger(__name__)


class ApplicationService:
    """企业应用配置服务 + 申请类型服务"""
    
    # ==================== V29.0 申请类型服务 ====================
    
    @staticmethod
    def get_application_types(category: str = None) -> List[Dict[str, Any]]:
        """
        获取申请类型列表
        
        Args:
            category: 分类筛选（可选）
            
        Returns:
            申请类型列表
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
                SELECT type_code, type_name, category, icon, description,
                       form_config, approval_config, status, sort_order
                FROM business_application_types 
                WHERE status = 1
            """
            params = []
            
            if category:
                sql += " AND category = %s"
                params.append(category)
            
            sql += " ORDER BY sort_order ASC, id ASC"
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # 解析 JSON 字段
            for item in results:
                import json
                try:
                    if item.get('form_config'):
                        item['form_config'] = json.loads(item['form_config'])
                except:
                    item['form_config'] = {}
                try:
                    if item.get('approval_config'):
                        item['approval_config'] = json.loads(item['approval_config'])
                except:
                    item['approval_config'] = {}
            
            return results
            
        except Exception as e:
            logger.error(f"获取申请类型列表失败: error={str(e)}")
            return []
    
    @staticmethod
    def get_application_type(type_code: str) -> Optional[Dict[str, Any]]:
        """
        获取申请类型详情
        
        Args:
            type_code: 申请类型代码
            
        Returns:
            申请类型详情，不存在则返回None
        """
        if not type_code:
            return None
            
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
                SELECT type_code, type_name, category, icon, description,
                       form_config, approval_config, status, sort_order
                FROM business_application_types 
                WHERE type_code = %s AND status = 1
            """
            cursor.execute(sql, (type_code,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                import json
                try:
                    if result.get('form_config'):
                        result['form_config'] = json.loads(result['form_config'])
                except:
                    result['form_config'] = {}
                try:
                    if result.get('approval_config'):
                        result['approval_config'] = json.loads(result['approval_config'])
                except:
                    result['approval_config'] = {}
            
            return result
            
        except Exception as e:
            logger.error(f"获取申请类型详情失败: type_code={type_code}, error={str(e)}")
            return None
    
    # ==================== V45.0 企业应用配置服务 ====================
    
    @staticmethod
    def get_app_config(ec_id: str) -> Optional[Dict[str, Any]]:
        """
        根据企业ID获取应用配置
        
        Args:
            ec_id: 企业ID
            
        Returns:
            应用配置字典，包含app_key和app_secret，不存在则返回None
        """
        if not ec_id:
            return None
            
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
                SELECT id, ec_id, app_key, app_secret, app_name, status, created_at, updated_at
                FROM t_bdc_application 
                WHERE ec_id = %s AND status = 1
            """
            cursor.execute(sql, (ec_id,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return result
            
        except Exception as e:
            logger.error(f"获取企业应用配置失败: ec_id={ec_id}, error={str(e)}")
            return None
    
    @staticmethod
    def get_app_credentials(ec_id: str) -> Optional[Dict[str, str]]:
        """
        根据企业ID获取AppKey和AppSecret
        
        Args:
            ec_id: 企业ID
            
        Returns:
            {'app_key': xxx, 'app_secret': xxx} 或 None
        """
        config = ApplicationService.get_app_config(ec_id)
        if not config:
            return None
            
        return {
            'app_key': config.get('app_key'),
            'app_secret': config.get('app_secret')
        }
    
    @staticmethod
    def create_app_config(ec_id: str, app_key: str, app_secret: str, app_name: str = None) -> bool:
        """
        创建企业应用配置
        
        Args:
            ec_id: 企业ID
            app_key: AppKey
            app_secret: AppSecret
            app_name: 应用名称（可选）
            
        Returns:
            是否创建成功
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            sql = """
                INSERT INTO t_bdc_application (ec_id, app_key, app_secret, app_name)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    app_key = VALUES(app_key),
                    app_secret = VALUES(app_secret),
                    app_name = VALUES(app_name),
                    status = 1,
                    updated_at = NOW()
            """
            cursor.execute(sql, (ec_id, app_key, app_secret, app_name))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"创建企业应用配置失败: ec_id={ec_id}, error={str(e)}")
            return False
    
    @staticmethod
    def update_app_config(ec_id: str, app_key: str = None, app_secret: str = None, 
                          app_name: str = None, status: int = None) -> bool:
        """
        更新企业应用配置
        
        Args:
            ec_id: 企业ID
            app_key: AppKey（可选）
            app_secret: AppSecret（可选）
            app_name: 应用名称（可选）
            status: 状态（可选）
            
        Returns:
            是否更新成功
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if app_key is not None:
                updates.append("app_key = %s")
                params.append(app_key)
            if app_secret is not None:
                updates.append("app_secret = %s")
                params.append(app_secret)
            if app_name is not None:
                updates.append("app_name = %s")
                params.append(app_name)
            if status is not None:
                updates.append("status = %s")
                params.append(status)
                
            if not updates:
                return True
                
            params.append(ec_id)
            sql = f"UPDATE t_bdc_application SET {', '.join(updates)} WHERE ec_id = %s"
            cursor.execute(sql, params)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"更新企业应用配置失败: ec_id={ec_id}, error={str(e)}")
            return False
    
    @staticmethod
    def delete_app_config(ec_id: str) -> bool:
        """
        删除企业应用配置（软删除，设置status=0）
        
        Args:
            ec_id: 企业ID
            
        Returns:
            是否删除成功
        """
        return ApplicationService.update_app_config(ec_id, status=0)
    
    # ==================== V29.0 申请单服务 ====================
    
    @staticmethod
    def create_application(user_id: str, user_name: str, user_phone: str, 
                          type_code: str, title: str, form_data: Dict[str, Any],
                          ec_id: str, project_id: str = None, 
                          attachments: List[Dict] = None, remark: str = None) -> Dict[str, Any]:
        """
        创建申请单
        
        Args:
            user_id: 用户ID
            user_name: 用户姓名
            user_phone: 用户手机号
            type_code: 申请类型代码
            title: 申请标题
            form_data: 表单数据
            ec_id: 企业ID
            project_id: 项目ID（可选）
            attachments: 附件列表（可选）
            remark: 备注（可选）
            
        Returns:
            {'success': True/False, 'msg': '消息', 'data': {...}}
        """
        import json
        import hashlib
        import time
        
        try:
            # 生成FID（32位字符串）
            fid = hashlib.md5(f"{user_id}{type_code}{time.time()}".encode()).hexdigest()
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # 生成申请编号
            today = time.strftime('%Y%m%d')
            cursor.execute("SELECT COUNT(*) as cnt FROM business_applications WHERE application_no LIKE %s", (f"APP{today}%",))
            count = cursor.fetchone()[0] + 1
            application_no = f"APP{today}{count:05d}"
            
            # 插入申请记录
            sql = """
                INSERT INTO business_applications 
                (fid, application_no, user_id, user_name, user_phone, type_code, 
                 title, form_data, ec_id, project_id, attachments, remark,
                 status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            cursor.execute(sql, (
                fid, application_no, user_id, user_name, user_phone, type_code,
                title, json.dumps(form_data or {}, ensure_ascii=False),
                ec_id, project_id,
                json.dumps(attachments or [], ensure_ascii=False) if attachments else None,
                remark, 'pending'
            ))
            
            conn.commit()
            application_id = cursor.lastrowid
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'msg': '申请提交成功',
                'data': {
                    'id': application_id,
                    'fid': fid,
                    'application_no': application_no,
                    'status': 'pending'
                }
            }
            
        except Exception as e:
            logger.error(f"创建申请单失败: error={str(e)}")
            return {'success': False, 'msg': f'提交失败: {str(e)}'}
    
    @staticmethod
    def get_user_applications(user_id: str, type_code: str = None, status: str = None,
                              keyword: str = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        获取用户的申请列表
        
        Args:
            user_id: 用户ID
            type_code: 申请类型筛选（可选）
            status: 状态筛选（可选）
            keyword: 关键词搜索（可选）
            page: 页码
            page_size: 每页数量
            
        Returns:
            {'list': [...], 'total': n}
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            where_clauses = ['a.user_id = %s', 'a.is_deleted = 0']
            params = [user_id]
            
            if type_code:
                where_clauses.append('a.type_code = %s')
                params.append(type_code)
            
            if status:
                where_clauses.append('a.status = %s')
                params.append(status)
            
            if keyword:
                where_clauses.append('(a.title LIKE %s OR a.application_no LIKE %s)')
                params.extend([f'%{keyword}%', f'%{keyword}%'])
            
            # 统计总数
            count_sql = f"""
                SELECT COUNT(*) as total 
                FROM business_applications a
                WHERE {' AND '.join(where_clauses)}
            """
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # 查询列表
            list_sql = f"""
                SELECT a.id, a.fid, a.application_no, a.type_code, 
                       t.type_name, t.icon, a.title, a.status,
                       a.created_at, a.updated_at, a.is_favorite
                FROM business_applications a
                LEFT JOIN business_application_types t ON a.type_code = t.type_code
                WHERE {' AND '.join(where_clauses)}
                ORDER BY a.is_favorite DESC, a.created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(list_sql, params + [page_size, (page - 1) * page_size])
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {'list': results, 'total': total, 'page': page, 'page_size': page_size}
            
        except Exception as e:
            logger.error(f"获取用户申请列表失败: error={str(e)}")
            return {'list': [], 'total': 0}
    
    @staticmethod
    def get_application_detail(app_id: int, user_id: str = None, is_staff: bool = False) -> Optional[Dict[str, Any]]:
        """
        获取申请详情
        
        Args:
            app_id: 申请ID
            user_id: 用户ID（用于权限校验，可选）
            is_staff: 是否为员工查询
            
        Returns:
            申请详情字典，不存在则返回None
        """
        import json
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
                SELECT a.*, t.type_name, t.icon, t.form_config, t.approval_config
                FROM business_applications a
                LEFT JOIN business_application_types t ON a.type_code = t.type_code
                WHERE a.id = %s AND a.is_deleted = 0
            """
            params = [app_id]
            
            if user_id and not is_staff:
                sql += " AND a.user_id = %s"
                params.append(user_id)
            
            cursor.execute(sql, params)
            result = cursor.fetchone()
            
            if result:
                # 解析JSON字段
                try:
                    if result.get('form_data'):
                        result['form_data'] = json.loads(result['form_data'])
                except:
                    result['form_data'] = {}
                try:
                    if result.get('attachments'):
                        result['attachments'] = json.loads(result['attachments'])
                except:
                    result['attachments'] = []
                try:
                    if result.get('approval_config'):
                        result['approval_config'] = json.loads(result['approval_config'])
                except:
                    result['approval_config'] = {}
            
            cursor.close()
            conn.close()
            
            return result
            
        except Exception as e:
            logger.error(f"获取申请详情失败: error={str(e)}")
            return None
    
    @staticmethod
    def cancel_application(app_id: int, user_id: str) -> Dict[str, Any]:
        """
        取消申请
        
        Args:
            app_id: 申请ID
            user_id: 用户ID
            
        Returns:
            {'success': True/False, 'msg': '消息'}
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 检查是否属于该用户且状态允许取消
            cursor.execute(
                "SELECT status FROM business_applications WHERE id = %s AND user_id = %s AND is_deleted = 0",
                (app_id, user_id)
            )
            result = cursor.fetchone()
            
            if not result:
                cursor.close()
                conn.close()
                return {'success': False, 'msg': '申请不存在'}
            
            if result['status'] in ['approved', 'rejected']:
                cursor.close()
                conn.close()
                return {'success': False, 'msg': '已审批的申请不能取消'}
            
            # 更新状态
            cursor.execute(
                "UPDATE business_applications SET status = 'cancelled', updated_at = NOW() WHERE id = %s",
                (app_id,)
            )
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return {'success': True, 'msg': '申请已取消'}
            
        except Exception as e:
            logger.error(f"取消申请失败: error={str(e)}")
            return {'success': False, 'msg': f'取消失败: {str(e)}'}
    
    @staticmethod
    def set_favorite(app_id: int, user_id: str, is_favorite: int) -> Dict[str, Any]:
        """
        设置/取消常用申请
        
        Args:
            app_id: 申请ID
            user_id: 用户ID
            is_favorite: 1-设为常用, 0-取消常用
            
        Returns:
            {'success': True/False, 'msg': '消息'}
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE business_applications SET is_favorite = %s, updated_at = NOW() WHERE id = %s AND user_id = %s",
                (is_favorite, app_id, user_id)
            )
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return {'success': True, 'msg': '设置成功'}
            
        except Exception as e:
            logger.error(f"设置常用申请失败: error={str(e)}")
            return {'success': False, 'msg': f'设置失败: {str(e)}'}
    
    @staticmethod
    def list_app_configs(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        分页获取应用配置列表
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            {'list': [...], 'total': n}
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 统计总数
            cursor.execute("SELECT COUNT(*) as total FROM t_bdc_application WHERE status = 1")
            total = cursor.fetchone()['total']
            
            # 分页查询
            offset = (page - 1) * page_size
            sql = """
                SELECT id, ec_id, app_key, app_name, status, created_at, updated_at
                FROM t_bdc_application 
                WHERE status = 1
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (page_size, offset))
            items = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {'list': items, 'total': total}
            
        except Exception as e:
            logger.error(f"获取应用配置列表失败: error={str(e)}")
            return {'list': [], 'total': 0}


# 便捷实例
application_service = ApplicationService()
