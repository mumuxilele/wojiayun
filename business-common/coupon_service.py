"""
Coupon Service - 优惠券业务逻辑层
V48.0: MVC架构批量改造
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class CouponService:
    """优惠券服务类"""
    
    def __init__(self):
        from business_common import db
        self.db = db
    
    def get_user_coupons(self, user_id: str, status: str = None,
                         page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取用户优惠券列表"""
        offset = (page - 1) * page_size
        
        conditions = ["uc.user_id=%s"]
        params = [user_id]
        
        if status == 'unused':
            conditions.append("uc.status='unused'")
            conditions.append("(c.valid_until IS NULL OR c.valid_until >= CURDATE())")
        elif status == 'used':
            conditions.append("uc.status='used'")
        elif status == 'expired':
            conditions.append("uc.status='unused'")
            conditions.append("c.valid_until < CURDATE()")
        
        where_clause = " AND ".join(conditions)
        
        # 总数
        total = self.db.get_total(
            f"""SELECT COUNT(*) FROM business_user_coupons uc
                LEFT JOIN business_coupons c ON uc.coupon_id=c.id
                WHERE {where_clause}""",
            params
        )
        
        # 列表
        items = self.db.get_all(f"""
            SELECT uc.*, c.coupon_name, c.coupon_type, c.discount_value,
                   c.min_amount, c.max_discount, c.valid_until, c.description
            FROM business_user_coupons uc
            LEFT JOIN business_coupons c ON uc.coupon_id=c.id
            WHERE {where_clause}
            ORDER BY uc.status ASC, uc.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset]) or []
        
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}
    
    def validate_coupon(self, user_id: str, coupon_code: str, order_amount: float = 0) -> Dict[str, Any]:
        """验证优惠券"""
        try:
            coupon = self.db.get_one("""
                SELECT uc.id, uc.user_id, uc.status, uc.coupon_code,
                       c.coupon_name, c.coupon_type, c.discount_value,
                       c.min_amount, c.max_discount, c.valid_until, c.description
                FROM business_user_coupons uc
                LEFT JOIN business_coupons c ON uc.coupon_id=c.id
                WHERE uc.user_id=%s AND uc.coupon_code=%s AND uc.status='unused'
            """, [user_id, coupon_code])
            
            if not coupon:
                return {'success': False, 'msg': '优惠券不存在或已使用'}
            
            if coupon.get('valid_until'):
                from datetime import datetime
                if datetime.strptime(str(coupon['valid_until']), '%Y-%m-%d').date() < datetime.now().date():
                    return {'success': False, 'msg': '优惠券已过期'}
            
            min_amount = float(coupon.get('min_amount') or 0)
            if order_amount < min_amount:
                return {'success': False, 'msg': f'订单金额需满{min_amount}元才能使用'}
            
            discount_value = float(coupon.get('discount_value') or 0)
            coupon_type = coupon.get('coupon_type')
            
            if coupon_type == 'cash':
                discount = discount_value
            elif coupon_type == 'discount':
                discount = order_amount * (1 - discount_value)
                max_d = float(coupon.get('max_discount') or 0)
                if max_d > 0:
                    discount = min(discount, max_d)
            else:
                discount = 0
            
            return {
                'success': True,
                'data': {
                    'coupon_id': coupon.get('id'),
                    'coupon_name': coupon.get('coupon_name'),
                    'coupon_type': coupon_type,
                    'discount_value': discount_value,
                    'discount': round(discount, 2),
                    'description': coupon.get('description', '')
                }
            }
        except Exception as e:
            logger.error(f"验证优惠券失败: {e}")
            return {'success': False, 'msg': '验证失败'}
    
    def exchange_coupon(self, user_id: str, coupon_code: str, ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """兑换优惠券"""
        try:
            # 查询优惠券模板
            template = self.db.get_one(
                "SELECT * FROM business_coupons WHERE coupon_code=%s AND status='active' AND deleted=0",
                [coupon_code]
            )
            
            if not template:
                return {'success': False, 'msg': '兑换码无效'}
            
            # 检查是否已兑换
            existing = self.db.get_one(
                "SELECT id FROM business_user_coupons WHERE user_id=%s AND coupon_id=%s",
                [user_id, template['id']]
            )
            
            if existing:
                return {'success': False, 'msg': '您已兑换过此优惠券'}
            
            # 执行兑换
            self.db.execute("""
                INSERT INTO business_user_coupons 
                (user_id, coupon_id, coupon_code, status, ec_id, project_id, created_at)
                VALUES (%s, %s, %s, 'unused', %s, %s, NOW())
            """, [user_id, template['id'], coupon_code, ec_id, project_id])
            
            return {'success': True, 'msg': '兑换成功'}
        except Exception as e:
            logger.error(f"兑换优惠券失败: {e}")
            return {'success': False, 'msg': '兑换失败'}


_coupon_service = None

def get_coupon_service() -> CouponService:
    global _coupon_service
    if _coupon_service is None:
        _coupon_service = CouponService()
    return _coupon_service