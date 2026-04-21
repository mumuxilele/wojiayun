"""
SearchHistory Service - 搜索历史业务逻辑层
V48.0: MVC架构批量改造
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SearchHistoryService:
    """搜索历史服务类"""
    
    def __init__(self):
        from business_common import db
        self.db = db
    
    def get_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """获取搜索历史"""
        return self.db.get_all("""
            SELECT id, keyword, searched_at
            FROM business_search_history
            WHERE user_id=%s
            ORDER BY searched_at DESC
            LIMIT %s
        """, [user_id, limit]) or []
    
    def add_history(self, user_id: str, keyword: str, ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """添加搜索历史"""
        try:
            # 先删除相同关键词
            self.db.execute(
                "DELETE FROM business_search_history WHERE user_id=%s AND keyword=%s",
                [user_id, keyword]
            )
            # 添加新记录
            self.db.execute("""
                INSERT INTO business_search_history (user_id, keyword, ec_id, project_id, searched_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, [user_id, keyword, ec_id, project_id])
            return {'success': True}
        except Exception as e:
            logger.warning(f"添加搜索历史失败: {e}")
            return {'success': False, 'msg': str(e)}
    
    def clear_history(self, user_id: str) -> Dict[str, Any]:
        """清空搜索历史"""
        try:
            self.db.execute("DELETE FROM business_search_history WHERE user_id=%s", [user_id])
            return {'success': True, 'msg': '已清空搜索历史'}
        except Exception as e:
            logger.warning(f"清空搜索历史失败: {e}")
            return {'success': False, 'msg': '清空失败'}


_search_history_service = None

def get_search_history_service() -> SearchHistoryService:
    global _search_history_service
    if _search_history_service is None:
        _search_history_service = SearchHistoryService()
    return _search_history_service