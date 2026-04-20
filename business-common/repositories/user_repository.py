"""
User Repository
用户数据访问层
"""
import logging
from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """用户仓储类"""
    
    TABLE_NAME = 'business_users'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'
    
    # ============ 查询 ============
    
    def find_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据 user_id 查询用户"""
        sql = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE user_id = %s AND deleted = 0
            LIMIT 1
        """
        return self.db.get_one(sql, [user_id])
    
    def find_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """根据手机号查询用户"""
        sql = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE phone = %s AND deleted = 0
            LIMIT 1
        """
        return self.db.get_one(sql, [phone])
    
    def find_by_ec(self, 
                   ec_id: str,
                   project_id: str = None,
                   page: int = 1,
                   page_size: int = 20) -> Dict[str, Any]:
        """查询企业下的用户列表"""
        offset = (page - 1) * page_size
        
        conditions = ["ec_id = %s", "deleted = 0"]
        params = [ec_id]
        
        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where_clause}"
        count_result = self.db.get_one(count_sql, params.copy())
        total = count_result.get('cnt', 0) if count_result else 0
        
        # 查询数据
        data_sql = f"""
            SELECT id, fid, user_id, user_name, phone, avatar,
                   ec_id, project_id, status, created_at, updated_at
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
    
    # ============ 统计 ============
    
    def count_by_ec(self, ec_id: str, project_id: str = None) -> int:
        """统计企业下的用户数量"""
        if project_id:
            sql = f"""
                SELECT COUNT(*) as cnt FROM {self.TABLE_NAME}
                WHERE ec_id = %s AND project_id = %s AND deleted = 0
            """
            result = self.db.get_one(sql, [ec_id, project_id])
        else:
            sql = f"""
                SELECT COUNT(*) as cnt FROM {self.TABLE_NAME}
                WHERE ec_id = %s AND deleted = 0
            """
            result = self.db.get_one(sql, [ec_id])
        
        return result.get('cnt', 0) if result else 0
    
    # ============ 更新 ============
    
    def update_status(self, user_id: int, status: int) -> int:
        """更新用户状态"""
        return self.update(user_id, {'status': status})
