"""
Application Repository
申请单数据访问层
"""
import logging
from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ApplicationRepository(BaseRepository):
    """申请单仓储类"""
    
    TABLE_NAME = 'business_applications'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'
    
    # ============ 用户端查询 ============
    
    def find_by_user(self, 
                     user_id: str,
                     status: str = None,
                     type_code: str = None,
                     page: int = 1,
                     page_size: int = 20) -> Dict[str, Any]:
        """
        查询用户的申请列表
        
        Args:
            user_id: 用户ID
            status: 状态筛选 (可选)
            type_code: 类型筛选 (可选)
            page: 页码
            page_size: 每页数量
            
        Returns:
            {'items': [...], 'total': n, 'page': n, 'page_size': n}
        """
        offset = (page - 1) * page_size
        
        # 构建 WHERE 条件
        conditions = ["user_id = %s", "deleted = 0"]
        params = [user_id]
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        if type_code:
            conditions.append("(type_code = %s OR app_type = %s)")
            params.extend([type_code, type_code])
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where_clause}"
        count_result = self.db.get_one(count_sql, params.copy())
        total = count_result.get('cnt', 0) if count_result else 0
        
        # 查询数据
        data_sql = f"""
            SELECT id, fid, application_no, app_no, type_code, app_type,
                   title, status, priority, user_id, user_name,
                   approver_id, approver_name, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        items = self.db.get_all(data_sql, params + [page_size, offset]) or []
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }
    
    def find_detail_by_id(self, 
                          app_id: int, 
                          user_id: str = None) -> Optional[Dict[str, Any]]:
        """
        查询申请详情
        
        Args:
            app_id: 申请ID
            user_id: 用户ID (用于权限校验，可选)
            
        Returns:
            申请详情或 None
        """
        conditions = ["id = %s", "deleted = 0"]
        params = [app_id]
        
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where_clause} LIMIT 1"
        
        return self.db.get_one(sql, params)
    
    def find_detail_by_fid(self, 
                           fid: str,
                           user_id: str = None) -> Optional[Dict[str, Any]]:
        """
        根据 FID 查询申请详情 (V47.0)
        
        Args:
            fid: 申请FID
            user_id: 用户ID (用于权限校验，可选)
            
        Returns:
            申请详情或 None
        """
        conditions = ["fid = %s", "deleted = 0"]
        params = [fid]
        
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where_clause} LIMIT 1"
        
        return self.db.get_one(sql, params)
    
    def find_by_application_no(self, application_no: str) -> Optional[Dict[str, Any]]:
        """根据申请编号查询"""
        sql = f"""
            SELECT * FROM {self.TABLE_NAME} 
            WHERE (application_no = %s OR app_no = %s) AND deleted = 0
            LIMIT 1
        """
        return self.db.get_one(sql, [application_no, application_no])
    
    # ============ 统计查询 ============
    
    def count_by_user_and_status(self, 
                                  user_id: str, 
                                  status: str = None) -> int:
        """统计用户的申请数量"""
        if status:
            sql = f"""
                SELECT COUNT(*) as cnt FROM {self.TABLE_NAME}
                WHERE user_id = %s AND status = %s AND deleted = 0
            """
            result = self.db.get_one(sql, [user_id, status])
        else:
            sql = f"""
                SELECT COUNT(*) as cnt FROM {self.TABLE_NAME}
                WHERE user_id = %s AND deleted = 0
            """
            result = self.db.get_one(sql, [user_id])
        
        return result.get('cnt', 0) if result else 0
    
    def get_user_stats(self, user_id: str) -> Dict[str, int]:
        """获取用户申请统计"""
        sql = f"""
            SELECT 
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                COUNT(*) as total
            FROM {self.TABLE_NAME}
            WHERE user_id = %s AND deleted = 0
        """
        result = self.db.get_one(sql, [user_id])
        
        if result:
            return {
                'pending': int(result.get('pending', 0) or 0),
                'processing': int(result.get('processing', 0) or 0),
                'completed': int(result.get('completed', 0) or 0),
                'cancelled': int(result.get('cancelled', 0) or 0),
                'total': int(result.get('total', 0) or 0)
            }
        return {'pending': 0, 'processing': 0, 'completed': 0, 'cancelled': 0, 'total': 0}
    
    # ============ 更新操作 ============
    
    def update_status(self, 
                      app_id: int,
                      status: str,
                      approver_id: int = None,
                      approver_name: str = None,
                      remark: str = None) -> int:
        """更新申请状态"""
        data = {'status': status}
        
        if approver_id is not None:
            data['approver_id'] = approver_id
        if approver_name is not None:
            data['approver_name'] = approver_name
        if remark is not None:
            data['approve_remark'] = remark
        
        return self.update(app_id, data)
    
    def cancel(self, app_id: int, user_id: str = None) -> bool:
        """取消申请，返回是否成功"""
        conditions = ["id = %s", "status = 'pending'", "deleted = 0"]
        params = [app_id]
        
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        
        where_clause = " AND ".join(conditions)
        sql = f"""
            UPDATE {self.TABLE_NAME} 
            SET status = 'cancelled', updated_at = NOW()
            WHERE {where_clause}
        """
        
        affected = self.db.execute(sql, params)
        return affected > 0
    
    # ============ 管理后台查询 ============
    
    def find_all_with_filters(self,
                              ec_id: str = None,
                              project_id: str = None,
                              status: str = None,
                              type_code: str = None,
                              keyword: str = None,
                              page: int = 1,
                              page_size: int = 20) -> Dict[str, Any]:
        """
        管理后台查询申请列表（支持多条件筛选）
        """
        offset = (page - 1) * page_size
        
        conditions = ["a.deleted = 0"]
        params = []
        
        if ec_id:
            conditions.append("a.ec_id = %s")
            params.append(ec_id)
        
        if project_id:
            conditions.append("a.project_id = %s")
            params.append(project_id)
        
        if status:
            conditions.append("a.status = %s")
            params.append(status)
        
        if type_code:
            conditions.append("(a.type_code = %s OR a.app_type = %s)")
            params.extend([type_code, type_code])
        
        if keyword:
            conditions.append("(a.title LIKE %s OR a.user_name LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} a WHERE {where_clause}"
        count_result = self.db.get_one(count_sql, params.copy())
        total = count_result.get('cnt', 0) if count_result else 0
        
        # 查询数据
        data_sql = f"""
            SELECT a.*, t.type_name, t.category
            FROM {self.TABLE_NAME} a
            LEFT JOIN business_application_types t 
                ON (a.type_code = t.type_code OR a.app_type = t.type_code)
            WHERE {where_clause}
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
        """
        items = self.db.get_all(data_sql, params + [page_size, offset]) or []
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }
