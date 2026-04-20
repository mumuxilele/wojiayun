"""
Repository 基类
提供通用的数据访问方法
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseRepository:
    """
    仓储基类
    
    所有 Repository 继承此类，获得标准的 CRUD 操作
    """
    
    # 表名，子类必须覆盖
    TABLE_NAME: str = ''
    
    # 主键字段名
    PRIMARY_KEY: str = 'id'
    
    # 默认排序字段
    DEFAULT_ORDER: str = 'id DESC'
    
    def __init__(self):
        """初始化，延迟导入 db 避免循环依赖"""
        from business_common import db
        self.db = db
    
    # ============ 基础查询 ============
    
    def find_by_id(self, id_value: Any) -> Optional[Dict[str, Any]]:
        """根据 ID 查询单条记录"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {self.PRIMARY_KEY} = %s LIMIT 1"
        return self.db.get_one(sql, [id_value])
    
    def find_by_fid(self, fid: str) -> Optional[Dict[str, Any]]:
        """根据 FID 查询单条记录 (V47.0)"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE fid = %s LIMIT 1"
        return self.db.get_one(sql, [fid])
    
    def find_all(self, 
                 limit: int = 100, 
                 offset: int = 0,
                 order_by: str = None) -> List[Dict[str, Any]]:
        """查询所有记录"""
        order = order_by or self.DEFAULT_ORDER
        sql = f"SELECT * FROM {self.TABLE_NAME} ORDER BY {order} LIMIT %s OFFSET %s"
        return self.db.get_all(sql, [limit, offset]) or []
    
    def find_by_field(self, 
                      field: str, 
                      value: Any,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """根据字段查询"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {field} = %s ORDER BY {self.DEFAULT_ORDER} LIMIT %s"
        return self.db.get_all(sql, [value, limit]) or []
    
    def find_one_by_field(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        """根据字段查询单条"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {field} = %s ORDER BY {self.DEFAULT_ORDER} LIMIT 1"
        return self.db.get_one(sql, [value])
    
    def find_by_fields(self, 
                       filters: Dict[str, Any],
                       limit: int = 100,
                       offset: int = 0) -> List[Dict[str, Any]]:
        """根据多个字段查询"""
        if not filters:
            return self.find_all(limit, offset)
        
        conditions = []
        values = []
        for field, value in filters.items():
            conditions.append(f"{field} = %s")
            values.append(value)
        
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where_clause} ORDER BY {self.DEFAULT_ORDER} LIMIT %s OFFSET %s"
        return self.db.get_all(sql, values + [limit, offset]) or []
    
    # ============ 分页查询 ============
    
    def find_page(self,
                  page: int = 1,
                  page_size: int = 20,
                  filters: Dict[str, Any] = None,
                  order_by: str = None) -> Dict[str, Any]:
        """分页查询"""
        offset = (page - 1) * page_size
        order = order_by or self.DEFAULT_ORDER
        
        # 构建 WHERE 条件
        where_clause = ""
        values = []
        if filters:
            conditions = []
            for field, value in filters.items():
                conditions.append(f"{field} = %s")
                values.append(value)
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} {where_clause}"
        count_result = self.db.get_one(count_sql, values.copy())
        total = count_result.get('cnt', 0) if count_result else 0
        
        # 查询数据
        data_sql = f"SELECT * FROM {self.TABLE_NAME} {where_clause} ORDER BY {order} LIMIT %s OFFSET %s"
        items = self.db.get_all(data_sql, values + [page_size, offset]) or []
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }
    
    # ============ 插入 ============
    
    def insert(self, data: Dict[str, Any]) -> int:
        """插入数据，返回自增 ID"""
        if not data:
            return 0
        
        # 自动添加时间戳
        if 'created_at' not in data:
            data['created_at'] = datetime.now()
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now()
        
        fields = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {self.TABLE_NAME} ({fields}) VALUES ({placeholders})"
        
        self.db.execute(sql, list(data.values()))
        
        # 获取最后插入的 ID
        result = self.db.get_one("SELECT LAST_INSERT_ID() as id")
        return result.get('id', 0) if result else 0
    
    def insert_many(self, data_list: List[Dict[str, Any]]) -> int:
        """批量插入，返回插入数量"""
        if not data_list:
            return 0
        
        affected = 0
        for data in data_list:
            if self.insert(data):
                affected += 1
        return affected
    
    # ============ 更新 ============
    
    def update(self, id_value: Any, data: Dict[str, Any]) -> int:
        """根据 ID 更新数据，返回影响行数"""
        if not data:
            return 0
        
        # 自动更新时间戳
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now()
        
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE {self.PRIMARY_KEY} = %s"
        
        values = list(data.values()) + [id_value]
        return self.db.execute(sql, values)
    
    def update_by_fid(self, fid: str, data: Dict[str, Any]) -> int:
        """根据 FID 更新数据 (V47.0)"""
        if not data:
            return 0
        
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now()
        
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE fid = %s"
        
        values = list(data.values()) + [fid]
        return self.db.execute(sql, values)
    
    def update_by_field(self, 
                        where_field: str, 
                        where_value: Any,
                        data: Dict[str, Any]) -> int:
        """根据字段条件更新"""
        if not data:
            return 0
        
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now()
        
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE {where_field} = %s"
        
        values = list(data.values()) + [where_value]
        return self.db.execute(sql, values)
    
    # ============ 删除 ============
    
    def delete(self, id_value: Any) -> int:
        """硬删除，返回影响行数"""
        sql = f"DELETE FROM {self.TABLE_NAME} WHERE {self.PRIMARY_KEY} = %s"
        return self.db.execute(sql, [id_value])
    
    def soft_delete(self, id_value: Any) -> int:
        """软删除，将 deleted 设为 1"""
        sql = f"UPDATE {self.TABLE_NAME} SET deleted = 1, updated_at = NOW() WHERE {self.PRIMARY_KEY} = %s"
        return self.db.execute(sql, [id_value])
    
    def soft_delete_by_fid(self, fid: str) -> int:
        """根据 FID 软删除 (V47.0)"""
        sql = f"UPDATE {self.TABLE_NAME} SET deleted = 1, updated_at = NOW() WHERE fid = %s"
        return self.db.execute(sql, [fid])
    
    # ============ 统计 ============
    
    def count(self, filters: Dict[str, Any] = None) -> int:
        """统计数量"""
        if filters:
            conditions = []
            values = []
            for field, value in filters.items():
                conditions.append(f"{field} = %s")
                values.append(value)
            where_clause = "WHERE " + " AND ".join(conditions)
            sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} {where_clause}"
            result = self.db.get_one(sql, values)
        else:
            sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME}"
            result = self.db.get_one(sql)
        
        return result.get('cnt', 0) if result else 0
    
    def exists(self, id_value: Any) -> bool:
        """判断记录是否存在"""
        sql = f"SELECT 1 FROM {self.TABLE_NAME} WHERE {self.PRIMARY_KEY} = %s LIMIT 1"
        result = self.db.get_one(sql, [id_value])
        return result is not None
