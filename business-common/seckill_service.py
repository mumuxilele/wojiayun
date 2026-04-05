#!/usr/bin/env python3
"""
秒杀服务 V21.0
提供秒杀下单、库存管理、防超卖机制
"""
import json
import logging
from datetime import datetime
from . import db

logger = logging.getLogger(__name__)


class SeckillService:
    """
    秒杀服务 - 保证高并发下的库存准确性
    
    核心特性:
    - 库存预扣减 + 行锁防超卖
    - 每人限买数量控制
    - 活动状态自动校验
    """
    
    @staticmethod
    def get_seckill_activity(activity_id=None, promo_type='seckill', ec_id=None, project_id=None):
        """
        获取秒杀活动详情
        
        Args:
            activity_id: 活动ID（优先）
            promo_type: 活动类型，默认秒杀
            ec_id: 企业ID
            project_id: 项目ID
        
        Returns:
            活动详情或None
        """
        now = datetime.now()
        
        if activity_id:
            return db.get_one("""
                SELECT * FROM business_promotions 
                WHERE id=%s AND promo_type='seckill' AND status='active'
                AND start_time <= %s AND end_time >= %s
            """, [activity_id, now, now])
        
        # 按优先级获取当前有效的秒杀活动
        where = "promo_type='seckill' AND status='active' AND start_time <= %s AND end_time >= %s"
        params = [now, now]
        
        if ec_id:
            where += " AND (ec_id=%s OR ec_id IS NULL)"
            params.append(ec_id)
        if project_id:
            where += " AND (project_id=%s OR project_id IS NULL)"
            params.append(project_id)
        
        return db.get_one(f"""
            SELECT * FROM business_promotions 
            WHERE {where}
            ORDER BY priority DESC, start_time ASC
            LIMIT 1
        """, params)
    
    @staticmethod
    def verify_seckill_stock(activity_id, product_id=None, quantity=1):
        """
        验证秒杀库存
        
        Args:
            activity_id: 活动ID
            product_id: 商品ID（秒杀商品）
            quantity: 购买数量
        
        Returns:
            (是否成功, 剩余库存, 错误信息)
        """
        # 获取活动信息
        activity = db.get_one(
            "SELECT * FROM business_promotions WHERE id=%s AND promo_type='seckill'",
            [activity_id]
        )
        
        if not activity:
            return False, 0, "活动不存在"
        
        # 检查活动时间
        now = datetime.now()
        if now < activity['start_time']:
            return False, 0, "活动尚未开始"
        if now > activity['end_time']:
            return False, 0, "活动已结束"
        
        # 检查活动状态
        if activity.get('status') != 'active':
            return False, 0, "活动已下架"
        
        # 检查库存
        total_stock = activity.get('total_stock', 0)
        if total_stock > 0:
            # 有库存限制，查询当前已售
            sold = db.get_total("""
                SELECT COALESCE(SUM(quantity), 0) FROM business_seckill_orders
                WHERE activity_id=%s AND status != 'cancelled'
            """, [activity_id])
            
            remaining = total_stock - sold
            if remaining < quantity:
                return False, remaining, f"库存不足，仅剩 {remaining} 件"
        
        return True, total_stock, "库存充足"
    
    @staticmethod
    def check_user_limit(activity_id, user_id, per_limit):
        """
        检查用户购买限制
        
        Args:
            activity_id: 活动ID
            user_id: 用户ID
            per_limit: 每人限制数量
        
        Returns:
            (是否可购买, 已购数量, 剩余可购)
        """
        if per_limit == 0:
            return True, 0, 999  # 0表示不限
        
        purchased = db.get_total("""
            SELECT COALESCE(SUM(quantity), 0) FROM business_seckill_orders
            WHERE activity_id=%s AND user_id=%s AND status != 'cancelled'
        """, [activity_id, user_id])
        
        remaining = per_limit - purchased
        return remaining >= 1, purchased, max(0, remaining)
    
    @staticmethod
    def create_seckill_order(activity_id, user_id, user_name, user_phone, 
                            quantity=1, address_id=None, ec_id=None, project_id=None):
        """
        创建秒杀订单（高并发安全）
        
        使用数据库事务锁保证：
        1. 库存原子扣减（防止超卖）
        2. 用户购买限制校验
        3. 订单原子创建
        
        Args:
            activity_id: 活动ID
            user_id: 用户ID
            user_name: 用户名
            user_phone: 手机号
            quantity: 购买数量
            address_id: 收货地址ID
            ec_id: 企业ID
            project_id: 项目ID
        
        Returns:
            {'success': bool, 'order_no': str, 'msg': str}
        """
        from . import utils
        
        # 获取活动信息
        activity = SeckillService.get_seckill_activity(activity_id, ec_id=ec_id, project_id=project_id)
        if not activity:
            return {'success': False, 'msg': '秒杀活动不存在或已结束'}
        
        # 验证库存
        can_buy, remaining, msg = SeckillService.verify_seckill_stock(
            activity_id, quantity=quantity
        )
        if not can_buy:
            return {'success': False, 'msg': msg}
        
        # 验证用户限制
        per_limit = activity.get('per_limit', 1)
        can_buy, purchased, remaining = SeckillService.check_user_limit(
            activity_id, user_id, per_limit
        )
        if not can_buy:
            return {'success': False, 'msg': f'您已购买 {purchased} 件，本活动限购买 {per_limit} 件'}
        
        # 扣减用户剩余可购数量
        if remaining < quantity:
            return {'success': False, 'msg': f'您还可购买 {remaining} 件'}
        
        # 获取秒杀价格
        seckill_price = float(activity.get('seckill_price', 0))
        original_price = float(activity.get('original_price', seckill_price))
        
        # 计算订单金额
        total_amount = seckill_price * quantity
        discount_amount = (original_price - seckill_price) * quantity
        
        # 获取商品信息（从活动关联的商品）
        apply_ids = json.loads(activity.get('apply_ids', '[]'))
        product_id = apply_ids[0] if apply_ids else None
        
        product_name = "秒杀商品"
        if product_id:
            product = db.get_one("SELECT product_name FROM business_products WHERE id=%s", [product_id])
            if product:
                product_name = product['product_name']
        
        # 收货地址快照
        address_snapshot = ""
        if address_id:
            addr = db.get_one(
                "SELECT * FROM business_user_addresses WHERE id=%s AND user_id=%s",
                [address_id, user_id]
            )
            if addr:
                address_snapshot = f"{addr.get('contact_name', '')} {addr.get('contact_phone', '')} {addr.get('province', '')}{addr.get('city', '')}{addr.get('district', '')}{addr.get('address', '')}"
        
        # 生成订单号
        order_no = utils.generate_no('SKO')  # SKO = Seckill Order
        
        conn = db.get_db()
        try:
            cursor = conn.cursor()
            conn.begin()
            
            # 锁定并扣减库存（防止超卖）
            if activity.get('total_stock', 0) > 0:
                # 使用 FOR UPDATE 锁定活动记录
                cursor.execute("""
                    SELECT id, total_stock FROM business_promotions 
                    WHERE id=%s FOR UPDATE
                """, [activity_id])
                
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return {'success': False, 'msg': '活动不存在'}
                
                # 查询已售数量
                cursor.execute("""
                    SELECT COALESCE(SUM(quantity), 0) as sold FROM business_seckill_orders
                    WHERE activity_id=%s AND status != 'cancelled'
                """, [activity_id])
                sold = cursor.fetchone()['sold']
                
                remaining_stock = row['total_stock'] - sold
                if remaining_stock < quantity:
                    conn.rollback()
                    return {'success': False, 'msg': f'库存不足，仅剩 {remaining_stock} 件'}
                
                # 扣减库存（更新活动表）
                # 注意：实际库存由 business_seckill_orders 记录，这里只更新活动表的统计
                cursor.execute("""
                    UPDATE business_promotions 
                    SET total_stock = total_stock - %s
                    WHERE id=%s AND total_stock >= %s
                """, [quantity, activity_id, quantity])
                
                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'success': False, 'msg': '库存扣减失败，请重试'}
            
            # 创建秒杀订单
            cursor.execute("""
                INSERT INTO business_seckill_orders
                (order_no, activity_id, user_id, user_name, user_phone, 
                 product_id, product_name, quantity, 
                 original_price, seckill_price, total_amount, discount_amount,
                 address_snapshot, status, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)
            """, [
                order_no, activity_id, user_id, user_name, user_phone,
                product_id, product_name, quantity,
                original_price, seckill_price, total_amount, discount_amount,
                address_snapshot, ec_id, project_id
            ])
            
            conn.commit()
            
            logger.info(f"秒杀订单创建成功: {order_no}, activity={activity_id}, user={user_id}, qty={quantity}")
            
            return {
                'success': True,
                'order_no': order_no,
                'order_id': cursor.lastrowid if hasattr(cursor, 'lastrowid') else 0,
                'total_amount': total_amount,
                'discount_amount': discount_amount,
                'msg': '秒杀订单创建成功'
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"秒杀订单创建失败: {e}")
            return {'success': False, 'msg': f'下单失败: {str(e)}'}
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass
    
    @staticmethod
    def get_user_seckill_orders(user_id, page=1, page_size=20):
        """
        获取用户的秒杀订单列表
        
        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
        
        Returns:
            订单列表和分页信息
        """
        offset = (page - 1) * page_size
        
        total = db.get_total(
            "SELECT COUNT(*) FROM business_seckill_orders WHERE user_id=%s",
            [user_id]
        )
        
        orders = db.get_all("""
            SELECT s.*, p.promo_name, p.start_time, p.end_time
            FROM business_seckill_orders s
            LEFT JOIN business_promotions p ON s.activity_id = p.id
            WHERE s.user_id=%s
            ORDER BY s.created_at DESC
            LIMIT %s OFFSET %s
        """, [user_id, page_size, offset])
        
        return {
            'items': orders or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }
    
    @staticmethod
    def get_seckill_history(activity_id, page=1, page_size=20):
        """
        获取秒杀活动的订单记录（管理端）
        
        Args:
            activity_id: 活动ID
            page: 页码
            page_size: 每页数量
        
        Returns:
            订单列表
        """
        offset = (page - 1) * page_size
        
        total = db.get_total(
            "SELECT COUNT(*) FROM business_seckill_orders WHERE activity_id=%s",
            [activity_id]
        )
        
        orders = db.get_all("""
            SELECT * FROM business_seckill_orders
            WHERE activity_id=%s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, [activity_id, page_size, offset])
        
        return {
            'items': orders or [],
            'total': total,
            'page': page,
            'page_size': page_size
        }


# 便捷实例
seckill = SeckillService()
