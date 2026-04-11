"""
发票服务模块 V33.0
功能:
  - 发票抬头管理（企业/个人）
  - 发票申请（电子发票/纸质发票）
  - 发票开具/作废/红冲
  - 发票查询与统计

依赖:
  - storage_service: 文件存储服务
  - notification: 消息通知服务
"""

import logging
import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)


class InvoiceService(BaseService):
    """发票服务"""

    SERVICE_NAME = 'InvoiceService'

    # 发票类型
    INVOICE_TYPES = {
        'electronic': '电子发票',
        'paper': '纸质发票'
    }

    # 发票抬头类型
    TITLE_TYPES = {
        'personal': '个人',
        'enterprise': '企业'
    }

    # 发票状态
    STATUS_PENDING = 'pending'      # 待审核
    STATUS_APPROVED = 'approved'    # 已审核
    STATUS_ISSUED = 'issued'        # 已开具
    STATUS_REJECTED = 'rejected'    # 已驳回
    STATUS_CANCELLED = 'cancelled'  # 已作废

    # 税率配置
    TAX_RATES = {
        'general': 0.06,    # 一般纳税人 6%
        'small': 0.03,     # 小规模纳税人 3%
    }

    # 默认税率
    DEFAULT_TAX_RATE = 0.06

    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            # 检查数据库连接
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_invoices LIMIT 1")
            base['db_status'] = 'connected'
            base['invoice_count'] = result.get('cnt', 0) if result else 0
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base

    # ============ 发票抬头管理 ============

    def get_titles(self, user_id: int, ec_id: int = None, project_id: int = None) -> List[Dict]:
        """
        获取用户的发票抬头列表

        Args:
            user_id: 用户ID
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            List[Dict]: 发票抬头列表
        """
        try:
            sql = """
                SELECT id, user_id, title_type, title_name, tax_no, bank_name, bank_account,
                       address, phone, is_default, created_at, updated_at
                FROM business_invoice_titles
                WHERE user_id=%s AND deleted=0
                ORDER BY is_default DESC, created_at DESC
            """
            params = [user_id]
            
            return db.get_all(sql, params) or []
        except Exception as e:
            logger.error(f"获取发票抬头失败: {e}")
            return []

    def get_title(self, title_id: int, user_id: int = None) -> Optional[Dict]:
        """
        获取发票抬头详情

        Args:
            title_id: 抬头ID
            user_id: 用户ID（可选，用于校验）

        Returns:
            Dict: 发票抬头详情
        """
        try:
            sql = """
                SELECT id, user_id, title_type, title_name, tax_no, bank_name, bank_account,
                       address, phone, is_default, created_at, updated_at
                FROM business_invoice_titles
                WHERE id=%s AND deleted=0
            """
            params = [title_id]
            
            if user_id:
                sql += " AND user_id=%s"
                params.append(user_id)
            
            return db.get_one(sql, params)
        except Exception as e:
            logger.error(f"获取发票抬头详情失败: {e}")
            return None

    def create_title(self, user_id: int, title_type: str, title_name: str,
                    ec_id: int = None, project_id: int = None,
                    tax_no: str = None, bank_name: str = None,
                    bank_account: str = None, address: str = None,
                    phone: str = None, is_default: bool = False) -> Dict[str, Any]:
        """
        创建发票抬头

        Args:
            user_id: 用户ID
            title_type: 抬头类型 (personal/enterprise)
            title_name: 发票抬头名称
            ec_id: 企业ID
            project_id: 项目ID
            tax_no: 税号
            bank_name: 开户银行
            bank_account: 银行账号
            address: 注册地址
            phone: 联系电话
            is_default: 是否默认

        Returns:
            Dict: 创建结果
        """
        try:
            # 企业抬头必须提供税号
            if title_type == 'enterprise' and not tax_no:
                return {'success': False, 'msg': '企业抬头条提供税号'}

            # 如果设置为默认，先取消其他默认
            if is_default:
                db.execute(
                    "UPDATE business_invoice_titles SET is_default=0 WHERE user_id=%s AND deleted=0",
                    [user_id]
                )

            sql = """
                INSERT INTO business_invoice_titles
                (user_id, title_type, title_name, tax_no, bank_name, bank_account,
                 address, phone, is_default, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            title_id = db.execute(sql, (
                user_id, title_type, title_name, tax_no, bank_name, bank_account,
                address, phone, 1 if is_default else 0, ec_id, project_id
            ))

            logger.info(f"创建发票抬头成功: title_id={title_id}, user_id={user_id}")

            return {
                'success': True,
                'msg': '发票抬头创建成功',
                'title_id': title_id
            }
        except Exception as e:
            logger.error(f"创建发票抬头失败: {e}")
            return {'success': False, 'msg': f'创建失败: {str(e)}'}

    def update_title(self, title_id: int, user_id: int = None, **kwargs) -> Dict[str, Any]:
        """
        更新发票抬头

        Args:
            title_id: 抬头ID
            user_id: 用户ID（可选，用于校验）
            **kwargs: 更新的字段

        Returns:
            Dict: 更新结果
        """
        try:
            # 检查抬头是否存在
            title = self.get_title(title_id, user_id)
            if not title:
                return {'success': False, 'msg': '发票抬头不存在'}

            # 构建更新语句
            update_fields = []
            params = []

            allowed_fields = ['title_type', 'title_name', 'tax_no', 'bank_name',
                            'bank_account', 'address', 'phone', 'is_default']

            for field in allowed_fields:
                if field in kwargs:
                    value = kwargs[field]
                    if field == 'is_default' and value:
                        # 如果设置为默认，先取消其他默认
                        db.execute(
                            "UPDATE business_invoice_titles SET is_default=0 WHERE user_id=%s AND deleted=0",
                            [title['user_id']]
                        )
                    update_fields.append(f"{field}=%s")
                    params.append(value)

            if not update_fields:
                return {'success': False, 'msg': '没有需要更新的字段'}

            params.append(title_id)

            sql = f"""
                UPDATE business_invoice_titles
                SET {', '.join(update_fields)}, updated_at=NOW()
                WHERE id=%s AND deleted=0
            """

            db.execute(sql, params)

            logger.info(f"更新发票抬头成功: title_id={title_id}")

            return {'success': True, 'msg': '发票抬头更新成功'}
        except Exception as e:
            logger.error(f"更新发票抬头失败: {e}")
            return {'success': False, 'msg': f'更新失败: {str(e)}'}

    def delete_title(self, title_id: int, user_id: int = None) -> Dict[str, Any]:
        """
        删除发票抬头

        Args:
            title_id: 抬头ID
            user_id: 用户ID（可选，用于校验）

        Returns:
            Dict: 删除结果
        """
        try:
            title = self.get_title(title_id, user_id)
            if not title:
                return {'success': False, 'msg': '发票抬头不存在'}

            # 软删除
            db.execute(
                "UPDATE business_invoice_titles SET deleted=1 WHERE id=%s",
                [title_id]
            )

            logger.info(f"删除发票抬头成功: title_id={title_id}")

            return {'success': True, 'msg': '发票抬头删除成功'}
        except Exception as e:
            logger.error(f"删除发票抬头失败: {e}")
            return {'success': False, 'msg': f'删除失败: {str(e)}'}

    # ============ 发票申请 ============

    def apply_invoice(self, user_id: int, order_id: int, title_id: int,
                     invoice_type: str = 'electronic',
                     amount: Decimal = None, tax_rate: float = None,
                     content: str = '商品明细', remark: str = None,
                     ec_id: int = None, project_id: int = None) -> Dict[str, Any]:
        """
        申请发票

        Args:
            user_id: 用户ID
            order_id: 订单ID
            title_id: 抬头ID
            invoice_type: 发票类型 (electronic/paper)
            amount: 开票金额（默认使用订单实际支付金额）
            tax_rate: 税率（默认使用6%）
            content: 发票内容
            remark: 备注
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            Dict: 申请结果
        """
        try:
            # 验证订单
            order = db.get_one(
                "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
                [order_id, user_id]
            )
            if not order:
                return {'success': False, 'msg': '订单不存在'}

            # 检查是否已支付
            if order.get('pay_status') != 'paid':
                return {'success': False, 'msg': '仅已支付订单可申请发票'}

            # 检查是否已申请过发票
            existing = db.get_one(
                "SELECT id FROM business_invoices WHERE order_id=%s AND deleted=0 AND invoice_status != 'cancelled'",
                [order_id]
            )
            if existing:
                return {'success': False, 'msg': '该订单已申请过发票'}

            # 验证抬头
            title = self.get_title(title_id, user_id)
            if not title:
                return {'success': False, 'msg': '发票抬头不存在'}

            # 计算开票金额
            if amount is None:
                amount = Decimal(str(order.get('actual_amount', 0)))

            # 计算税额
            if tax_rate is None:
                tax_rate = self.DEFAULT_TAX_RATE
            tax_amount = amount * Decimal(str(tax_rate))

            # 生成发票号
            invoice_no = self._generate_invoice_no()

            # 创建发票记录
            sql = """
                INSERT INTO business_invoices
                (invoice_no, order_id, order_no, user_id, title_id, title_type,
                 title_name, tax_no, invoice_type, invoice_status, amount,
                 tax_amount, tax_rate, content, remark, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            invoice_id = db.execute(sql, (
                invoice_no, order_id, order.get('order_no'), user_id, title_id,
                title['title_type'], title['title_name'], title.get('tax_no'),
                invoice_type, self.STATUS_PENDING, amount, tax_amount, tax_rate,
                content, remark, ec_id, project_id
            ))

            logger.info(f"申请发票成功: invoice_id={invoice_id}, order_id={order_id}")

            return {
                'success': True,
                'msg': '发票申请成功',
                'invoice_id': invoice_id,
                'invoice_no': invoice_no
            }
        except Exception as e:
            logger.error(f"申请发票失败: {e}")
            return {'success': False, 'msg': f'申请失败: {str(e)}'}

    def get_invoices(self, user_id: int = None, ec_id: int = None, project_id: int = None,
                    status: str = None, page: int = 1, page_size: int = 20) -> Dict:
        """
        获取发票列表

        Args:
            user_id: 用户ID（用户端筛选）
            ec_id: 企业ID（管理端筛选）
            project_id: 项目ID（管理端筛选）
            status: 发票状态
            page: 页码
            page_size: 每页数量

        Returns:
            Dict: 分页结果
        """
        try:
            where_clauses = ["deleted=0"]
            params = []

            if user_id:
                where_clauses.append("user_id=%s")
                params.append(user_id)

            if ec_id:
                where_clauses.append("ec_id=%s")
                params.append(ec_id)

            if project_id:
                where_clauses.append("project_id=%s")
                params.append(project_id)

            if status:
                where_clauses.append("invoice_status=%s")
                params.append(status)

            where_sql = " AND ".join(where_clauses)

            # 统计总数
            total = db.get_total(f"SELECT COUNT(*) FROM business_invoices WHERE {where_sql}", params)

            # 分页查询
            offset = (page - 1) * page_size
            sql = f"""
                SELECT i.*, t.title_type, t.title_name, t.tax_no
                FROM business_invoices i
                LEFT JOIN business_invoice_titles t ON i.title_id = t.id
                WHERE {where_sql}
                ORDER BY i.created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])

            items = db.get_all(sql, params) or []

            return {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size if total else 0
            }
        except Exception as e:
            logger.error(f"获取发票列表失败: {e}")
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

    def get_invoice(self, invoice_id: int, user_id: int = None) -> Optional[Dict]:
        """
        获取发票详情

        Args:
            invoice_id: 发票ID
            user_id: 用户ID（可选，用于校验）

        Returns:
            Dict: 发票详情
        """
        try:
            sql = """
                SELECT i.*, t.title_type, t.title_name, t.tax_no,
                       t.bank_name, t.bank_account, t.address, t.phone,
                       o.actual_amount, o.pay_time
                FROM business_invoices i
                LEFT JOIN business_invoice_titles t ON i.title_id = t.id
                LEFT JOIN business_orders o ON i.order_id = o.id
                WHERE i.id=%s AND i.deleted=0
            """
            params = [invoice_id]

            if user_id:
                sql += " AND i.user_id=%s"
                params.append(user_id)

            return db.get_one(sql, params)
        except Exception as e:
            logger.error(f"获取发票详情失败: {e}")
            return None

    # ============ 发票管理（管理端）============

    def approve_invoice(self, invoice_id: int, admin_id: int = None,
                       admin_name: str = None) -> Dict[str, Any]:
        """
        审核发票

        Args:
            invoice_id: 发票ID
            admin_id: 审核人ID
            admin_name: 审核人名称

        Returns:
            Dict: 审核结果
        """
        try:
            invoice = self.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'msg': '发票不存在'}

            if invoice['invoice_status'] != self.STATUS_PENDING:
                return {'success': False, 'msg': '该发票已审核或已作废'}

            sql = """
                UPDATE business_invoices
                SET invoice_status=%s, updated_at=NOW()
                WHERE id=%s
            """
            db.execute(sql, [self.STATUS_APPROVED, invoice_id])

            logger.info(f"审核发票成功: invoice_id={invoice_id}, admin={admin_name}")

            return {'success': True, 'msg': '发票审核通过'}
        except Exception as e:
            logger.error(f"审核发票失败: {e}")
            return {'success': False, 'msg': f'审核失败: {str(e)}'}

    def reject_invoice(self, invoice_id: int, reason: str = None,
                       admin_id: int = None, admin_name: str = None) -> Dict[str, Any]:
        """
        驳回发票申请

        Args:
            invoice_id: 发票ID
            reason: 驳回原因
            admin_id: 审核人ID
            admin_name: 审核人名称

        Returns:
            Dict: 驳回结果
        """
        try:
            invoice = self.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'msg': '发票不存在'}

            if invoice['invoice_status'] != self.STATUS_PENDING:
                return {'success': False, 'msg': '该发票已审核或已作废'}

            sql = """
                UPDATE business_invoices
                SET invoice_status=%s, remark=CONCAT(IFNULL(remark, ''), ' 驳回原因: ', %s), updated_at=NOW()
                WHERE id=%s
            """
            db.execute(sql, [self.STATUS_REJECTED, reason or '未说明', invoice_id])

            logger.info(f"驳回发票申请: invoice_id={invoice_id}, reason={reason}")

            return {'success': True, 'msg': '发票申请已驳回'}
        except Exception as e:
            logger.error(f"驳回发票失败: {e}")
            return {'success': False, 'msg': f'驳回失败: {str(e)}'}

    def issue_invoice(self, invoice_id: int, admin_id: int = None,
                      admin_name: str = None, pdf_url: str = None) -> Dict[str, Any]:
        """
        开具发票

        Args:
            invoice_id: 发票ID
            admin_id: 开票人ID
            admin_name: 开票人名称
            pdf_url: 电子发票PDF地址

        Returns:
            Dict: 开票结果
        """
        try:
            invoice = self.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'msg': '发票不存在'}

            if invoice['invoice_status'] not in [self.STATUS_PENDING, self.STATUS_APPROVED]:
                return {'success': False, 'msg': '该发票状态不允许开具'}

            sql = """
                UPDATE business_invoices
                SET invoice_status=%s, issued_at=NOW(), issued_by=%s, pdf_url=%s, updated_at=NOW()
                WHERE id=%s
            """
            db.execute(sql, [self.STATUS_ISSUED, admin_name, pdf_url, invoice_id])

            # 更新订单发票状态
            db.execute(
                "UPDATE business_orders SET invoice_status='issued' WHERE id=%s",
                [invoice['order_id']]
            )

            logger.info(f"开具发票成功: invoice_id={invoice_id}")

            return {'success': True, 'msg': '发票开具成功', 'pdf_url': pdf_url}
        except Exception as e:
            logger.error(f"开具发票失败: {e}")
            return {'success': False, 'msg': f'开具失败: {str(e)}'}

    def cancel_invoice(self, invoice_id: int, reason: str = None,
                      admin_id: int = None, admin_name: str = None) -> Dict[str, Any]:
        """
        作废发票

        Args:
            invoice_id: 发票ID
            reason: 作废原因
            admin_id: 操作人ID
            admin_name: 操作人名称

        Returns:
            Dict: 作废结果
        """
        try:
            invoice = self.get_invoice(invoice_id)
            if not invoice:
                return {'success': False, 'msg': '发票不存在'}

            if invoice['invoice_status'] == self.STATUS_CANCELLED:
                return {'success': False, 'msg': '该发票已作废'}

            sql = """
                UPDATE business_invoices
                SET invoice_status=%s, remark=CONCAT(IFNULL(remark, ''), ' 作废原因: ', %s), updated_at=NOW()
                WHERE id=%s
            """
            db.execute(sql, [self.STATUS_CANCELLED, reason or '主动作废', invoice_id])

            # 更新订单发票状态
            db.execute(
                "UPDATE business_orders SET invoice_status='cancelled' WHERE id=%s",
                [invoice['order_id']]
            )

            logger.info(f"作废发票成功: invoice_id={invoice_id}, reason={reason}")

            return {'success': True, 'msg': '发票已作废'}
        except Exception as e:
            logger.error(f"作废发票失败: {e}")
            return {'success': False, 'msg': f'作废失败: {str(e)}'}

    # ============ 发票统计 ============

    def get_statistics(self, ec_id: int = None, project_id: int = None,
                       date_from: str = None, date_to: str = None) -> Dict:
        """
        获取发票统计

        Args:
            ec_id: 企业ID
            project_id: 项目ID
            date_from: 开始日期
            date_to: 结束日期

        Returns:
            Dict: 统计数据
        """
        try:
            where_clauses = ["deleted=0"]
            params = []

            if ec_id:
                where_clauses.append("ec_id=%s")
                params.append(ec_id)

            if project_id:
                where_clauses.append("project_id=%s")
                params.append(project_id)

            if date_from:
                where_clauses.append("created_at >= %s")
                params.append(date_from)

            if date_to:
                where_clauses.append("created_at <= %s")
                params.append(date_to + ' 23:59:59')

            where_sql = " AND ".join(where_clauses)

            # 总数统计
            total_stats = db.get_one(f"""
                SELECT 
                    COUNT(*) as total_count,
                    COALESCE(SUM(amount), 0) as total_amount,
                    COALESCE(SUM(tax_amount), 0) as total_tax
                FROM business_invoices
                WHERE {where_sql}
            """, params)

            # 按状态统计
            status_stats = db.get_all(f"""
                SELECT invoice_status,
                       COUNT(*) as count,
                       COALESCE(SUM(amount), 0) as amount
                FROM business_invoices
                WHERE {where_sql}
                GROUP BY invoice_status
            """, params)

            # 按类型统计
            type_stats = db.get_all(f"""
                SELECT invoice_type,
                       COUNT(*) as count,
                       COALESCE(SUM(amount), 0) as amount
                FROM business_invoices
                WHERE {where_sql}
                GROUP BY invoice_type
            """, params)

            # 按抬头类型统计
            title_type_stats = db.get_all(f"""
                SELECT title_type,
                       COUNT(*) as count,
                       COALESCE(SUM(amount), 0) as amount
                FROM business_invoices
                WHERE {where_sql}
                GROUP BY title_type
            """, params)

            return {
                'total_count': int(total_stats.get('total_count', 0) or 0),
                'total_amount': float(total_stats.get('total_amount', 0) or 0),
                'total_tax': float(total_stats.get('total_tax', 0) or 0),
                'by_status': {s['invoice_status']: {'count': s['count'], 'amount': float(s['amount'])}
                              for s in status_stats},
                'by_type': {s['invoice_type']: {'count': s['count'], 'amount': float(s['amount'])}
                           for s in type_stats},
                'by_title_type': {s['title_type']: {'count': s['count'], 'amount': float(s['amount'])}
                                for s in title_type_stats}
            }
        except Exception as e:
            logger.error(f"获取发票统计失败: {e}")
            return {
                'total_count': 0, 'total_amount': 0, 'total_tax': 0,
                'by_status': {}, 'by_type': {}, 'by_title_type': {}
            }

    # ============ 辅助方法 ============

    def _generate_invoice_no(self) -> str:
        """生成发票号"""
        date_str = datetime.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4().hex[:8]).upper()
        return f"INV{date_str}{random_str}"


# 单例实例
invoice_service = InvoiceService()
