"""
Member Repository
会员数据访问层
"""
import logging
from typing import Optional, Dict, Any, List
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MemberRepository(BaseRepository):
    """会员仓储类"""

    TABLE_NAME = 'business_members'
    PRIMARY_KEY = 'id'
    DEFAULT_ORDER = 'created_at DESC'

    def find_members_with_filter(self,
                                  keyword: str = None,
                                  page: int = 1,
                                  page_size: int = 20) -> Dict[str, Any]:
        """查询会员列表（支持关键字搜索）"""
        offset = (page - 1) * page_size

        conditions = ["1=1"]
        params = []
        if keyword:
            conditions.append("(user_name LIKE %s OR phone LIKE %s)")
            params.extend(["%" + keyword + "%", "%" + keyword + "%"])

        where_clause = " AND ".join(conditions)

        # 总数
        count_sql = "SELECT COUNT(*) as cnt FROM business_members WHERE " + where_clause
        count_result = self.db.get_one(count_sql, params.copy())
        total = count_result.get('cnt', 0) if count_result else 0

        # 数据
        data_sql = ("SELECT * FROM business_members WHERE " + where_clause +
                    " ORDER BY created_at DESC LIMIT %s OFFSET %s")
        items = self.db.get_all(data_sql, params + [page_size, offset]) or []

        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }
