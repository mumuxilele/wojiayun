"""
Order Repository
订单数据访问层
"""
import logging
from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository):
    """订单仓储类"""
    
    TABLE_NAME = 'business_orders'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'
    
    # ============ 用户端查询 ============
    
    def find_by_user(self,
                     user_id: str,
                     status: str = None,
                     page: int = 1,
                     page_size: int = 20) -> Dict[str, Any]:
        """查询用户的订单列表"""
        offset = (page - 1) * page_size
        
        conditions = ["user_id = %s", "deleted = 0"]
        params = [user_id]
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where_clause}"
        count_result = self.db.get_one(count_sql, params.copy())
        total = count_result.get('cnt', 0) if count_result else 0
        
        # 查询数据
        data_sql = f"""
            SELECT id, fid, order_no, user_id, user_name, total_amount,
                   actual_amount, status, pay_status, receiver_name,
                   created_at, updated_at
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
                          order_id: int,
                          user_id: str = None) -> Optional[Dict[str, Any]]:
        """查询订单详情"""
        conditions = ["id = %s", "deleted = 0"]
        params = [order_id]
        
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where_clause} LIMIT 1"
        
        return self.db.get_one(sql, params)
    
    def find_by_order_no(self, order_no: str) -> Optional[Dict[str, Any]]:
        """根据订单号查询"""
        sql = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE order_no = %s AND deleted = 0
            LIMIT 1
        """
        return self.db.get_one(sql, [order_no])
    
    # ============ 统计 ============
    
    def count_by_user(self, user_id: str) -> int:
        """统计用户的订单数量"""
        sql = f"""
            SELECT COUNT(*) as cnt FROM {self.TABLE_NAME}
            WHERE user_id = %s AND deleted = 0
        """
        result = self.db.get_one(sql, [user_id])
        return result.get('cnt', 0) if result else 0
    
    def get_user_order_stats(self, user_id: str) -> Dict[str, int]:
        """获取用户订单统计"""
        sql = f"""
            SELECT 
                SUM(CASE WHEN status = 'pending_payment' THEN 1 ELSE 0 END) as pending_payment,
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid,
                SUM(CASE WHEN status = 'shipped' THEN 1 ELSE 0 END) as shipped,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                COUNT(*) as total
            FROM {self.TABLE_NAME}
            WHERE user_id = %s AND deleted = 0
        """
        result = self.db.get_one(sql, [user_id])
        
        if result:
            return {
                'pending_payment': int(result.get('pending_payment', 0) or 0),
                'paid': int(result.get('paid', 0) or 0),
                'shipped': int(result.get('shipped', 0) or 0),
                'completed': int(result.get('completed', 0) or 0),
                'total': int(result.get('total', 0) or 0)
            }
        return {'pending_payment': 0, 'paid': 0, 'shipped': 0, 'completed': 0, 'total': 0}
    
    # ============ 更新 ============
    
    def update_status(self, order_id: int, status: str) -> int:
        """更新订单状态"""
        return self.update(order_id, {'status': status})
    
    def update_pay_status(self, order_id: int, pay_status: int) -> int:
        """更新支付状态"""
        data = {
            'pay_status': pay_status,
            'pay_time': 'NOW()' if pay_status == 1 else None
        }
        return self.update(order_id, data)
    
    # ============ 管理后台查询 ============
    
    def find_all_with_filters(self,
                              ec_id: str = None,
                              project_id: str = None,
                              status: str = None,
                              keyword: str = None,
                              page: int = 1,
                              page_size: int = 20) -> Dict[str, Any]:
        """管理后台查询订单列表"""
        offset = (page - 1) * page_size
        
        conditions = ["deleted = 0"]
        params = []
        
        if ec_id:
            conditions.append("ec_id = %s")
            params.append(ec_id)
        
        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        if keyword:
            conditions.append("(order_no LIKE %s OR user_name LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where_clause}"
        count_result = self.db.get_one(count_sql, params.copy())
        total = count_result.get('cnt', 0) if count_result else 0
        
        # 查询数据
        data_sql = f"""
            SELECT * FROM {self.TABLE_NAME}
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
