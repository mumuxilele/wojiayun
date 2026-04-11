"""
V38.0 最优折扣计算服务
提供优惠券和积分的最优组合计算

功能：
1. 计算最优优惠券+积分组合
2. 提供折扣方案推荐
3. 实时计算最佳抵扣金额
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)


class DiscountCalculatorService(BaseService):
    """最优折扣计算服务"""
    
    SERVICE_NAME = 'DiscountCalculatorService'
    
    # 积分兑换比例：100积分 = 1元
    POINTS_RATE = 100
    POINTS_MAX_DEDUCTION_RATE = 0.2  # 积分最多抵扣订单金额的20%
    
    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        base['points_rate'] = self.POINTS_RATE
        base['max_deduction_rate'] = self.POINTS_MAX_DEDUCTION_RATE
        return base
    
    def get_available_coupons(self, user_id: int, order_amount: float,
                             ec_id: int, project_id: int) -> List[Dict]:
        """
        获取用户可用的优惠券列表
        
        Returns:
            List: 可用优惠券列表
        """
        coupons = db.get_all("""
            SELECT 
                uc.id as user_coupon_id,
                uc.coupon_id,
                c.coupon_name,
                c.coupon_type,
                c.discount_value,
                c.min_amount,
                c.max_discount,
                c.expire_at
            FROM business_user_coupons uc
            JOIN business_coupons c ON c.id = uc.coupon_id
            WHERE uc.user_id = %s 
              AND uc.status = 'unused'
              AND c.ec_id = %s 
              AND c.project_id = %s
              AND c.status = 'active'
              AND c.expire_at >= CURDATE()
              AND (%s >= c.min_amount OR c.min_amount = 0)
        """, [user_id, ec_id, project_id, order_amount])
        
        result = []
        for c in (coupons or []):
            discount = self._calculate_coupon_discount(
                c['coupon_type'], 
                c['discount_value'], 
                c['max_discount'],
                order_amount
            )
            result.append({
                'user_coupon_id': c['user_coupon_id'],
                'coupon_id': c['coupon_id'],
                'coupon_name': c['coupon_name'],
                'coupon_type': c['coupon_type'],
                'discount_value': float(c['discount_value']),
                'min_amount': float(c['min_amount']),
                'max_discount': float(c['max_discount']) if c['max_discount'] else 0,
                'discount_amount': discount,
                'expire_at': str(c['expire_at']) if c['expire_at'] else None,
            })
        
        # 按优惠金额降序排列
        result.sort(key=lambda x: x['discount_amount'], reverse=True)
        return result
    
    def _calculate_coupon_discount(self, coupon_type: str, discount_value: float,
                                  max_discount: float, order_amount: float) -> float:
        """计算优惠券优惠金额"""
        if coupon_type == 'cash':
            # 现金券：直接减免
            discount = float(discount_value)
        elif coupon_type == 'discount':
            # 折扣券：订单金额 * (1 - 折扣率)
            discount = order_amount * (1 - float(discount_value))
            if max_discount and max_discount > 0:
                discount = min(discount, float(max_discount))
        else:
            discount = 0
        
        # 优惠金额不能超过订单金额
        return min(discount, order_amount)
    
    def calculate_optimal_discount(self, user_id: int, order_amount: float,
                                 user_points: int, ec_id: int, project_id: int,
                                 force_use_coupon_id: int = None) -> Dict:
        """
        计算最优折扣组合
        
        Args:
            user_id: 用户ID
            order_amount: 订单金额
            user_points: 用户可用积分
            ec_id: 企业ID
            project_id: 项目ID
            force_use_coupon_id: 强制使用的优惠券ID（可选）
        
        Returns:
            {
                "success": True,
                "optimal_plan": {
                    "coupon": {...},  # 使用的优惠券
                    "use_points": 1000,  # 使用的积分
                    "points_deduction": 10.0,  # 积分抵扣金额
                    "total_discount": 40.0,  # 总优惠
                    "final_amount": 60.0  # 最终应付金额
                },
                "all_plans": [...]  # 所有可用方案对比
            }
        """
        if order_amount <= 0:
            return {
                'success': False,
                'msg': '订单金额必须大于0',
            }
        
        # 获取可用优惠券
        available_coupons = self.get_available_coupons(
            user_id, order_amount, ec_id, project_id
        )
        
        # 如果指定了强制使用的优惠券
        if force_use_coupon_id:
            available_coupons = [
                c for c in available_coupons 
                if c['user_coupon_id'] == force_use_coupon_id
            ]
        
        all_plans = []
        
        # 方案1：不使用任何优惠
        plan_no_discount = {
            'plan_name': '不使用优惠',
            'coupon': None,
            'use_points': 0,
            'points_deduction': 0,
            'coupon_discount': 0,
            'total_discount': 0,
            'final_amount': order_amount,
        }
        all_plans.append(plan_no_discount)
        
        # 方案2-4：不使用优惠券，只用积分
        max_points_for_order = min(
            user_points,
            int(order_amount * self.POINTS_MAX_DEDUCTION_RATE * self.POINTS_RATE)
        )
        
        # 分段测试积分使用量
        for use_rate in [0.25, 0.5, 1.0]:
            use_points = int(max_points_for_order * use_rate / 100) * 100  # 保留到100的整数倍
            if use_points > 0:
                points_deduction = use_points / self.POINTS_RATE
                plan = {
                    'plan_name': f'仅使用{use_points}积分',
                    'coupon': None,
                    'use_points': use_points,
                    'points_deduction': round(points_deduction, 2),
                    'coupon_discount': 0,
                    'total_discount': round(points_deduction, 2),
                    'final_amount': round(order_amount - points_deduction, 2),
                }
                all_plans.append(plan)
        
        # 方案：使用优惠券 + 积分
        for coupon in available_coupons:
            coupon_discount = coupon['discount_amount']
            after_coupon = order_amount - coupon_discount
            
            # 计算使用优惠券后，最多能用多少积分
            max_points_after_coupon = min(
                user_points,
                int(after_coupon * self.POINTS_MAX_DEDUCTION_RATE * self.POINTS_RATE)
            )
            
            # 找出最优积分使用量
            best_points = 0
            best_final = after_coupon
            
            for use_rate in [0.25, 0.5, 0.75, 1.0]:
                use_points = int(max_points_after_coupon * use_rate / 100) * 100
                if use_points > 0:
                    points_deduction = use_points / self.POINTS_RATE
                    final = after_coupon - points_deduction
                    if final < best_final:
                        best_final = final
                        best_points = use_points
            
            plan = {
                'plan_name': f'{coupon["coupon_name"]} + {best_points}积分',
                'coupon': coupon,
                'use_points': best_points,
                'points_deduction': round(best_points / self.POINTS_RATE, 2),
                'coupon_discount': round(coupon_discount, 2),
                'total_discount': round(coupon_discount + best_points / self.POINTS_RATE, 2),
                'final_amount': round(max(0, best_final), 2),
            }
            all_plans.append(plan)
        
        # 找出最优方案
        optimal_plan = min(all_plans, key=lambda x: x['final_amount'])
        
        # 如果最优方案和不使用优惠一样，不推荐使用
        if optimal_plan['total_discount'] == 0:
            optimal_plan['recommend'] = True
            optimal_plan['recommend_reason'] = '当前没有可用优惠'
        elif optimal_plan['final_amount'] < order_amount * 0.9:  # 节省超过10%
            optimal_plan['recommend'] = True
            optimal_plan['recommend_reason'] = f'可节省¥{optimal_plan["total_discount"]:.2f}'
        else:
            optimal_plan['recommend'] = False
            optimal_plan['recommend_reason'] = '优惠幅度较小'
        
        return {
            'success': True,
            'order_amount': order_amount,
            'user_points': user_points,
            'points_rate': self.POINTS_RATE,
            'max_points_for_order': max_points_for_order,
            'available_coupons_count': len(available_coupons),
            'optimal_plan': optimal_plan,
            'all_plans': all_plans[:10],  # 最多返回10个方案
        }
    
    def calculate_preview(self, order_amount: float, coupon: Dict = None,
                         use_points: int = 0) -> Dict:
        """
        预览计算（不查询数据库）
        
        Args:
            order_amount: 订单金额
            coupon: 优惠券信息
            use_points: 使用积分数
        
        Returns:
            计算结果预览
        """
        coupon_discount = 0
        if coupon:
            coupon_discount = self._calculate_coupon_discount(
                coupon['coupon_type'],
                coupon['discount_value'],
                coupon.get('max_discount', 0),
                order_amount
            )
        
        after_coupon = max(0, order_amount - coupon_discount)
        
        # 校验积分使用量
        max_points_allowed = int(after_coupon * self.POINTS_MAX_DEDUCTION_RATE * self.POINTS_RATE)
        use_points = min(use_points, max_points_allowed)
        points_deduction = use_points / self.POINTS_RATE
        
        final_amount = max(0, after_coupon - points_deduction)
        total_discount = coupon_discount + points_deduction
        
        return {
            'order_amount': order_amount,
            'coupon_discount': round(coupon_discount, 2),
            'after_coupon': round(after_coupon, 2),
            'use_points': use_points,
            'points_deduction': round(points_deduction, 2),
            'final_amount': round(final_amount, 2),
            'total_discount': round(total_discount, 2),
            'savings_percent': round(total_discount / order_amount * 100, 1) if order_amount > 0 else 0,
        }


# 全局实例
discount_calculator = DiscountCalculatorService()
