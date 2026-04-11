"""
用户行为追踪与分析服务 V40.0

功能：
1. 用户行为事件采集（浏览、点击、收藏、购买等）
2. 实时行为数据统计
3. 用户画像构建
4. 个性化推荐特征

依赖：
- db: 数据库模块
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from . import db

logger = logging.getLogger(__name__)


class UserBehaviorService:
    """用户行为追踪与分析服务"""

    # 行为类型定义
    BEHAVIOR_TYPES = {
        'browse_product': {'name': '浏览商品', 'weight': 1, 'category': 'browse'},
        'browse_shop': {'name': '浏览门店', 'weight': 1, 'category': 'browse'},
        'browse_category': {'name': '浏览分类', 'weight': 1, 'category': 'browse'},
        'search': {'name': '搜索行为', 'weight': 2, 'category': 'browse'},
        'add_cart': {'name': '加入购物车', 'weight': 5, 'category': 'intention'},
        'remove_cart': {'name': '移出购物车', 'weight': -2, 'category': 'intention'},
        'favorite': {'name': '收藏商品', 'weight': 8, 'category': 'intention'},
        'unfavorite': {'name': '取消收藏', 'weight': -3, 'category': 'intention'},
        'view_detail': {'name': '查看详情', 'weight': 3, 'category': 'engagement'},
        'share': {'name': '分享行为', 'weight': 10, 'category': 'engagement'},
        'checkin': {'name': '签到打卡', 'weight': 5, 'category': 'engagement'},
        'submit_order': {'name': '提交订单', 'weight': 15, 'category': 'conversion'},
        'pay_order': {'name': '支付订单', 'weight': 20, 'category': 'conversion'},
        'cancel_order': {'name': '取消订单', 'weight': -10, 'category': 'conversion'},
        'refund': {'name': '申请退款', 'weight': -15, 'category': 'conversion'},
        'review': {'name': '发表评价', 'weight': 10, 'category': 'engagement'},
        'use_coupon': {'name': '使用优惠券', 'weight': 8, 'category': 'conversion'},
        'claim_coupon': {'name': '领取优惠券', 'weight': 5, 'category': 'intention'},
        'view_notification': {'name': '查看通知', 'weight': 2, 'category': 'engagement'},
        'booking': {'name': '预约场地', 'weight': 15, 'category': 'conversion'},
        'apply': {'name': '提交申请', 'weight': 10, 'category': 'conversion'},
    }

    # 兴趣权重配置
    INTEREST_WEIGHTS = {
        'product': 1.0,
        'category': 0.7,
        'shop': 0.5,
        'tag': 0.8
    }

    def __init__(self):
        self._init_tables()

    def _init_tables(self):
        """初始化所需的数据库表"""
        try:
            # 检查行为事件表
            result = db.get_one("SHOW TABLES LIKE 'business_user_behaviors'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_user_behaviors (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL COMMENT '用户ID',
                        behavior_type VARCHAR(50) NOT NULL COMMENT '行为类型',
                        target_type VARCHAR(50) COMMENT '目标类型: product/category/shop/order',
                        target_id INT COMMENT '目标ID',
                        target_name VARCHAR(200) COMMENT '目标名称（冗余存储）',
                        ec_id INT DEFAULT 1 COMMENT '企业ID',
                        project_id INT DEFAULT 1 COMMENT '项目ID',
                        session_id VARCHAR(100) COMMENT '会话ID',
                        duration INT DEFAULT 0 COMMENT '停留时长(秒)',
                        extra_data TEXT COMMENT '扩展数据 JSON',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_type (user_id, behavior_type),
                        INDEX idx_user_time (user_id, created_at),
                        INDEX idx_target (target_type, target_id),
                        INDEX idx_ec_project (ec_id, project_id),
                        INDEX idx_created (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '用户行为记录表';
                """)
                logger.info("[UserBehavior] 创建 business_user_behaviors 表成功")

            # 检查用户画像表
            result = db.get_one("SHOW TABLES LIKE 'business_user_profiles'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_user_profiles (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL COMMENT '用户ID',
                        ec_id INT DEFAULT 1 COMMENT '企业ID',
                        project_id INT DEFAULT 1 COMMENT '项目ID',
                        interest_products TEXT COMMENT '感兴趣的商品ID列表 JSON',
                        interest_categories TEXT COMMENT '感兴趣的分类 JSON',
                        interest_shops TEXT COMMENT '感兴趣的门店 JSON',
                        interest_tags TEXT COMMENT '兴趣标签 JSON',
                        preference_price_min DECIMAL(10,2) DEFAULT 0 COMMENT '价格偏好下限',
                        preference_price_max DECIMAL(10,2) DEFAULT 0 COMMENT '价格偏好上限',
                        purchase_power VARCHAR(20) DEFAULT 'normal' COMMENT '购买力: low/normal/high/vip',
                        active_score INT DEFAULT 0 COMMENT '活跃度得分 0-100',
                        engagement_score INT DEFAULT 0 COMMENT '参与度得分 0-100',
                        conversion_score INT DEFAULT 0 COMMENT '转化得分 0-100',
                        last_active_at DATETIME COMMENT '最后活跃时间',
                        behavior_count INT DEFAULT 0 COMMENT '累计行为次数',
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_user (user_id),
                        INDEX idx_ec_project (ec_id, project_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '用户画像表';
                """)
                logger.info("[UserBehavior] 创建 business_user_profiles 表成功")

            # 检查用户漏斗分析表
            result = db.get_one("SHOW TABLES LIKE 'business_user_funnel'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_user_funnel (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL COMMENT '用户ID',
                        ec_id INT DEFAULT 1 COMMENT '企业ID',
                        project_id INT DEFAULT 1 COMMENT '项目ID',
                        funnel_date DATE NOT NULL COMMENT '漏斗日期',
                        step1_visit INT DEFAULT 0 COMMENT '步骤1: 访问',
                        step2_browse INT DEFAULT 0 COMMENT '步骤2: 浏览商品',
                        step3_cart INT DEFAULT 0 COMMENT '步骤3: 加购',
                        step4_favorite INT DEFAULT 0 COMMENT '步骤4: 收藏',
                        step5_order INT DEFAULT 0 COMMENT '步骤5: 下单',
                        step6_pay INT DEFAULT 0 COMMENT '步骤6: 支付',
                        total_amount DECIMAL(12,2) DEFAULT 0 COMMENT '当日消费金额',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_user_date (user_id, funnel_date),
                        INDEX idx_ec_project (ec_id, project_id),
                        INDEX idx_funnel_date (funnel_date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '用户行为漏斗表';
                """)
                logger.info("[UserBehavior] 创建 business_user_funnel 表成功")

        except Exception as e:
            logger.error(f"[UserBehavior] 初始化表失败: {e}")

    # ============ 行为采集核心方法 ============

    def track_behavior(self, user_id: int, behavior_type: str,
                      target_type: str = None, target_id: int = None,
                      target_name: str = None, ec_id: int = 1,
                      project_id: int = 1, session_id: str = None,
                      duration: int = 0, extra_data: Dict = None) -> Dict[str, Any]:
        """
        记录用户行为事件

        Args:
            user_id: 用户ID
            behavior_type: 行为类型 (见BEHAVIOR_TYPES)
            target_type: 目标类型 (product/category/shop/order)
            target_id: 目标ID
            target_name: 目标名称
            ec_id: 企业ID
            project_id: 项目ID
            session_id: 会话ID
            duration: 停留时长(秒)
            extra_data: 扩展数据

        Returns:
            dict: 记录结果
        """
        try:
            # 验证行为类型
            if behavior_type not in self.BEHAVIOR_TYPES:
                logger.warning(f"[UserBehavior] 未知行为类型: {behavior_type}")
                behavior_type = 'other'

            # 存储扩展数据
            extra_str = None
            if extra_data:
                try:
                    import json
                    extra_str = json.dumps(extra_data)
                except:
                    pass

            # 插入行为记录
            db.execute("""
                INSERT INTO business_user_behaviors
                (user_id, behavior_type, target_type, target_id, target_name,
                 ec_id, project_id, session_id, duration, extra_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [user_id, behavior_type, target_type, target_id, target_name,
                  ec_id, project_id, session_id, duration, extra_str])

            # 更新用户画像
            self._update_user_profile(user_id, behavior_type, target_type, target_id, ec_id, project_id)

            # 更新漏斗数据
            self._update_funnel_data(user_id, behavior_type, ec_id, project_id)

            logger.info(f"[UserBehavior] 记录行为: user_id={user_id}, type={behavior_type}, target={target_type}:{target_id}")

            return {'success': True, 'msg': '行为记录成功'}

        except Exception as e:
            logger.error(f"[UserBehavior] 记录行为失败: {e}")
            return {'success': False, 'msg': str(e)}

    def _update_user_profile(self, user_id: int, behavior_type: str,
                           target_type: str, target_id: int,
                           ec_id: int, project_id: int):
        """更新用户画像"""
        try:
            import json

            behavior_config = self.BEHAVIOR_TYPES.get(behavior_type, {})
            behavior_weight = behavior_config.get('weight', 1)

            # 获取当前画像
            profile = db.get_one("""
                SELECT * FROM business_user_profiles WHERE user_id=%s
            """, [user_id])

            if not profile:
                # 创建新画像
                db.execute("""
                    INSERT INTO business_user_profiles
                    (user_id, ec_id, project_id, active_score, engagement_score, behavior_count, last_active_at)
                    VALUES (%s, %s, %s, 0, 0, 1, NOW())
                """, [user_id, ec_id, project_id])
                profile = {'interest_products': '[]', 'interest_categories': '[]',
                          'interest_shops': '[]', 'interest_tags': '[]'}

            # 解析现有兴趣数据
            interest_products = json.loads(profile.get('interest_products', '[]')) if profile.get('interest_products') else []
            interest_categories = json.loads(profile.get('interest_categories', '[]')) if profile.get('interest_categories') else []
            interest_shops = json.loads(profile.get('interest_shops', '[]')) if profile.get('interest_shops') else []

            # 更新兴趣数据
            if target_type == 'product' and target_id:
                if behavior_type in ['browse_product', 'add_cart', 'favorite', 'pay_order']:
                    if target_id not in interest_products:
                        interest_products.append(target_id)
                    # 提升权重（最近的行为排在前面）
                    interest_products = [target_id] + [p for p in interest_products if p != target_id]
                elif behavior_type in ['unfavorite', 'remove_cart']:
                    interest_products = [p for p in interest_products if p != target_id]

            elif target_type == 'category' and target_id:
                if behavior_type in ['browse_category', 'browse_product']:
                    if target_id not in interest_categories:
                        interest_categories.append(target_id)
                    interest_categories = [target_id] + [c for c in interest_categories if c != target_id]

            elif target_type == 'shop' and target_id:
                if behavior_type in ['browse_shop']:
                    if target_id not in interest_shops:
                        interest_shops.append(target_id)
                    interest_shops = [target_id] + [s for s in interest_shops if s != target_id]

            # 保留最近100个兴趣
            interest_products = interest_products[:100]
            interest_categories = interest_categories[:50]
            interest_shops = interest_shops[:50]

            # 计算活跃度得分
            active_score = self._calculate_active_score(user_id)
            engagement_score = self._calculate_engagement_score(user_id, behavior_type)
            behavior_count = (profile.get('behavior_count') or 0) + 1

            # 更新画像
            db.execute("""
                UPDATE business_user_profiles
                SET interest_products=%s, interest_categories=%s, interest_shops=%s,
                    active_score=%s, engagement_score=%s, behavior_count=%s,
                    last_active_at=NOW()
                WHERE user_id=%s
            """, [json.dumps(interest_products), json.dumps(interest_categories),
                  json.dumps(interest_shops), active_score, engagement_score,
                  behavior_count, user_id])

        except Exception as e:
            logger.warning(f"[UserBehavior] 更新画像失败: {e}")

    def _calculate_active_score(self, user_id: int) -> int:
        """计算活跃度得分"""
        try:
            # 最近7天的行为数
            week_count = db.get_total("""
                SELECT COUNT(*) FROM business_user_behaviors
                WHERE user_id=%s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """, [user_id])

            # 最近30天的行为数
            month_count = db.get_total("""
                SELECT COUNT(*) FROM business_user_behaviors
                WHERE user_id=%s AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """, [user_id])

            # 综合得分
            week_score = min(50, week_count * 5)
            month_score = min(50, month_count * 2)

            return week_score + month_score

        except Exception as e:
            logger.warning(f"[UserBehavior] 计算活跃度失败: {e}")
            return 0

    def _calculate_engagement_score(self, user_id: int, last_behavior: str) -> int:
        """计算参与度得分"""
        try:
            # 根据最近行为类型计算
            behavior_config = self.BEHAVIOR_TYPES.get(last_behavior, {})
            category = behavior_config.get('category', 'browse')

            # 获取最近行为分布
            recent = db.get_one("""
                SELECT
                    SUM(CASE WHEN behavior_type IN ('browse_product','browse_category','browse_shop','search') THEN 1 ELSE 0 END) as browse_count,
                    SUM(CASE WHEN behavior_type IN ('add_cart','favorite','view_detail') THEN 1 ELSE 0 END) as intent_count,
                    SUM(CASE WHEN behavior_type IN ('pay_order','booking','review','share','checkin') THEN 1 ELSE 0 END) as engage_count
                FROM business_user_behaviors
                WHERE user_id=%s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """, [user_id]) or {}

            browse = int(recent.get('browse_count') or 0)
            intent = int(recent.get('intent_count') or 0)
            engage = int(recent.get('engage_count') or 0)

            # 参与度 = 浏览转化意图 + 意图转化行动
            browse_rate = min(30, browse)
            intent_rate = min(30, intent * 3)
            engage_rate = min(40, engage * 5)

            return browse_rate + intent_rate + engage_rate

        except Exception as e:
            logger.warning(f"[UserBehavior] 计算参与度失败: {e}")
            return 0

    def _update_funnel_data(self, user_id: int, behavior_type: str,
                           ec_id: int, project_id: int):
        """更新用户漏斗数据"""
        try:
            today = datetime.now().date()

            # 根据行为类型确定漏斗步骤
            step_field = None
            if behavior_type in ['browse_product', 'browse_shop', 'search', 'browse_category']:
                step_field = 'step2_browse'
            elif behavior_type in ['add_cart', 'view_detail', 'favorite']:
                step_field = 'step3_cart'
            elif behavior_type == 'submit_order':
                step_field = 'step5_order'
            elif behavior_type == 'pay_order':
                step_field = 'step6_pay'

            if step_field:
                # 检查今日记录是否存在
                existing = db.get_one("""
                    SELECT id FROM business_user_funnel
                    WHERE user_id=%s AND funnel_date=%s
                """, [user_id, today])

                if existing:
                    db.execute(f"""
                        UPDATE business_user_funnel
                        SET {step_field} = {step_field} + 1,
                            updated_at = NOW()
                        WHERE user_id=%s AND funnel_date=%s
                    """, [user_id, today])
                else:
                    db.execute("""
                        INSERT INTO business_user_funnel
                        (user_id, ec_id, project_id, funnel_date, step1_visit, step2_browse)
                        VALUES (%s, %s, %s, %s, 1, %s)
                    """, [user_id, ec_id, project_id, today, 1 if step_field == 'step2_browse' else 0])

        except Exception as e:
            logger.warning(f"[UserBehavior] 更新漏斗失败: {e}")

    # ============ 用户画像查询 ============

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户画像

        Args:
            user_id: 用户ID

        Returns:
            dict: 用户画像
        """
        try:
            import json

            profile = db.get_one("""
                SELECT * FROM business_user_profiles WHERE user_id=%s
            """, [user_id])

            if not profile:
                return {'success': False, 'msg': '用户画像不存在'}

            return {
                'success': True,
                'user_id': user_id,
                'interest_products': json.loads(profile.get('interest_products', '[]')),
                'interest_categories': json.loads(profile.get('interest_categories', '[]')),
                'interest_shops': json.loads(profile.get('interest_shops', '[]')),
                'interest_tags': json.loads(profile.get('interest_tags', '[]')),
                'preference_price': {
                    'min': float(profile.get('preference_price_min') or 0),
                    'max': float(profile.get('preference_price_max') or 0)
                },
                'purchase_power': profile.get('purchase_power', 'normal'),
                'active_score': profile.get('active_score', 0),
                'engagement_score': profile.get('engagement_score', 0),
                'conversion_score': profile.get('conversion_score', 0),
                'last_active_at': profile.get('last_active_at'),
                'behavior_count': profile.get('behavior_count', 0)
            }

        except Exception as e:
            logger.error(f"[UserBehavior] 获取画像失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_recent_behaviors(self, user_id: int, days: int = 7,
                            behavior_type: str = None,
                            limit: int = 50) -> List[Dict]:
        """
        获取用户最近行为记录

        Args:
            user_id: 用户ID
            days: 查询天数
            behavior_type: 行为类型筛选
            limit: 返回数量限制

        Returns:
            list: 行为记录列表
        """
        try:
            where = "user_id=%s AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"
            params = [user_id, days]

            if behavior_type:
                where += " AND behavior_type=%s"
                params.append(behavior_type)

            behaviors = db.get_all(f"""
                SELECT * FROM business_user_behaviors
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s
            """, params + [limit]) or []

            # 补充行为名称
            for b in behaviors:
                config = self.BEHAVIOR_TYPES.get(b.get('behavior_type'), {})
                b['behavior_name'] = config.get('name', b.get('behavior_type'))

            return behaviors

        except Exception as e:
            logger.error(f"[UserBehavior] 获取行为记录失败: {e}")
            return []

    def get_behavior_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        获取用户行为统计

        Args:
            user_id: 用户ID
            days: 统计天数

        Returns:
            dict: 统计结果
        """
        try:
            # 行为类型分布
            type_stats = db.get_all("""
                SELECT behavior_type, COUNT(*) as count
                FROM business_user_behaviors
                WHERE user_id=%s AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY behavior_type
                ORDER BY count DESC
            """, [user_id, days]) or []

            # 每日行为趋势
            daily_stats = db.get_all("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM business_user_behaviors
                WHERE user_id=%s AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """, [user_id, days]) or []

            # 统计汇总
            total = sum(int(s.get('count', 0)) for s in type_stats)
            unique_days = len(daily_stats)

            return {
                'success': True,
                'total_behaviors': total,
                'active_days': unique_days,
                'avg_daily': round(total / max(unique_days, 1), 1),
                'behavior_distribution': [
                    {
                        'type': s['behavior_type'],
                        'name': self.BEHAVIOR_TYPES.get(s['behavior_type'], {}).get('name', s['behavior_type']),
                        'count': int(s['count']),
                        'percentage': round(int(s['count']) / max(total, 1) * 100, 1)
                    }
                    for s in type_stats
                ],
                'daily_trend': [
                    {
                        'date': str(s['date']),
                        'count': int(s['count'])
                    }
                    for s in daily_stats
                ]
            }

        except Exception as e:
            logger.error(f"[UserBehavior] 获取统计失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_funnel_analysis(self, ec_id: int = None, project_id: int = None,
                           days: int = 30) -> Dict[str, Any]:
        """
        获取漏斗分析数据

        Args:
            ec_id: 企业ID
            project_id: 项目ID
            days: 分析天数

        Returns:
            dict: 漏斗分析结果
        """
        try:
            where = "funnel_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)"
            params = [days]

            if ec_id:
                where += " AND ec_id=%s"
                params.append(ec_id)
            if project_id:
                where += " AND project_id=%s"
                params.append(project_id)

            stats = db.get_one(f"""
                SELECT
                    COUNT(DISTINCT user_id) as total_users,
                    SUM(step2_browse) as total_browse,
                    SUM(step3_cart) as total_cart,
                    SUM(step4_favorite) as total_favorite,
                    SUM(step5_order) as total_order,
                    SUM(step6_pay) as total_pay,
                    SUM(total_amount) as total_amount
                FROM business_user_funnel
                WHERE {where}
            """, params) or {}

            total_users = int(stats.get('total_users') or 0)
            browse = int(stats.get('total_browse') or 0)
            cart = int(stats.get('total_cart') or 0)
            favorite = int(stats.get('total_favorite') or 0)
            order = int(stats.get('total_order') or 0)
            pay = int(stats.get('total_pay') or 0)

            return {
                'success': True,
                'period_days': days,
                'total_users': total_users,
                'funnel': {
                    'visit': {'name': '访问', 'count': total_users},
                    'browse': {'name': '浏览商品', 'count': browse, 'conversion': round(browse / max(total_users, 1) * 100, 1)},
                    'cart': {'name': '加购', 'count': cart, 'conversion': round(cart / max(browse, 1) * 100, 1)},
                    'favorite': {'name': '收藏', 'count': favorite, 'conversion': round(favorite / max(cart, 1) * 100, 1)},
                    'order': {'name': '下单', 'count': order, 'conversion': round(order / max(favorite, 1) * 100, 1)},
                    'pay': {'name': '支付', 'count': pay, 'conversion': round(pay / max(order, 1) * 100, 1)},
                },
                'overall_conversion': round(pay / max(total_users, 1) * 100, 2),
                'total_gmv': float(stats.get('total_amount') or 0)
            }

        except Exception as e:
            logger.error(f"[UserBehavior] 获取漏斗分析失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ 便捷快捷方法 ============

    def track_product_view(self, user_id: int, product_id: int, product_name: str,
                          ec_id: int = 1, project_id: int = 1, duration: int = 0):
        """快捷方法：记录商品浏览"""
        return self.track_behavior(
            user_id=user_id, behavior_type='browse_product',
            target_type='product', target_id=product_id,
            target_name=product_name, ec_id=ec_id,
            project_id=project_id, duration=duration
        )

    def track_add_cart(self, user_id: int, product_id: int, product_name: str,
                      ec_id: int = 1, project_id: int = 1, quantity: int = 1):
        """快捷方法：记录加入购物车"""
        return self.track_behavior(
            user_id=user_id, behavior_type='add_cart',
            target_type='product', target_id=product_id,
            target_name=product_name, ec_id=ec_id,
            project_id=project_id, extra_data={'quantity': quantity}
        )

    def track_favorite(self, user_id: int, product_id: int, product_name: str,
                      ec_id: int = 1, project_id: int = 1, action: str = 'add'):
        """快捷方法：记录收藏行为"""
        behavior_type = 'favorite' if action == 'add' else 'unfavorite'
        return self.track_behavior(
            user_id=user_id, behavior_type=behavior_type,
            target_type='product', target_id=product_id,
            target_name=product_name, ec_id=ec_id,
            project_id=project_id
        )

    def track_order(self, user_id: int, order_id: int, order_no: str,
                   behavior_type: str, ec_id: int = 1, project_id: int = 1,
                   amount: float = 0):
        """快捷方法：记录订单相关行为"""
        return self.track_behavior(
            user_id=user_id, behavior_type=behavior_type,
            target_type='order', target_id=order_id,
            target_name=order_no, ec_id=ec_id,
            project_id=project_id, extra_data={'amount': amount}
        )


# 单例实例
user_behavior_service = UserBehaviorService()
