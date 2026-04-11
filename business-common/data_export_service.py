"""
数据导出服务 V44.0

功能:
1. 订单数据导出 (Excel/CSV)
2. 会员数据导出
3. 积分记录导出
4. 财务对账单导出
5. 导出任务异步处理（大数据量）
6. 导出记录管理
"""

import logging
import json
import io
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from . import db
from .cache_service import cache_get, cache_set

logger = logging.getLogger(__name__)


class ExportFormat:
    CSV = 'csv'
    EXCEL = 'excel'


class ExportType:
    ORDERS = 'orders'
    MEMBERS = 'members'
    POINTS = 'points'
    FINANCE = 'finance'
    REVIEWS = 'reviews'
    BOOKINGS = 'bookings'


class DataExportService:
    """数据导出服务"""

    # 单次最大导出条数（防止超大数据集导出崩溃）
    MAX_EXPORT_ROWS = 50000

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """确保导出记录表存在"""
        try:
            exists = db.get_one("SHOW TABLES LIKE 'business_export_logs'")
            if not exists:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_export_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        export_type VARCHAR(30) NOT NULL COMMENT '导出类型',
                        export_format VARCHAR(10) DEFAULT 'csv' COMMENT '格式:csv/excel',
                        filters TEXT COMMENT '筛选条件JSON',
                        row_count INT DEFAULT 0 COMMENT '导出行数',
                        file_name VARCHAR(200) COMMENT '文件名',
                        status VARCHAR(20) DEFAULT 'pending' COMMENT '状态:pending/done/failed',
                        error_msg TEXT COMMENT '错误信息',
                        operator_id INT COMMENT '操作人ID',
                        operator_name VARCHAR(50) COMMENT '操作人姓名',
                        ec_id INT DEFAULT 1,
                        project_id INT DEFAULT 1,
                        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        finished_at DATETIME COMMENT '完成时间',
                        INDEX idx_operator (operator_id),
                        INDEX idx_scope (ec_id, project_id),
                        INDEX idx_time (started_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据导出记录表'
                """)
                logger.info("business_export_logs 表已创建")
        except Exception as e:
            logger.warning(f"初始化导出记录表失败: {e}")

    def _log_export(
        self, export_type: str, filters: Dict, row_count: int,
        file_name: str, operator_id: int, operator_name: str,
        ec_id: int, project_id: int, status: str = 'done', error_msg: str = None
    ):
        """记录导出日志"""
        try:
            db.execute("""
                INSERT INTO business_export_logs
                (export_type, filters, row_count, file_name, status, error_msg,
                 operator_id, operator_name, ec_id, project_id, finished_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, [
                export_type,
                json.dumps(filters, ensure_ascii=False, default=str),
                row_count,
                file_name,
                status,
                error_msg,
                operator_id,
                operator_name,
                ec_id,
                project_id,
            ])
        except Exception as e:
            logger.warning(f"记录导出日志失败: {e}")

    # ============ 订单导出 ============

    def export_orders(
        self,
        ec_id: int, project_id: int,
        filters: Dict = None,
        operator_id: int = 0, operator_name: str = '',
    ) -> Dict:
        """
        导出订单数据为CSV字符串

        filters支持:
            - start_date: 开始日期 (YYYY-MM-DD)
            - end_date: 结束日期 (YYYY-MM-DD)
            - order_status: 订单状态
            - pay_status: 支付状态
        """
        filters = filters or {}
        where = "o.ec_id=%s AND o.project_id=%s AND o.deleted=0"
        params = [ec_id, project_id]

        if filters.get('start_date'):
            where += " AND DATE(o.created_at) >= %s"
            params.append(filters['start_date'])
        if filters.get('end_date'):
            where += " AND DATE(o.created_at) <= %s"
            params.append(filters['end_date'])
        if filters.get('order_status'):
            where += " AND o.order_status=%s"
            params.append(filters['order_status'])
        if filters.get('pay_status'):
            where += " AND o.pay_status=%s"
            params.append(filters['pay_status'])

        # 限制行数
        params.append(self.MAX_EXPORT_ROWS)

        try:
            rows = db.get_all(f"""
                SELECT
                    o.order_no          AS '订单号',
                    o.created_at        AS '下单时间',
                    m.user_name         AS '买家姓名',
                    m.phone             AS '买家手机',
                    o.total_amount      AS '订单金额',
                    o.discount_amount   AS '优惠金额',
                    o.actual_amount     AS '实付金额',
                    CASE o.order_status
                        WHEN 'pending' THEN '待支付'
                        WHEN 'paid' THEN '已支付'
                        WHEN 'shipped' THEN '已发货'
                        WHEN 'completed' THEN '已完成'
                        WHEN 'cancelled' THEN '已取消'
                        ELSE o.order_status
                    END AS '订单状态',
                    CASE o.pay_status
                        WHEN 'paid' THEN '已支付'
                        WHEN 'unpaid' THEN '未支付'
                        WHEN 'refunding' THEN '退款中'
                        WHEN 'refunded' THEN '已退款'
                        ELSE o.pay_status
                    END AS '支付状态',
                    o.tracking_no       AS '快递单号',
                    o.address_snapshot  AS '收货地址',
                    o.remark            AS '买家备注',
                    o.points_used       AS '使用积分',
                    o.coupon_discount    AS '优惠券减免'
                FROM business_orders o
                LEFT JOIN business_members m ON o.user_id = m.user_id
                WHERE {where}
                ORDER BY o.created_at DESC
                LIMIT %s
            """, params) or []

            csv_content = self._to_csv(rows)
            file_name = f"订单导出_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
            self._log_export(
                ExportType.ORDERS, filters, len(rows), file_name,
                operator_id, operator_name, ec_id, project_id
            )
            return {
                'success': True,
                'data': csv_content,
                'file_name': file_name,
                'row_count': len(rows),
                'content_type': 'text/csv; charset=utf-8-sig',
            }
        except Exception as e:
            logger.error(f"导出订单失败: {e}")
            self._log_export(
                ExportType.ORDERS, filters, 0, '', operator_id, operator_name,
                ec_id, project_id, status='failed', error_msg=str(e)
            )
            return {'success': False, 'msg': f'导出失败: {e}'}

    # ============ 会员导出 ============

    def export_members(
        self,
        ec_id: int, project_id: int,
        filters: Dict = None,
        operator_id: int = 0, operator_name: str = '',
    ) -> Dict:
        """导出会员数据"""
        filters = filters or {}
        where = "m.ec_id=%s AND m.project_id=%s AND m.deleted=0"
        params = [ec_id, project_id]

        if filters.get('member_level'):
            where += " AND m.member_level=%s"
            params.append(filters['member_level'])
        if filters.get('start_date'):
            where += " AND DATE(m.created_at) >= %s"
            params.append(filters['start_date'])
        if filters.get('end_date'):
            where += " AND DATE(m.created_at) <= %s"
            params.append(filters['end_date'])

        params.append(self.MAX_EXPORT_ROWS)

        try:
            rows = db.get_all(f"""
                SELECT
                    m.user_name         AS '会员姓名',
                    m.phone             AS '手机号',
                    CASE m.member_level
                        WHEN 'L1' THEN '普通会员'
                        WHEN 'L2' THEN '白银会员'
                        WHEN 'L3' THEN '黄金会员'
                        WHEN 'L4' THEN '铂金会员'
                        WHEN 'L5' THEN '钻石会员'
                        ELSE m.member_level
                    END AS '会员等级',
                    m.points            AS '当前积分',
                    m.balance           AS '账户余额',
                    m.total_consume     AS '累计消费',
                    m.growth_value      AS '成长值',
                    (SELECT COUNT(*) FROM business_orders o
                     WHERE o.user_id=m.user_id AND o.pay_status='paid') AS '订单数',
                    m.created_at        AS '注册时间',
                    (SELECT MAX(created_at) FROM business_orders
                     WHERE user_id=m.user_id AND pay_status='paid') AS '最后消费时间'
                FROM business_members m
                WHERE {where}
                ORDER BY m.total_consume DESC
                LIMIT %s
            """, params) or []

            csv_content = self._to_csv(rows)
            file_name = f"会员导出_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
            self._log_export(
                ExportType.MEMBERS, filters, len(rows), file_name,
                operator_id, operator_name, ec_id, project_id
            )
            return {
                'success': True,
                'data': csv_content,
                'file_name': file_name,
                'row_count': len(rows),
                'content_type': 'text/csv; charset=utf-8-sig',
            }
        except Exception as e:
            logger.error(f"导出会员失败: {e}")
            return {'success': False, 'msg': f'导出失败: {e}'}

    # ============ 财务对账单导出 ============

    def export_finance_statement(
        self,
        ec_id: int, project_id: int,
        start_date: str, end_date: str,
        operator_id: int = 0, operator_name: str = '',
    ) -> Dict:
        """导出财务对账单（按日汇总）"""
        filters = {'start_date': start_date, 'end_date': end_date}
        try:
            rows = db.get_all("""
                SELECT
                    DATE(created_at)                                                AS '日期',
                    COUNT(*)                                                        AS '订单总数',
                    COUNT(CASE WHEN pay_status='paid' THEN 1 END)                  AS '成功支付订单数',
                    COALESCE(SUM(CASE WHEN pay_status='paid' THEN actual_amount END), 0) AS '实收金额',
                    COALESCE(SUM(CASE WHEN pay_status='paid' THEN discount_amount END), 0) AS '总优惠金额',
                    COALESCE(SUM(CASE WHEN pay_status='paid' THEN coupon_discount END), 0)  AS '优惠券减免',
                    COALESCE(SUM(CASE WHEN pay_status='paid' THEN points_deduction END), 0) AS '积分抵扣',
                    COUNT(CASE WHEN refund_status='refunded' THEN 1 END)           AS '退款单数',
                    COALESCE(SUM(CASE WHEN refund_status='refunded' THEN refund_amount END), 0) AS '退款金额'
                FROM business_orders
                WHERE ec_id=%s AND project_id=%s
                  AND DATE(created_at) BETWEEN %s AND %s
                  AND deleted=0
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at)
            """, [ec_id, project_id, start_date, end_date]) or []

            csv_content = self._to_csv(rows)
            file_name = f"财务对账单_{start_date}至{end_date}.csv"
            self._log_export(
                ExportType.FINANCE, filters, len(rows), file_name,
                operator_id, operator_name, ec_id, project_id
            )
            return {
                'success': True,
                'data': csv_content,
                'file_name': file_name,
                'row_count': len(rows),
                'content_type': 'text/csv; charset=utf-8-sig',
            }
        except Exception as e:
            logger.error(f"导出财务对账单失败: {e}")
            return {'success': False, 'msg': f'导出失败: {e}'}

    # ============ 积分记录导出 ============

    def export_points_log(
        self,
        ec_id: int, project_id: int,
        filters: Dict = None,
        operator_id: int = 0, operator_name: str = '',
    ) -> Dict:
        """导出积分记录"""
        filters = filters or {}
        where = "pl.ec_id=%s AND pl.project_id=%s"
        params = [ec_id, project_id]

        if filters.get('start_date'):
            where += " AND DATE(pl.created_at) >= %s"
            params.append(filters['start_date'])
        if filters.get('end_date'):
            where += " AND DATE(pl.created_at) <= %s"
            params.append(filters['end_date'])
        if filters.get('log_type'):
            where += " AND pl.log_type=%s"
            params.append(filters['log_type'])

        params.append(self.MAX_EXPORT_ROWS)

        try:
            rows = db.get_all(f"""
                SELECT
                    pl.created_at       AS '时间',
                    m.user_name         AS '会员姓名',
                    m.phone             AS '手机号',
                    CASE pl.log_type
                        WHEN 'earn' THEN '获得积分'
                        WHEN 'use' THEN '使用积分'
                        WHEN 'expire' THEN '积分过期'
                        WHEN 'admin' THEN '管理员调整'
                        ELSE pl.log_type
                    END AS '操作类型',
                    pl.points           AS '积分变动',
                    pl.balance          AS '变动后余额',
                    pl.remark           AS '备注'
                FROM business_points_log pl
                LEFT JOIN business_members m ON pl.user_id = m.user_id
                WHERE {where}
                ORDER BY pl.created_at DESC
                LIMIT %s
            """, params) or []

            csv_content = self._to_csv(rows)
            file_name = f"积分记录_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
            self._log_export(
                ExportType.POINTS, filters, len(rows), file_name,
                operator_id, operator_name, ec_id, project_id
            )
            return {
                'success': True,
                'data': csv_content,
                'file_name': file_name,
                'row_count': len(rows),
                'content_type': 'text/csv; charset=utf-8-sig',
            }
        except Exception as e:
            logger.error(f"导出积分记录失败: {e}")
            return {'success': False, 'msg': f'导出失败: {e}'}

    # ============ 导出记录查询 ============

    def get_export_logs(self, ec_id: int, project_id: int, page: int = 1, page_size: int = 20) -> Dict:
        """查询导出历史记录"""
        where = "ec_id=%s AND project_id=%s"
        params = [ec_id, project_id]
        total = db.get_total(f"SELECT COUNT(*) FROM business_export_logs WHERE {where}", params)
        offset = (page - 1) * page_size
        items = db.get_all(f"""
            SELECT id, export_type, export_format, row_count, file_name, status,
                   operator_name, started_at, finished_at
            FROM business_export_logs
            WHERE {where}
            ORDER BY started_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset]) or []
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0,
        }

    # ============ 工具函数 ============

    def _to_csv(self, rows: List[Dict]) -> str:
        """将数据行转换为UTF-8 with BOM的CSV字符串（Excel兼容）"""
        if not rows:
            return '\ufeff'  # BOM only

        output = io.StringIO()
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            # 处理datetime格式
            clean_row = {}
            for k, v in row.items():
                if hasattr(v, 'strftime'):
                    clean_row[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                elif v is None:
                    clean_row[k] = ''
                else:
                    clean_row[k] = v
            writer.writerow(clean_row)

        csv_str = '\ufeff' + output.getvalue()  # 添加BOM使Excel正确识别UTF-8
        output.close()
        return csv_str


# 全局单例
data_export = DataExportService()
