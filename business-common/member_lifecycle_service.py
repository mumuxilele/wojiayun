"""
会员生命周期自动化服务 V40.0

功能：
1. 会员生命周期阶段管理（新用户 -> 活跃 -> 沉睡 -> 流失）
2. 自动化触达策略（欢迎短信、生日祝福、流失挽回等）
3. 会员健康度评分
4. 自动化任务调度

依赖：
- notification: 通知服务
- member_service: 会员服务
- push_service: 推送服务
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from . import db
from .notification import send_notification

logger = logging.getLogger(__name__)


class MemberLifecycleService:
    """会员生命周期自动化服务"""

    # 会员生命周期阶段
    STAGE_NEW_USER = 'new_user'           # 新用户（注册7天内）
    STAGE_ACTIVE = 'active'              # 活跃用户（30天内有行为）
    STAGE_HOT = 'hot'                    # 高价值用户（月消费3次以上）
    STAGE_SLEEPING = 'sleeping'          # 沉睡用户（30-90天无行为）
    STAGE_CHURNING = 'churning'          # 流失预警（90-180天无行为）
    STAGE_CHURNED = 'churned'           # 已流失（180天以上无行为）

    # 阶段配置
    STAGE_CONFIG = {
        STAGE_NEW_USER: {
            'name': '新用户',
            'days_threshold': 7,
            'color': '#4CAF50',
            'strategy': 'welcome'
        },
        STAGE_ACTIVE: {
            'name': '活跃用户',
            'days_threshold': 30,
            'color': '#2196F3',
            'strategy': 'retention'
        },
        STAGE_HOT: {
            'name': '高价值用户',
            'days_threshold': 30,
            'color': '#FF9800',
            'strategy': 'vip'
        },
        STAGE_SLEEPING: {
            'name': '沉睡用户',
            'days_threshold': 90,
            'color': '#9E9E9E',
            'strategy': 'awaken'
        },
        STAGE_CHURNING: {
            'name': '流失预警',
            'days_threshold': 180,
            'color': '#F44336',
            'strategy': 'recover'
        },
        STAGE_CHURNED: {
            'name': '已流失',
            'days_threshold': None,
            'color': '#607D8B',
            'strategy': 'winback'
        }
    }

    # 任务配置
    BATCH_SIZE = 100
    SCHEDULE_INTERVAL_HOURS = 6

    def __init__(self):
        self._init_tables()

    def _init_tables(self):
        """初始化所需的数据库表"""
        try:
            # 检查会员生命周期表是否存在
            result = db.get_one("SHOW TABLES LIKE 'business_member_lifecycle'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_member_lifecycle (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL COMMENT '用户ID',
                        ec_id INT DEFAULT 1 COMMENT '企业ID',
                        project_id INT DEFAULT 1 COMMENT '项目ID',
                        current_stage VARCHAR(20) DEFAULT 'new_user' COMMENT '当前阶段',
                        stage_updated_at DATETIME COMMENT '阶段更新时间',
                        last_action_at DATETIME COMMENT '最后活动时间',
                        action_count INT DEFAULT 0 COMMENT '行为次数',
                        health_score INT DEFAULT 100 COMMENT '健康度评分 0-100',
                        risk_level VARCHAR(20) DEFAULT 'none' COMMENT '风险等级',
                        tags TEXT COMMENT '用户标签 JSON',
                        next_action_at DATETIME COMMENT '下次触达时间',
                        action_history TEXT COMMENT '触达历史 JSON',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_user (user_id),
                        INDEX idx_stage (current_stage),
                        INDEX idx_ec_project (ec_id, project_id),
                        INDEX idx_last_action (last_action_at),
                        INDEX idx_health_score (health_score)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '会员生命周期表';
                """)
                logger.info("[MemberLifecycle] 创建 business_member_lifecycle 表成功")

            # 检查触达策略表是否存在
            result = db.get_one("SHOW TABLES LIKE 'business_lifecycle_strategies'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_lifecycle_strategies (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        strategy_code VARCHAR(50) NOT NULL COMMENT '策略代码',
                        strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
                        stage VARCHAR(20) NOT NULL COMMENT '适用阶段',
                        trigger_condition VARCHAR(200) COMMENT '触发条件',
                        action_type VARCHAR(20) NOT NULL COMMENT '动作类型: notification/sms/coupon/points',
                        action_config TEXT COMMENT '动作配置 JSON',
                        priority INT DEFAULT 100 COMMENT '优先级 1-100',
                        status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/paused',
                        ec_id INT COMMENT '企业ID（NULL表示通用）',
                        project_id INT COMMENT '项目ID（NULL表示通用）',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_strategy_code (strategy_code),
                        INDEX idx_stage (stage),
                        INDEX idx_status (status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '触达策略表';
                """)
                logger.info("[MemberLifecycle] 创建 business_lifecycle_strategies 表成功")

                # 插入默认策略
                self._insert_default_strategies()

        except Exception as e:
            logger.error(f"[MemberLifecycle] 初始化表失败: {e}")

    def _insert_default_strategies(self):
        """插入默认触达策略"""
        default_strategies = [
            # 新用户策略
            {
                'strategy_code': 'new_user_welcome',
                'strategy_name': '新用户欢迎礼包',
                'stage': self.STAGE_NEW_USER,
                'action_type': 'notification',
                'action_config': '{"title": "欢迎加入", "content": "恭喜您成为会员，新人专属福利等你来领！", "coupon": true, "points": 50}'
            },
            {
                'strategy_code': 'new_user_guide',
                'strategy_name': '新用户引导',
                'stage': self.STAGE_NEW_USER,
                'trigger_condition': 'action_count < 3',
                'action_type': 'notification',
                'action_config': '{"title": "新手引导", "content": "完善个人资料，解锁更多会员权益！"}'
            },
            # 活跃用户策略
            {
                'strategy_code': 'active_birthday',
                'strategy_name': '生日祝福',
                'stage': self.STAGE_ACTIVE,
                'trigger_condition': 'is_birthday = true',
                'action_type': 'coupon',
                'action_config': '{"coupon_type": "birthday", "discount": 10, "amount": 100}'
            },
            {
                'strategy_code': 'active_points_remind',
                'strategy_name': '积分到期提醒',
                'stage': self.STAGE_ACTIVE,
                'trigger_condition': 'points_expiring_days <= 30',
                'action_type': 'notification',
                'action_config': '{"title": "积分即将过期", "content": "您有 {points} 积分即将过期，请尽快使用！"}'
            },
            # 高价值用户策略
            {
                'strategy_code': 'hot_vip_exclusive',
                'strategy_name': 'VIP专属优惠',
                'stage': self.STAGE_HOT,
                'action_type': 'coupon',
                'action_config': '{"coupon_type": "vip", "discount": 20, "amount": 200, "threshold": 500}'
            },
            {
                'strategy_code': 'hot_early_access',
                'strategy_name': '新品优先购',
                'stage': self.STAGE_HOT,
                'action_type': 'notification',
                'action_config': '{"title": "新品预售", "content": "尊敬的高价值会员，您已获得新品优先购买资格！"}'
            },
            # 沉睡唤醒策略
            {
                'strategy_code': 'sleep_awaken_v1',
                'strategy_name': '沉睡唤醒-小额券',
                'stage': self.STAGE_SLEEPING,
                'action_type': 'coupon',
                'action_config': '{"coupon_type": "awaken", "discount": 5, "amount": 50, "threshold": 100}'
            },
            {
                'strategy_code': 'sleep_awaken_v2',
                'strategy_name': '沉睡唤醒-积分奖励',
                'stage': self.STAGE_SLEEPING,
                'trigger_condition': 'action_count > 0',
                'action_type': 'points',
                'action_config': '{"points": 20, "condition": "return_activity"}'
            },
            # 流失预警策略
            {
                'strategy_code': 'churning_recover_v1',
                'strategy_name': '流失召回-大额券',
                'stage': self.STAGE_CHURNING,
                'action_type': 'coupon',
                'action_config': '{"coupon_type": "winback", "discount": 20, "amount": 100, "threshold": 200}'
            },
            {
                'strategy_code': 'churning_recover_v2',
                'strategy_name': '流失召回-限时活动',
                'stage': self.STAGE_CHURNING,
                'action_type': 'notification',
                'action_config': '{"title": "专属召回", "content": "我们想念您！回来看看，专属折扣等着您。"}'
            },
            # 已流失策略
            {
                'strategy_code': 'churned_winback',
                'strategy_name': '流失挽回-超级礼包',
                'stage': self.STAGE_CHURNED,
                'action_type': 'coupon',
                'action_config': '{"coupon_type": "winback", "discount": 30, "amount": 200, "threshold": 300}'
            },
        ]

        for strategy in default_strategies:
            try:
                db.execute("""
                    INSERT INTO business_lifecycle_strategies
                    (strategy_code, strategy_name, stage, trigger_condition, action_type, action_config, priority)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [
                    strategy['strategy_code'],
                    strategy['strategy_name'],
                    strategy['stage'],
                    strategy.get('trigger_condition'),
                    strategy['action_type'],
                    strategy['action_config'],
                    100
                ])
            except Exception as e:
                logger.warning(f"[MemberLifecycle] 插入默认策略失败: {strategy['strategy_code']}, {e}")

    # ============ 生命周期管理核心方法 ============

    def get_member_stage(self, user_id: int) -> Dict[str, Any]:
        """
        获取会员当前生命周期阶段

        Args:
            user_id: 用户ID

        Returns:
            dict: 包含阶段信息、健康度、风险等级等
        """
        lifecycle = db.get_one("""
            SELECT * FROM business_member_lifecycle WHERE user_id=%s
        """, [user_id])

        if not lifecycle:
            # 获取会员基础信息
            member = db.get_one("SELECT * FROM business_members WHERE user_id=%s", [user_id])
            if not member:
                return {'success': False, 'msg': '用户不存在'}

            # 创建生命周期记录
            created_at = member.get('created_at')
            days_since_joined = (datetime.now() - created_at).days if created_at else 0

            stage = self.STAGE_NEW_USER if days_since_joined <= 7 else self.STAGE_ACTIVE

            db.execute("""
                INSERT INTO business_member_lifecycle
                (user_id, ec_id, project_id, current_stage, stage_updated_at, last_action_at, action_count)
                VALUES (%s, %s, %s, %s, NOW(), %s, 1)
            """, [user_id, member.get('ec_id', 1), member.get('project_id', 1), stage, created_at])

            lifecycle = db.get_one("SELECT * FROM business_member_lifecycle WHERE user_id=%s", [user_id])

        stage_code = lifecycle.get('current_stage', self.STAGE_NEW_USER)
        stage_config = self.STAGE_CONFIG.get(stage_code, self.STAGE_CONFIG[self.STAGE_NEW_USER])

        return {
            'success': True,
            'user_id': user_id,
            'current_stage': stage_code,
            'stage_name': stage_config['name'],
            'stage_color': stage_config['color'],
            'stage_updated_at': lifecycle.get('stage_updated_at'),
            'last_action_at': lifecycle.get('last_action_at'),
            'action_count': lifecycle.get('action_count', 0),
            'health_score': lifecycle.get('health_score', 100),
            'risk_level': lifecycle.get('risk_level', 'none'),
            'next_action_at': lifecycle.get('next_action_at'),
            'tags': self._parse_tags(lifecycle.get('tags'))
        }

    def update_member_action(self, user_id: int, action_type: str = 'general',
                            ec_id: int = 1, project_id: int = 1) -> Dict[str, Any]:
        """
        更新会员行为记录

        Args:
            user_id: 用户ID
            action_type: 行为类型
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 更新结果
        """
        try:
            lifecycle = db.get_one("""
                SELECT * FROM business_member_lifecycle WHERE user_id=%s
            """, [user_id])

            if not lifecycle:
                # 创建新记录
                member = db.get_one("SELECT * FROM business_members WHERE user_id=%s", [user_id])
                if not member:
                    return {'success': False, 'msg': '用户不存在'}

                db.execute("""
                    INSERT INTO business_member_lifecycle
                    (user_id, ec_id, project_id, current_stage, stage_updated_at,
                     last_action_at, action_count, health_score)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), 1, 100)
                """, [user_id, ec_id, project_id, self.STAGE_NEW_USER])
            else:
                # 更新现有记录
                now = datetime.now()
                action_count = (lifecycle.get('action_count') or 0) + 1

                # 计算新的健康度评分
                health_score = self._calculate_health_score(user_id, action_count)

                # 判断是否需要阶段升级
                new_stage = self._determine_stage(user_id, lifecycle.get('current_stage'))

                update_fields = "last_action_at=NOW(), action_count=%s, health_score=%s"
                params = [action_count, health_score]

                if new_stage != lifecycle.get('current_stage'):
                    update_fields += ", current_stage=%s, stage_updated_at=NOW()"
                    params.append(new_stage)

                db.execute(f"""
                    UPDATE business_member_lifecycle
                    SET {update_fields}
                    WHERE user_id=%s
                """, params + [user_id])

                logger.info(f"[MemberLifecycle] 更新会员行为: user_id={user_id}, action_count={action_count}, new_stage={new_stage}")

            return {'success': True, 'msg': '更新成功'}

        except Exception as e:
            logger.error(f"[MemberLifecycle] 更新会员行为失败: {e}")
            return {'success': False, 'msg': str(e)}

    def _calculate_health_score(self, user_id: int, action_count: int) -> int:
        """计算会员健康度评分"""
        try:
            # 基础分 100
            score = 100

            # 获取会员信息
            member = db.get_one("""
                SELECT m.*,
                       (SELECT COUNT(*) FROM business_orders WHERE user_id=m.user_id AND pay_status='paid' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as monthly_orders,
                       (SELECT SUM(actual_amount) FROM business_orders WHERE user_id=m.user_id AND pay_status='paid' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as monthly_amount,
                       (SELECT COUNT(*) FROM business_points_log WHERE user_id=m.user_id AND change_type='checkin' AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)) as weekly_checkins
                FROM business_members m WHERE m.user_id=%s
            """, [user_id])

            if not member:
                return 50

            # 订单频率扣分（太少扣分）
            monthly_orders = member.get('monthly_orders') or 0
            if monthly_orders == 0:
                score -= 30
            elif monthly_orders < 2:
                score -= 15

            # 消费金额扣分（太少扣分）
            monthly_amount = float(member.get('monthly_amount') or 0)
            if monthly_amount < 50:
                score -= 20
            elif monthly_amount < 100:
                score -= 10

            # 签到活跃度加分
            weekly_checkins = member.get('weekly_checkins') or 0
            if weekly_checkins >= 5:
                score += 10
            elif weekly_checkins >= 3:
                score += 5

            # 会员等级加分
            level = member.get('member_level', 1)
            if level >= 5:
                score += 10
            elif level >= 3:
                score += 5

            return max(0, min(100, score))

        except Exception as e:
            logger.warning(f"[MemberLifecycle] 计算健康度失败: {e}")
            return 50

    def _determine_stage(self, user_id: int, current_stage: str) -> str:
        """根据行为判断会员应该处于哪个阶段"""
        try:
            member = db.get_one("""
                SELECT m.*,
                       lc.last_action_at,
                       (SELECT COUNT(*) FROM business_orders WHERE user_id=m.user_id AND pay_status='paid' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as monthly_orders
                FROM business_members m
                LEFT JOIN business_member_lifecycle lc ON lc.user_id = m.user_id
                WHERE m.user_id=%s
            """, [user_id])

            if not member:
                return current_stage

            now = datetime.now()
            last_action = member.get('last_action_at') or member.get('created_at')
            if isinstance(last_action, str):
                last_action = datetime.strptime(last_action, '%Y-%m-%d %H:%M:%S')

            days_inactive = (now - last_action).days
            created_at = member.get('created_at')
            days_since_joined = (now - created_at).days if created_at else 0
            monthly_orders = member.get('monthly_orders') or 0

            # 判断阶段
            if days_since_joined <= 7:
                return self.STAGE_NEW_USER

            if days_inactive > 180:
                return self.STAGE_CHURNED
            elif days_inactive > 90:
                return self.STAGE_CHURNING
            elif days_inactive > 30:
                return self.STAGE_SLEEPING

            # 活跃用户
            if monthly_orders >= 3:
                return self.STAGE_HOT
            return self.STAGE_ACTIVE

        except Exception as e:
            logger.warning(f"[MemberLifecycle] 判断阶段失败: {e}")
            return current_stage

    def _parse_tags(self, tags_str: str) -> List[str]:
        """解析用户标签"""
        if not tags_str:
            return []
        try:
            import json
            return json.loads(tags_str) if isinstance(tags_str, str) else tags_str
        except:
            return []

    # ============ 触达策略执行 ============

    def execute_strategy(self, user_id: int, strategy_code: str) -> Dict[str, Any]:
        """
        执行指定的触达策略

        Args:
            user_id: 用户ID
            strategy_code: 策略代码

        Returns:
            dict: 执行结果
        """
        try:
            strategy = db.get_one("""
                SELECT * FROM business_lifecycle_strategies
                WHERE strategy_code=%s AND status='active'
            """, [strategy_code])

            if not strategy:
                return {'success': False, 'msg': '策略不存在或已停用'}

            member = db.get_one("SELECT * FROM business_members WHERE user_id=%s", [user_id])
            if not member:
                return {'success': False, 'msg': '用户不存在'}

            action_type = strategy.get('action_type')
            action_config_str = strategy.get('action_config', '{}')

            try:
                import json
                action_config = json.loads(action_config_str) if isinstance(action_config_str, str) else action_config_str
            except:
                action_config = {}

            result = {'success': True, 'action_type': action_type}

            # 执行不同类型的触达动作
            if action_type == 'notification':
                title = action_config.get('title', '温馨提示')
                content = action_config.get('content', '')

                # 替换变量
                content = content.format(
                    points=member.get('points', 0),
                    nickname=member.get('nickname', '会员'),
                    level=member.get('member_grade', '')
                )

                send_notification(
                    user_id=user_id,
                    title=title,
                    content=content,
                    notify_type='system',
                    ec_id=member.get('ec_id'),
                    project_id=member.get('project_id')
                )
                result['msg'] = '站内信已发送'

            elif action_type == 'coupon':
                # 发放优惠券：调用真实发券逻辑
                coupon_type = action_config.get('coupon_type', 'discount')
                discount_value = action_config.get('discount_value', 0)
                min_order_amount = action_config.get('min_order_amount', 0)
                valid_days = action_config.get('valid_days', 30)
                coupon_name = action_config.get('coupon_name', '专属优惠券')
                ec_id = member.get('ec_id')
                project_id = member.get('project_id')
                try:
                    # 创建并发放优惠券
                    coupon_id = db.execute("""
                        INSERT INTO business_coupons
                        (ec_id, project_id, name, coupon_type, discount_value,
                         min_order_amount, total_count, issued_count, per_limit,
                         start_time, end_time, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, 1, 0, 1,
                                NOW(), DATE_ADD(NOW(), INTERVAL %s DAY),
                                'active', NOW())
                    """, [ec_id, project_id, coupon_name, coupon_type,
                          discount_value, min_order_amount, valid_days])
                    if coupon_id:
                        db.execute("""
                            INSERT INTO business_user_coupons
                            (ec_id, project_id, user_id, coupon_id, status, obtained_at, expired_at)
                            VALUES (%s, %s, %s, %s, 'unused', NOW(), DATE_ADD(NOW(), INTERVAL %s DAY))
                        """, [ec_id, project_id, user_id, coupon_id, valid_days])
                        result['msg'] = f'优惠券已发放: {coupon_name}'
                        result['coupon_id'] = coupon_id
                    else:
                        result['success'] = False
                        result['msg'] = '优惠券创建失败'
                except Exception as ce:
                    logger.error(f"[MemberLifecycle] 发放优惠券失败: {ce}")
                    result['success'] = False
                    result['msg'] = f'发放优惠券失败: {ce}'

            elif action_type == 'points':
                # 发放积分：调用真实积分增加逻辑
                points = int(action_config.get('points', 10))
                reason = action_config.get('reason', '会员关怀积分')
                ec_id = member.get('ec_id')
                project_id = member.get('project_id')
                try:
                    db.execute("""
                        UPDATE business_members
                        SET points = points + %s, updated_at = NOW()
                        WHERE user_id = %s
                    """, [points, user_id])
                    db.execute("""
                        INSERT INTO business_points_log
                        (ec_id, project_id, user_id, points, log_type, description, created_at)
                        VALUES (%s, %s, %s, %s, 'earn', %s, NOW())
                    """, [ec_id, project_id, user_id, points, reason])
                    result['msg'] = f'积分已发放: +{points}'
                    result['points'] = points
                except Exception as pe:
                    logger.error(f"[MemberLifecycle] 发放积分失败: {pe}")
                    result['success'] = False
                    result['msg'] = f'发放积分失败: {pe}'

            # 更新触达历史
            self._record_action_history(user_id, strategy_code, action_type, result)

            logger.info(f"[MemberLifecycle] 执行策略: user_id={user_id}, strategy={strategy_code}, result={result}")

            return result

        except Exception as e:
            logger.error(f"[MemberLifecycle] 执行策略失败: {e}")
            return {'success': False, 'msg': str(e)}

    def _record_action_history(self, user_id: int, strategy_code: str,
                               action_type: str, result: Dict):
        """记录触达历史"""
        try:
            import json
            history_entry = {
                'strategy_code': strategy_code,
                'action_type': action_type,
                'result': result.get('msg', ''),
                'executed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            lifecycle = db.get_one("""
                SELECT action_history FROM business_member_lifecycle WHERE user_id=%s
            """, [user_id])

            if lifecycle and lifecycle.get('action_history'):
                try:
                    history = json.loads(lifecycle['action_history'])
                    if not isinstance(history, list):
                        history = []
                except:
                    history = []
            else:
                history = []

            history.append(history_entry)
            # 保留最近50条记录
            history = history[-50:]

            db.execute("""
                UPDATE business_member_lifecycle
                SET action_history=%s, updated_at=NOW()
                WHERE user_id=%s
            """, [json.dumps(history), user_id])

        except Exception as e:
            logger.warning(f"[MemberLifecycle] 记录触达历史失败: {e}")

    # ============ 批量处理调度 ============

    def run_lifecycle_check(self, ec_id: int = None, project_id: int = None) -> Dict[str, Any]:
        """
        执行生命周期检查和阶段更新

        Args:
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 执行统计结果
        """
        try:
            stats = {
                'total_checked': 0,
                'stage_updated': 0,
                'strategies_executed': 0,
                'errors': 0
            }

            # 查询所有活跃会员的生命周期记录
            where = "m.deleted=0"
            params = []

            if ec_id:
                where += " AND m.ec_id=%s"
                params.append(ec_id)
            if project_id:
                where += " AND m.project_id=%s"
                params.append(project_id)

            members = db.get_all(f"""
                SELECT m.user_id, lc.current_stage, lc.action_count
                FROM business_members m
                LEFT JOIN business_member_lifecycle lc ON lc.user_id = m.user_id
                WHERE {where}
                LIMIT {self.BATCH_SIZE}
            """, params) or []

            stats['total_checked'] = len(members)

            for member in members:
                try:
                    user_id = member['user_id']
                    current_stage = member.get('current_stage') or self.STAGE_NEW_USER
                    new_stage = self._determine_stage(user_id, current_stage)

                    if new_stage != current_stage:
                        db.execute("""
                            UPDATE business_member_lifecycle
                            SET current_stage=%s, stage_updated_at=NOW(), updated_at=NOW()
                            WHERE user_id=%s
                        """, [new_stage, user_id])
                        stats['stage_updated'] += 1

                        # 阶段变更时执行对应策略
                        strategies = db.get_all("""
                            SELECT strategy_code FROM business_lifecycle_strategies
                            WHERE stage=%s AND status='active'
                            ORDER BY priority ASC
                            LIMIT 3
                        """, [new_stage]) or []

                        for strategy in strategies:
                            self.execute_strategy(user_id, strategy['strategy_code'])
                            stats['strategies_executed'] += 1

                except Exception as e:
                    logger.warning(f"[MemberLifecycle] 处理会员失败: {member.get('user_id')}, {e}")
                    stats['errors'] += 1

            logger.info(f"[MemberLifecycle] 生命周期检查完成: {stats}")
            return {'success': True, 'stats': stats}

        except Exception as e:
            logger.error(f"[MemberLifecycle] 生命周期检查失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_lifecycle_stats(self, ec_id: int = None, project_id: int = None) -> Dict[str, Any]:
        """
        获取会员生命周期统计

        Args:
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 统计结果
        """
        try:
            where = "deleted=0"
            params = []

            if ec_id:
                where += " AND ec_id=%s"
                params.append(ec_id)
            if project_id:
                where += " AND project_id=%s"
                params.append(project_id)

            # 各阶段会员数量
            stage_stats = db.get_all(f"""
                SELECT current_stage, COUNT(*) as count
                FROM business_member_lifecycle
                WHERE {where}
                GROUP BY current_stage
            """, params) or []

            stage_map = {}
            for stat in stage_stats:
                stage_map[stat['current_stage']] = stat['count']

            # 健康度分布
            health_distribution = db.get_all(f"""
                SELECT
                    CASE
                        WHEN health_score >= 80 THEN 'excellent'
                        WHEN health_score >= 60 THEN 'good'
                        WHEN health_score >= 40 THEN 'fair'
                        WHEN health_score >= 20 THEN 'poor'
                        ELSE 'critical'
                    END as health_level,
                    COUNT(*) as count
                FROM business_member_lifecycle
                WHERE {where}
                GROUP BY health_level
            """, params) or []

            health_map = {}
            for stat in health_distribution:
                health_map[stat['health_level']] = stat['count']

            return {
                'success': True,
                'stage_distribution': [
                    {
                        'stage': stage,
                        'stage_name': self.STAGE_CONFIG.get(stage, {}).get('name', stage),
                        'stage_color': self.STAGE_CONFIG.get(stage, {}).get('color', '#999'),
                        'count': stage_map.get(stage, 0)
                    }
                    for stage in [self.STAGE_NEW_USER, self.STAGE_ACTIVE, self.STAGE_HOT,
                                 self.STAGE_SLEEPING, self.STAGE_CHURNING, self.STAGE_CHURNED]
                ],
                'health_distribution': {
                    'excellent': health_map.get('excellent', 0),  # 80+
                    'good': health_map.get('good', 0),            # 60-79
                    'fair': health_map.get('fair', 0),            # 40-59
                    'poor': health_map.get('poor', 0),            # 20-39
                    'critical': health_map.get('critical', 0),    # 0-19
                },
                'total_members': sum(stage_map.values())
            }

        except Exception as e:
            logger.error(f"[MemberLifecycle] 获取统计失败: {e}")
            return {'success': False, 'msg': str(e)}


# 单例实例
member_lifecycle_service = MemberLifecycleService()
