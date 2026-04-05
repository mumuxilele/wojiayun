"""
会员等级服务模块 V16.0
功能：
  1. 计算会员等级（基于累计消费）
  2. 获取会员权益（折扣、积分倍率）
  3. 等级升级/降级处理
  4. 权益计算（订单优惠、积分发放）
"""
import json
import logging
from datetime import datetime
from . import db

logger = logging.getLogger(__name__)


class MemberLevelService:
    """会员等级服务"""
    
    # 默认等级配置（如果数据库未配置时使用）
    DEFAULT_LEVELS = {
        'L1': {'name': '普通会员', 'discount': 1.00, 'points_rate': 1.00},
        'L2': {'name': '铜牌会员', 'discount': 0.95, 'points_rate': 1.20},
        'L3': {'name': '银牌会员', 'discount': 0.90, 'points_rate': 1.50},
        'L4': {'name': '金牌会员', 'discount': 0.85, 'points_rate': 2.00},
        'L5': {'name': '钻石会员', 'discount': 0.80, 'points_rate': 3.00},
    }
    
    @staticmethod
    def get_all_levels(ec_id=None, project_id=None):
        """
        获取所有会员等级配置
        
        Args:
            ec_id: 企业ID
            project_id: 项目ID
        
        Returns:
            会员等级列表（按sort_order排序）
        """
        where = "status='active'"
        params = []
        
        if ec_id:
            where += " AND (ec_id=%s OR ec_id IS NULL)"
            params.append(ec_id)
        if project_id:
            where += " AND (project_id=%s OR project_id IS NULL)"
            params.append(project_id)
        
        levels = db.get_all(f"""
            SELECT * FROM business_member_levels 
            WHERE {where} 
            ORDER BY sort_order ASC
        """, params)
        
        # 如果数据库无数据，返回默认配置
        if not levels:
            result = []
            for code, info in MemberLevelService.DEFAULT_LEVELS.items():
                result.append({
                    'level_code': code,
                    'level_name': info['name'],
                    'min_amount': 0,
                    'discount_rate': info['discount'],
                    'points_rate': info['points_rate'],
                    'privileges': json.dumps([info['name']])
                })
            return result
        
        return levels
    
    @staticmethod
    def get_member_level_info(user_id):
        """
        获取会员当前等级信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            会员等级详细信息
        """
        member = db.get_one("""
            SELECT m.*, l.level_name, l.discount_rate, l.points_rate, l.privileges, l.next_level
            FROM business_members m
            LEFT JOIN business_member_levels l ON m.member_level = l.level_code
            WHERE m.user_id = %s
        """, [user_id])
        
        if not member:
            return None
        
        # 如果没有等级信息，使用默认L1
        if not member.get('level_code'):
            member['level_name'] = '普通会员'
            member['discount_rate'] = 1.00
            member['points_rate'] = 1.00
            member['privileges'] = '["基础积分倍率"]'
        
        # 计算升级进度
        member['next_level_info'] = MemberLevelService._get_next_level(member.get('member_level'))
        
        return member
    
    @staticmethod
    def _get_next_level(current_code):
        """获取下一等级信息"""
        levels = MemberLevelService.get_all_levels()
        current_order = 0
        
        for i, level in enumerate(levels):
            if level['level_code'] == current_code:
                current_order = i
                break
        
        if current_order < len(levels) - 1:
            next_level = levels[current_order + 1]
            return {
                'level_code': next_level['level_code'],
                'level_name': next_level['level_name'],
                'min_amount': next_level['min_amount']
            }
        return None
    
    @staticmethod
    def calculate_discount(user_id, original_amount):
        """
        计算会员折扣
        
        Args:
            user_id: 用户ID
            original_amount: 原价
        
        Returns:
            (折扣后金额, 优惠金额, 使用的等级信息)
        """
        member = db.get_one("""
            SELECT m.member_level, l.discount_rate, l.level_name
            FROM business_members m
            LEFT JOIN business_member_levels l ON m.member_level = l.level_code
            WHERE m.user_id = %s
        """, [user_id])
        
        discount_rate = 1.00
        level_name = '普通会员'
        
        if member and member.get('discount_rate'):
            discount_rate = float(member['discount_rate'])
            level_name = member.get('level_name', '普通会员')
        
        final_amount = round(float(original_amount) * discount_rate, 2)
        saved_amount = round(float(original_amount) - final_amount, 2)
        
        return final_amount, saved_amount, {
            'level_code': member.get('member_level', 'L1') if member else 'L1',
            'level_name': level_name,
            'discount_rate': discount_rate
        }
    
    @staticmethod
    def calculate_points(user_id, amount):
        """
        计算订单应得积分
        
        Args:
            user_id: 用户ID
            amount: 消费金额
        
        Returns:
            (积分数量, 积分倍率)
        """
        member = db.get_one("""
            SELECT m.member_level, l.points_rate, l.level_name
            FROM business_members m
            LEFT JOIN business_member_levels l ON m.member_level = l.level_code
            WHERE m.user_id = %s
        """, [user_id])
        
        points_rate = 1.00
        level_name = '普通会员'
        
        if member and member.get('points_rate'):
            points_rate = float(member['points_rate'])
            level_name = member.get('level_name', '普通会员')
        
        # 1元 = 1积分 * 倍率
        points = int(float(amount) * points_rate)
        
        return points, points_rate
    
    @staticmethod
    def update_total_consume(user_id, amount, ec_id=None, project_id=None):
        """
        更新会员累计消费金额，并检查是否需要升级
        
        Args:
            user_id: 用户ID
            amount: 本次消费金额
            ec_id: 企业ID
            project_id: 项目ID
        
        Returns:
            {'upgraded': bool, 'new_level': dict}
        """
        # 查询当前累计消费
        member = db.get_one("""
            SELECT user_id, total_consume, member_level 
            FROM business_members 
            WHERE user_id = %s
        """, [user_id])
        
        if not member:
            logger.warning(f"会员不存在: {user_id}")
            return {'upgraded': False, 'new_level': None}
        
        # 计算新的累计消费
        new_total = float(member.get('total_consume', 0)) + float(amount)
        
        # 获取所有等级配置
        levels = MemberLevelService.get_all_levels(ec_id, project_id)
        
        # 查找应该属于的等级
        new_level_code = 'L1'
        for level in levels:
            if new_total >= float(level['min_amount']):
                new_level_code = level['level_code']
            else:
                break
        
        old_level = member.get('member_level', 'L1')
        
        # 更新累计消费和等级
        db.execute("""
            UPDATE business_members 
            SET total_consume = %s, 
                member_level = %s,
                member_level_updated_at = NOW()
            WHERE user_id = %s
        """, [new_total, new_level_code, user_id])
        
        upgraded = new_level_code != old_level
        
        if upgraded:
            new_level = db.get_one("SELECT * FROM business_member_levels WHERE level_code=%s", [new_level_code])
            logger.info(f"会员升级: user={user_id}, {old_level} -> {new_level_code}, 累计消费={new_total}")
            
            # 可以在这里发送升级通知
            try:
                from .notification import send_notification
                send_notification(
                    user_id=user_id,
                    title='会员等级升级',
                    content=f'恭喜！您的会员等级已升级为{new_level["level_name"]}，享受{new_level["discount_rate"]*10}折优惠！',
                    notify_type='points',
                    ec_id=ec_id,
                    project_id=project_id
                )
            except Exception as e:
                logger.warning(f"升级通知发送失败: {e}")
        
        return {
            'upgraded': upgraded,
            'old_level': old_level,
            'new_level': new_level_code,
            'new_level_name': new_level.get('level_name') if upgraded else None,
            'total_consume': new_total
        }
    
    @staticmethod
    def get_member_statistics(ec_id=None, project_id=None):
        """
        获取会员等级统计
        
        Args:
            ec_id: 企业ID
            project_id: 项目ID
        
        Returns:
            等级分布统计
        """
        where = "deleted=0"
        params = []
        
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        # 按等级统计
        stats = db.get_all(f"""
            SELECT 
                COALESCE(m.member_level, 'L1') as level_code,
                COUNT(*) as count,
                SUM(m.total_consume) as total_amount,
                AVG(m.total_consume) as avg_amount
            FROM business_members m
            WHERE {where}
            GROUP BY m.member_level
            ORDER BY m.member_level
        """, params)
        
        # 获取等级名称
        levels = MemberLevelService.get_all_levels(ec_id, project_id)
        level_names = {l['level_code']: l['level_name'] for l in levels}
        
        for stat in stats:
            stat['level_name'] = level_names.get(stat['level_code'], '普通会员')
        
        return stats


class PromotionService:
    """营销活动服务"""
    
    @staticmethod
    def get_active_promotions(product_id=None, category_id=None, ec_id=None, project_id=None):
        """
        获取当前可用的营销活动
        
        Args:
            product_id: 商品ID（用于商品级活动）
            category_id: 分类ID
            ec_id: 企业ID
            project_id: 项目ID
        
        Returns:
            可用营销活动列表
        """
        now = datetime.now()
        
        where = """
            status='active' 
            AND start_time <= %s 
            AND end_time >= %s
            AND (total_stock > 0 OR total_stock = 0)
        """
        params = [now, now]
        
        if ec_id:
            where += " AND (ec_id=%s OR ec_id IS NULL)"
            params.append(ec_id)
        if project_id:
            where += " AND (project_id=%s OR project_id IS NULL)"
            params.append(project_id)
        
        promotions = db.get_all(f"""
            SELECT * FROM business_promotions
            WHERE {where}
            ORDER BY 
                CASE promo_type 
                    WHEN 'seckill' THEN 1 
                    WHEN 'full_reduce' THEN 2 
                    WHEN 'discount' THEN 3 
                    ELSE 4 
                END
        """, params)
        
        # 过滤适用商品
        result = []
        for promo in promotions:
            apply_type = promo.get('apply_type', 'all')
            
            if apply_type == 'all':
                result.append(promo)
            elif apply_type == 'category' and category_id:
                apply_ids = json.loads(promo.get('apply_ids', '[]'))
                if category_id in apply_ids:
                    result.append(promo)
            elif apply_type == 'product' and product_id:
                apply_ids = json.loads(promo.get('apply_ids', '[]'))
                if product_id in apply_ids:
                    result.append(promo)
        
        return result
    
    @staticmethod
    def calculate_promo_discount(promo, original_amount):
        """
        计算活动优惠金额
        
        Args:
            promo: 活动对象
            original_amount: 原价
        
        Returns:
            (优惠后金额, 优惠金额)
        """
        promo_type = promo.get('promo_type')
        
        if promo_type == 'full_reduce':
            min_amount = float(promo.get('min_amount', 0))
            reduce_amount = float(promo.get('reduce_amount', 0))
            
            if original_amount >= min_amount:
                return max(original_amount - reduce_amount, 0), reduce_amount
            return original_amount, 0
        
        elif promo_type == 'discount':
            discount_rate = float(promo.get('discount_rate', 1.00))
            final_amount = original_amount * discount_rate
            return final_amount, original_amount - final_amount
        
        elif promo_type == 'seckill':
            seckill_price = float(promo.get('seckill_price', 0))
            if seckill_price > 0 and original_amount > seckill_price:
                return seckill_price, original_amount - seckill_price
            return original_amount, 0
        
        return original_amount, 0
    
    @staticmethod
    def record_promo_usage(promo_id, user_id, user_name='', phone='', ec_id=None, project_id=None):
        """
        记录活动使用
        
        Args:
            promo_id: 活动ID
            user_id: 用户ID
            user_name: 用户名
            phone: 手机号
            ec_id: 企业ID
            project_id: 项目ID
        """
        # 检查是否需要限制
        promo = db.get_one("SELECT per_limit FROM business_promotions WHERE id=%s", [promo_id])
        if not promo:
            return False
        
        # 查询用户使用记录
        record = db.get_one("""
            SELECT * FROM business_promotion_users 
            WHERE promotion_id=%s AND user_id=%s
        """, [promo_id, user_id])
        
        if record:
            new_count = record['use_count'] + 1
            if promo['per_limit'] > 0 and new_count > promo['per_limit']:
                return False
            
            db.execute("""
                UPDATE business_promotion_users 
                SET use_count=%s, last_use_at=NOW() 
                WHERE id=%s
            """, [new_count, record['id']])
        else:
            db.execute("""
                INSERT INTO business_promotion_users 
                (promotion_id, user_id, user_name, phone, use_count, ec_id, project_id)
                VALUES (%s, %s, %s, %s, 1, %s, %s)
            """, [promo_id, user_id, user_name, phone, ec_id, project_id])
        
        return True
    
    @staticmethod
    def check_and_deduct_stock(promo_id):
        """
        检查并扣减库存
        
        Args:
            promo_id: 活动ID
        
        Returns:
            (是否成功, 剩余库存)
        """
        promo = db.get_one("SELECT total_stock FROM business_promotions WHERE id=%s", [promo_id])
        
        if not promo:
            return False, 0
        
        stock = promo.get('total_stock', 0)
        
        # 0表示不限库存
        if stock == 0:
            return True, 99999
        
        if stock <= 0:
            return False, 0
        
        # 扣减库存
        db.execute("UPDATE business_promotions SET total_stock = total_stock - 1 WHERE id=%s", [promo_id])
        
        return True, stock - 1