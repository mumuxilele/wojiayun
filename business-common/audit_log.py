"""
操作审计日志模块
记录关键操作，用于追溯和统计
"""
import json
import logging
from . import db
from flask import request

logger = logging.getLogger(__name__)


def log_action(user_id, user_name, action, details=None, ip=None, ec_id=None, project_id=None):
    """
    记录操作日志
    
    参数:
        user_id: 操作人ID
        user_name: 操作人姓名
        action: 操作类型（如：create_application, update_order, delete_venue等）
        details: 操作详情（dict，会被JSON化）
        ip: 客户端IP
        ec_id: 企业ID
        project_id: 项目ID
    """
    try:
        if ip is None:
            ip = request.remote_addr if request else '127.0.0.1'
        
        details_json = json.dumps(details) if details else None
        
        db.execute(
            """INSERT INTO system_audit_log 
               (user_id, user_name, action, details, ip, ec_id, project_id, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
            [user_id, user_name, action, details_json, ip, ec_id, project_id]
        )
        logger.debug(f"[审计日志] {action} by {user_name}({user_id})")
    except Exception as e:
        # 日志记录失败不影响主流程，只打印日志
        logger.error(f"[审计日志记录失败] {e}")


def get_audit_logs(user_id=None, action=None, date_from=None, date_to=None,
                   ec_id=None, project_id=None, page=1, page_size=50):
    """
    查询审计日志
    
    参数:
        user_id: 按用户ID筛选
        action: 按操作类型筛选
        date_from: 开始日期
        date_to: 结束日期
        ec_id: 企业ID
        project_id: 项目ID
        page: 页码
        page_size: 每页条数
    
    返回:
        {'items': [...], 'total': total, 'page': page, 'page_size': page_size}
    """
    where = "1=1"
    params = []
    
    if user_id:
        where += " AND user_id=%s"
        params.append(user_id)
    if action:
        where += " AND action LIKE %s"
        params.append(f"%{action}%")
    if date_from:
        where += " AND DATE(created_at)>=%s"
        params.append(date_from)
    if date_to:
        where += " AND DATE(created_at)<=%s"
        params.append(date_to)
    if ec_id:
        where += " AND ec_id=%s"
        params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"
        params.append(project_id)
    
    total = db.get_total(f"SELECT COUNT(*) FROM system_audit_log WHERE {where}", params)
    offset = (page - 1) * page_size
    
    items = db.get_all(
        f"""SELECT id, user_id, user_name, action, details, ip, 
                  ec_id, project_id, created_at 
           FROM system_audit_log 
           WHERE {where} 
           ORDER BY created_at DESC 
           LIMIT %s OFFSET %s""",
        params + [page_size, offset]
    )
    
    # 解析details JSON
    for item in items:
        if item.get('details'):
            try:
                item['details'] = json.loads(item['details'])
            except:
                pass
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }


# 创建审计日志表的SQL
CREATE_AUDIT_LOG_SQL = """
CREATE TABLE IF NOT EXISTS system_audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) COMMENT '操作人ID',
    user_name VARCHAR(100) COMMENT '操作人姓名',
    action VARCHAR(100) NOT NULL COMMENT '操作类型',
    details TEXT COMMENT '操作详情JSON',
    ip VARCHAR(50) COMMENT '客户端IP',
    ec_id VARCHAR(64) COMMENT '企业ID',
    project_id VARCHAR(64) COMMENT '项目ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at),
    INDEX idx_ec_project (ec_id, project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统审计日志表';
"""
