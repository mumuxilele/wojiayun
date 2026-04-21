"""
Invoice Service - 发票业务逻辑层
V48.0: MVC架构批量改造
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class InvoiceService:
    """发票服务类"""
    
    def __init__(self):
        from business_common import db
        self.db = db
    
    def get_invoice_titles(self, user_id: str) -> List[Dict]:
        """获取用户的发票抬头列表"""
        return self.db.get_all("""
            SELECT id, title_type, title_name, tax_no, bank_name, bank_account,
                   address, phone, is_default, created_at
            FROM business_invoice_titles
            WHERE user_id=%s AND deleted=0
            ORDER BY is_default DESC, created_at DESC
        """, [user_id]) or []
    
    def create_invoice_title(self, user_id: str, title_type: str, title_name: str,
                            tax_no: str = '', bank_name: str = '', bank_account: str = '',
                            address: str = '', phone: str = '', is_default: bool = False,
                            ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """创建发票抬头"""
        try:
            if is_default:
                self.db.execute(
                    "UPDATE business_invoice_titles SET is_default=0 WHERE user_id=%s AND deleted=0",
                    [user_id]
                )
            
            self.db.execute("""
                INSERT INTO business_invoice_titles 
                (user_id, title_type, title_name, tax_no, bank_name, bank_account, address, phone, is_default, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [user_id, title_type, title_name, tax_no, bank_name, bank_account, address, phone, 1 if is_default else 0, ec_id, project_id])
            
            return {'success': True, 'msg': '发票抬头创建成功'}
        except Exception as e:
            logger.error(f"创建发票抬头失败: {e}")
            return {'success': False, 'msg': '创建失败'}
    
    def update_invoice_title(self, title_id: int, user_id: str,
                             title_name: str = None, tax_no: str = None,
                             bank_name: str = None, bank_account: str = None,
                             address: str = None, phone: str = None,
                             is_default: bool = None) -> Dict[str, Any]:
        """更新发票抬头"""
        try:
            existing = self.db.get_one(
                "SELECT id FROM business_invoice_titles WHERE id=%s AND user_id=%s AND deleted=0",
                [title_id, user_id]
            )
            if not existing:
                return {'success': False, 'msg': '发票抬头不存在'}
            
            updates = []
            values = []
            for field, value in [
                ('title_name', title_name), ('tax_no', tax_no), ('bank_name', bank_name),
                ('bank_account', bank_account), ('address', address), ('phone', phone)
            ]:
                if value is not None:
                    updates.append(f"{field}=%s")
                    values.append(value)
            
            if is_default == 1:
                self.db.execute(
                    "UPDATE business_invoice_titles SET is_default=0 WHERE user_id=%s AND deleted=0",
                    [user_id]
                )
                updates.append("is_default=1")
            elif is_default is not None:
                updates.append("is_default=0")
            
            if not updates:
                return {'success': True, 'msg': '没有更新字段'}
            
            updates.append("updated_at=NOW()")
            values.extend([title_id, user_id])
            
            self.db.execute(
                f"UPDATE business_invoice_titles SET {', '.join(updates)} WHERE id=%s AND user_id=%s",
                values
            )
            return {'success': True, 'msg': '更新成功'}
        except Exception as e:
            logger.error(f"更新发票抬头失败: {e}")
            return {'success': False, 'msg': '更新失败'}
    
    def delete_invoice_title(self, title_id: int, user_id: str) -> Dict[str, Any]:
        """删除发票抬头"""
        try:
            affected = self.db.execute(
                "UPDATE business_invoice_titles SET deleted=1, updated_at=NOW() WHERE id=%s AND user_id=%s",
                [title_id, user_id]
            )
            if affected > 0:
                return {'success': True, 'msg': '已删除'}
            return {'success': False, 'msg': '不存在'}
        except Exception as e:
            logger.error(f"删除发票抬头失败: {e}")
            return {'success': False, 'msg': '删除失败'}
    
    def get_invoices(self, user_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取用户的发票列表"""
        offset = (page - 1) * page_size
        total = self.db.get_total(
            "SELECT COUNT(*) FROM business_invoices WHERE user_id=%s AND deleted=0",
            [user_id]
        )
        items = self.db.get_all("""
            SELECT i.*, o.order_no
            FROM business_invoices i
            LEFT JOIN business_orders o ON i.order_id=o.id
            WHERE i.user_id=%s AND i.deleted=0
            ORDER BY i.created_at DESC
            LIMIT %s OFFSET %s
        """, [user_id, page_size, offset]) or []
        
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}
    
    def apply_invoice_from_order(self, user_id: str, order_id: int, title_id: int = None,
                                 title_type: str = None, title_name: str = None,
                                 tax_no: str = None) -> Dict[str, Any]:
        """申请从订单开发票"""
        try:
            order = self.db.get_one(
                "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
                [order_id, user_id]
            )
            if not order:
                return {'success': False, 'msg': '订单不存在'}
            
            if order.get('invoice_status') == 'applied':
                return {'success': False, 'msg': '已申请过发票'}
            
            invoice_amount = float(order.get('actual_amount', 0))
            invoice_title = ''
            
            if title_id:
                title = self.db.get_one(
                    "SELECT title_name, tax_no FROM business_invoice_titles WHERE id=%s AND user_id=%s",
                    [title_id, user_id]
                )
                if title:
                    invoice_title = f"{title['title_name']}({title['tax_no']})"
            
            self.db.execute("""
                INSERT INTO business_invoices 
                (order_id, user_id, title_type, title_name, tax_no, invoice_amount, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW())
            """, [order_id, user_id, title_type or 'personal', 
                  title_name or invoice_title, tax_no or '', invoice_amount])
            
            self.db.execute(
                "UPDATE business_orders SET invoice_status='applied' WHERE id=%s",
                [order_id]
            )
            
            return {'success': True, 'msg': '发票申请已提交'}
        except Exception as e:
            logger.error(f"申请发票失败: {e}")
            return {'success': False, 'msg': '申请失败'}
    
    def cancel_invoice(self, invoice_id: int, user_id: str) -> Dict[str, Any]:
        """取消发票申请"""
        try:
            invoice = self.db.get_one(
                "SELECT * FROM business_invoices WHERE id=%s AND user_id=%s AND deleted=0",
                [invoice_id, user_id]
            )
            if not invoice:
                return {'success': False, 'msg': '发票不存在'}
            
            if invoice.get('status') != 'pending':
                return {'success': False, 'msg': '只有待处理的发票可以取消'}
            
            self.db.execute(
                "UPDATE business_invoices SET deleted=1, updated_at=NOW() WHERE id=%s",
                [invoice_id]
            )
            
            self.db.execute(
                "UPDATE business_orders SET invoice_status=NULL WHERE id=%s",
                [invoice.get('order_id')]
            )
            
            return {'success': True, 'msg': '已取消发票申请'}
        except Exception as e:
            logger.error(f"取消发票失败: {e}")
            return {'success': False, 'msg': '取消失败'}


_invoice_service = None

def get_invoice_service() -> InvoiceService:
    global _invoice_service
    if _invoice_service is None:
        _invoice_service = InvoiceService()
    return _invoice_service