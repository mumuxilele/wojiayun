"""
智能促销引擎 V44.0

功能:
1. 满减活动 (full_reduction) - 满X元减Y元
2. 阶梯满减 (ladder_reduction) - 满100-10/满200-30/满500-100
3. 折扣活动 (discount) - 全场X折
4. 件数满减 (count_reduction) - 满X件减Y元/打X折
5. 促销叠加规则 - 与优惠券是否可叠加
6. 用户端"差X元享优惠"提示计算
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from . import db
from .cache_service import cache_get, cache_set

logger = logging.getLogger(__name__)


class PromotionType:
    """促销类型"""
    FULL_REDUCTION = 'full_reduction'    # 满减
    LADDER = 'ladder_reduction'          # 阶梯满减
    DISCOUNT = 'discount'               # 折扣
    COUNT_REDUCTION = 'count_reduction'  # 件数满减
    FREE_SHIPPING = 'free_shipping'      # 免邮


class PromotionEngineService:
    """
    智能促销引擎
    负责促销规则的存储、匹配、计算
    """

    CACHE_TTL = 300  # 5分钟缓存

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """确保促销规则表存在"""
        try:
            exists = db.get_one("SHOW TABLES LIKE 'business_promotion_rules'")
            if not exists:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_promotion_rules (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        rule_name VARCHAR(100) NOT NULL COMMENT '规则名称',
                        rule_type VARCHAR(30) NOT NULL COMMENT '类型:full_reduction/ladder_reduction/discount/count_reduction/free_shipping',
                        rule_config TEXT NOT NULL COMMENT '规则配置JSON',
                        apply_scope VARCHAR(20) DEFAULT 'all' COMMENT '适用范围:all/category/product',
                        scope_ids TEXT COMMENT '适用范围ID列表JSON',
                        can_stack_coupon TINYINT(1) DEFAULT 0 COMMENT '是否可与优惠券叠加',
                        can_stack_points TINYINT(1) DEFAULT 1 COMMENT '是否可与积分抵扣叠加',
                        priority INT DEFAULT 0 COMMENT '优先级，越大越优先',
                        status VARCHAR(10) DEFAULT 'active' COMMENT '状态:active/inactive',
                        start_time DATETIME COMMENT '生效时间',
                        end_time DATETIME COMMENT '失效时间',
                        ec_id INT DEFAULT 1,
                        project_id INT DEFAULT 1,
                        created_by INT COMMENT '创建人',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_type (rule_type),
                        INDEX idx_status (status),
                        INDEX idx_time (start_time, end_time),
                        INDEX idx_scope (ec_id, project_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='促销规则表'
                """)
                logger.info("business_promotion_rules 表已创建")

                # 插入默认促销规则示例
                self._insert_sample_rules()
        except Exception as e:
            logger.warning(f"初始化促销规则表失败: {e}")

    def _insert_sample_rules(self):
        """插入示例促销规则"""
        try:
            now = datetime.now()
            # 满100减10 满200减25 满500减70 阶梯满减
            db.execute("""
                INSERT IGNORE INTO business_promotion_rules
                (rule_name, rule_type, rule_config, can_stack_coupon, can_stack_points, priority, status, start_time, end_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                '阶梯满减活动',
                PromotionType.LADDER,
                json.dumps([
                    {"threshold": 100, "discount": 10, "label": "满100减10"},
                    {"threshold": 200, "discount": 25, "label": "满200减25"},
                    {"threshold": 500, "discount": 70, "label": "满500减70"},
                ]),
                0, 1, 10, 'active',
                now.strftime('%Y-%m-%d 00:00:00'),
                '2099-12-31 23:59:59'
            ])
            logger.info("已插入默认促销规则示例")
        except Exception as e:
            logger.warning(f"插入示例规则失败: {e}")

    # ============ 规则查询 ============

    def get_active_rules(self, ec_id: int = None, project_id: int = None) -> List[Dict]:
        """获取当前有效的促销规则（带缓存）"""
        cache_key = f"promo_rules_{ec_id}_{project_id}"
        cached = cache_get(cache_key)
        if cached:
            return cached

        now = datetime.now()
        where = "status='active' AND (start_time IS NULL OR start_time <= %s) AND (end_time IS NULL OR end_time >= %s)"
        params = [now, now]

        if ec_id:
            where += " AND (ec_id=%s OR ec_id IS NULL OR ec_id=1)"
            params.append(ec_id)
        if project_id:
            where += " AND (project_id=%s OR project_id IS NULL OR project_id=1)"
            params.append(project_id)

        rules = db.get_all(f"""
            SELECT * FROM business_promotion_rules
            WHERE {where}
            ORDER BY priority DESC, id ASC
        """, params) or []

        # 解析rule_config JSON
        for rule in rules:
            try:
                if isinstance(rule.get('rule_config'), str):
                    rule['rule_config'] = json.loads(rule['rule_config'])
            except Exception:
                rule['rule_config'] = {}

        cache_set(cache_key, rules, self.CACHE_TTL)
        return rules

    def get_rule_by_id(self, rule_id: int) -> Optional[Dict]:
        """获取单条规则"""
        rule = db.get_one("SELECT * FROM business_promotion_rules WHERE id=%s", [rule_id])
        if rule and isinstance(rule.get('rule_config'), str):
            try:
                rule['rule_config'] = json.loads(rule['rule_config'])
            except Exception:
                pass
        return rule

    # ============ 核心计算逻辑 ============

    def calculate_promotion(
        self,
        order_amount: float,
        item_count: int = 1,
        ec_id: int = None,
        project_id: int = None,
        product_ids: List[int] = None,
        category_ids: List[int] = None,
    ) -> Dict[str, Any]:
        """
        计算订单最优促销优惠

        Args:
            order_amount: 订单原始金额
            item_count: 商品件数
            ec_id: 企业ID
            project_id: 项目ID
            product_ids: 订单商品ID列表（用于品类过滤）
            category_ids: 订单商品分类ID列表

        Returns:
            {
                "applicable_rules": [...],      # 适用的规则列表
                "best_rule": {...},             # 最优规则
                "discount_amount": 25.0,        # 最大优惠金额
                "final_amount": 175.0,          # 最终金额
                "next_tier_hint": {...},        # 差X元享受下一档优惠
                "can_stack_coupon": True,       # 是否可叠加优惠券
                "can_stack_points": True,       # 是否可叠加积分
            }
        """
        rules = self.get_active_rules(ec_id, project_id)
        applicable_rules = []
        best_discount = 0.0
        best_rule = None
        next_tier_hint = None

        for rule in rules:
            result = self._apply_rule(rule, order_amount, item_count, product_ids, category_ids)
            if result['applicable']:
                applicable_rules.append({
                    'id': rule['id'],
                    'name': rule['rule_name'],
                    'type': rule['rule_type'],
                    'discount': result['discount'],
                    'label': result.get('label', ''),
                    'can_stack_coupon': bool(rule.get('can_stack_coupon')),
                    'can_stack_points': bool(rule.get('can_stack_points')),
                })
                if result['discount'] > best_discount:
                    best_discount = result['discount']
                    best_rule = applicable_rules[-1]

        # 计算下一档优惠提示（只对阶梯满减有意义）
        for rule in rules:
            if rule['rule_type'] == PromotionType.LADDER:
                hint = self._calc_next_tier(rule, order_amount)
                if hint and (next_tier_hint is None or hint['gap'] < next_tier_hint['gap']):
                    next_tier_hint = hint

        can_stack_coupon = best_rule.get('can_stack_coupon', False) if best_rule else False
        can_stack_points = best_rule.get('can_stack_points', True) if best_rule else True

        final_amount = max(0.0, round(order_amount - best_discount, 2))

        return {
            'order_amount': order_amount,
            'applicable_rules': applicable_rules,
            'best_rule': best_rule,
            'discount_amount': round(best_discount, 2),
            'final_amount': final_amount,
            'next_tier_hint': next_tier_hint,
            'can_stack_coupon': can_stack_coupon,
            'can_stack_points': can_stack_points,
        }

    def _apply_rule(
        self,
        rule: Dict,
        order_amount: float,
        item_count: int,
        product_ids: List[int] = None,
        category_ids: List[int] = None,
    ) -> Dict[str, Any]:
        """应用单条规则，返回优惠金额"""
        rule_type = rule['rule_type']
        config = rule['rule_config']

        # 检查适用范围
        if not self._check_scope(rule, product_ids, category_ids):
            return {'applicable': False, 'discount': 0}

        if rule_type == PromotionType.FULL_REDUCTION:
            return self._calc_full_reduction(config, order_amount)

        elif rule_type == PromotionType.LADDER:
            return self._calc_ladder_reduction(config, order_amount)

        elif rule_type == PromotionType.DISCOUNT:
            return self._calc_discount(config, order_amount)

        elif rule_type == PromotionType.COUNT_REDUCTION:
            return self._calc_count_reduction(config, order_amount, item_count)

        elif rule_type == PromotionType.FREE_SHIPPING:
            return self._calc_free_shipping(config, order_amount)

        return {'applicable': False, 'discount': 0}

    def _check_scope(self, rule: Dict, product_ids: List[int], category_ids: List[int]) -> bool:
        """检查规则适用范围"""
        scope = rule.get('apply_scope', 'all')
        if scope == 'all':
            return True

        scope_ids_raw = rule.get('scope_ids', '[]')
        try:
            scope_ids = json.loads(scope_ids_raw) if isinstance(scope_ids_raw, str) else scope_ids_raw
        except Exception:
            scope_ids = []

        if not scope_ids:
            return True

        if scope == 'product' and product_ids:
            return bool(set(product_ids) & set(scope_ids))

        if scope == 'category' and category_ids:
            return bool(set(category_ids) & set(scope_ids))

        return False

    def _calc_full_reduction(self, config: Any, amount: float) -> Dict:
        """满X减Y计算"""
        if isinstance(config, dict):
            threshold = float(config.get('threshold', 0))
            discount = float(config.get('discount', 0))
        else:
            return {'applicable': False, 'discount': 0}

        if amount >= threshold:
            return {
                'applicable': True,
                'discount': discount,
                'label': f"满{threshold:.0f}减{discount:.0f}",
            }
        return {'applicable': False, 'discount': 0}

    def _calc_ladder_reduction(self, config: Any, amount: float) -> Dict:
        """阶梯满减计算：找到满足条件的最高档"""
        if not isinstance(config, list):
            return {'applicable': False, 'discount': 0}

        best_discount = 0.0
        best_label = ''
        for tier in sorted(config, key=lambda x: float(x.get('threshold', 0)), reverse=True):
            threshold = float(tier.get('threshold', 0))
            discount = float(tier.get('discount', 0))
            if amount >= threshold:
                if discount > best_discount:
                    best_discount = discount
                    best_label = tier.get('label', f"满{threshold:.0f}减{discount:.0f}")
                break  # 取第一个（最高档）满足条件的

        if best_discount > 0:
            return {'applicable': True, 'discount': best_discount, 'label': best_label}
        return {'applicable': False, 'discount': 0}

    def _calc_discount(self, config: Any, amount: float) -> Dict:
        """折扣计算"""
        if isinstance(config, dict):
            min_amount = float(config.get('min_amount', 0))
            rate = float(config.get('discount_rate', 1.0))  # 0.9 = 九折
        else:
            return {'applicable': False, 'discount': 0}

        if amount >= min_amount and 0 < rate < 1:
            discount = round(amount * (1 - rate), 2)
            return {
                'applicable': True,
                'discount': discount,
                'label': f"全场{rate * 10:.1f}折",
            }
        return {'applicable': False, 'discount': 0}

    def _calc_count_reduction(self, config: Any, amount: float, item_count: int) -> Dict:
        """件数满减"""
        if isinstance(config, dict):
            min_count = int(config.get('min_count', 0))
            discount = float(config.get('discount', 0))
            discount_rate = float(config.get('discount_rate', 1.0))
        else:
            return {'applicable': False, 'discount': 0}

        if item_count >= min_count:
            if discount > 0:
                return {'applicable': True, 'discount': discount, 'label': f"满{min_count}件减{discount:.0f}元"}
            elif discount_rate < 1:
                d = round(amount * (1 - discount_rate), 2)
                return {'applicable': True, 'discount': d, 'label': f"满{min_count}件{discount_rate * 10:.1f}折"}
        return {'applicable': False, 'discount': 0}

    def _calc_free_shipping(self, config: Any, amount: float) -> Dict:
        """免邮计算"""
        if isinstance(config, dict):
            threshold = float(config.get('threshold', 99))
            shipping_fee = float(config.get('shipping_fee', 10))
        else:
            return {'applicable': False, 'discount': 0}

        if amount >= threshold:
            return {'applicable': True, 'discount': shipping_fee, 'label': f"满{threshold:.0f}元免邮"}
        return {'applicable': False, 'discount': 0}

    def _calc_next_tier(self, rule: Dict, amount: float) -> Optional[Dict]:
        """计算距离下一档优惠还差多少钱"""
        config = rule['rule_config']
        if not isinstance(config, list):
            return None

        tiers = sorted(config, key=lambda x: float(x.get('threshold', 0)))
        for tier in tiers:
            threshold = float(tier.get('threshold', 0))
            discount = float(tier.get('discount', 0))
            if amount < threshold:
                gap = round(threshold - amount, 2)
                return {
                    'gap': gap,
                    'threshold': threshold,
                    'discount': discount,
                    'label': tier.get('label', f"满{threshold:.0f}减{discount:.0f}"),
                    'hint': f"再消费 ¥{gap:.2f} 可享{tier.get('label', f'满{threshold:.0f}减{discount:.0f}')}",
                }
        return None

    # ============ 管理端操作 ============

    def create_rule(self, data: Dict, created_by: int, ec_id: int, project_id: int) -> Dict:
        """创建促销规则"""
        try:
            rule_config = data.get('rule_config', {})
            if isinstance(rule_config, (dict, list)):
                rule_config = json.dumps(rule_config, ensure_ascii=False)

            rule_id = db.insert("""
                INSERT INTO business_promotion_rules
                (rule_name, rule_type, rule_config, apply_scope, scope_ids,
                 can_stack_coupon, can_stack_points, priority, status, start_time, end_time,
                 ec_id, project_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                data.get('rule_name', '未命名活动'),
                data.get('rule_type', PromotionType.FULL_REDUCTION),
                rule_config,
                data.get('apply_scope', 'all'),
                json.dumps(data.get('scope_ids', [])),
                int(data.get('can_stack_coupon', 0)),
                int(data.get('can_stack_points', 1)),
                int(data.get('priority', 0)),
                data.get('status', 'active'),
                data.get('start_time'),
                data.get('end_time'),
                ec_id, project_id, created_by
            ])
            self._clear_cache(ec_id, project_id)
            return {'success': True, 'rule_id': rule_id, 'msg': '促销规则创建成功'}
        except Exception as e:
            logger.error(f"创建促销规则失败: {e}")
            return {'success': False, 'msg': f'创建失败: {e}'}

    def update_rule(self, rule_id: int, data: Dict, ec_id: int, project_id: int) -> Dict:
        """更新促销规则"""
        try:
            rule = self.get_rule_by_id(rule_id)
            if not rule:
                return {'success': False, 'msg': '规则不存在'}

            rule_config = data.get('rule_config', rule.get('rule_config', {}))
            if isinstance(rule_config, (dict, list)):
                rule_config = json.dumps(rule_config, ensure_ascii=False)

            db.execute("""
                UPDATE business_promotion_rules
                SET rule_name=%s, rule_type=%s, rule_config=%s, apply_scope=%s,
                    can_stack_coupon=%s, can_stack_points=%s, priority=%s,
                    status=%s, start_time=%s, end_time=%s, updated_at=NOW()
                WHERE id=%s
            """, [
                data.get('rule_name', rule['rule_name']),
                data.get('rule_type', rule['rule_type']),
                rule_config,
                data.get('apply_scope', rule.get('apply_scope', 'all')),
                int(data.get('can_stack_coupon', rule.get('can_stack_coupon', 0))),
                int(data.get('can_stack_points', rule.get('can_stack_points', 1))),
                int(data.get('priority', rule.get('priority', 0))),
                data.get('status', rule.get('status', 'active')),
                data.get('start_time', rule.get('start_time')),
                data.get('end_time', rule.get('end_time')),
                rule_id
            ])
            self._clear_cache(ec_id, project_id)
            return {'success': True, 'msg': '更新成功'}
        except Exception as e:
            logger.error(f"更新促销规则失败: {e}")
            return {'success': False, 'msg': f'更新失败: {e}'}

    def delete_rule(self, rule_id: int, ec_id: int, project_id: int) -> Dict:
        """删除/下架促销规则"""
        try:
            db.execute(
                "UPDATE business_promotion_rules SET status='inactive', updated_at=NOW() WHERE id=%s",
                [rule_id]
            )
            self._clear_cache(ec_id, project_id)
            return {'success': True, 'msg': '已下架促销规则'}
        except Exception as e:
            return {'success': False, 'msg': f'操作失败: {e}'}

    def get_rule_list(self, ec_id: int, project_id: int, page: int = 1, page_size: int = 20) -> Dict:
        """管理端分页查询规则列表"""
        where = "ec_id=%s AND project_id=%s"
        params = [ec_id, project_id]
        total = db.get_total(f"SELECT COUNT(*) FROM business_promotion_rules WHERE {where}", params)
        offset = (page - 1) * page_size
        rules = db.get_all(f"""
            SELECT id, rule_name, rule_type, rule_config, apply_scope, can_stack_coupon,
                   can_stack_points, priority, status, start_time, end_time, created_at
            FROM business_promotion_rules WHERE {where}
            ORDER BY priority DESC, created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset]) or []

        for rule in rules:
            try:
                if isinstance(rule.get('rule_config'), str):
                    rule['rule_config'] = json.loads(rule['rule_config'])
            except Exception:
                pass

        return {
            'items': rules,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0,
        }

    def _clear_cache(self, ec_id: int, project_id: int):
        """清除促销规则缓存"""
        try:
            from .cache_service import cache_delete
            cache_delete(f"promo_rules_{ec_id}_{project_id}")
        except Exception:
            pass


# 全局单例
promotion_engine = PromotionEngineService()
