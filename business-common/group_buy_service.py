#!/usr/bin/env python3
"""
拼团活动服务 V24.0
提供拼团活动创建、参与、订单管理功能
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from . import db

logger = logging.getLogger(__name__)


class GroupBuyService:
    """拼团服务 - 社交电商能力"""

    # 拼团状态
    STATUS = {
        'pending': '待开始',
        'ongoing': '拼团中',
        'success': '拼团成功',
        'failed': '拼团失败',
        'cancelled': '已取消',
    }

    # 拼团订单状态
    ORDER_STATUS = {
        'pending': '待支付',
        'paid': '已支付',
        'refunded': '已退款',
        'cancelled': '已取消',
    }

    @staticmethod
    def create_activity(name, product_id, product_name, product_image,
                       original_price, group_price, min_people, max_people,
                       valid_hours=24, ec_id=None, project_id=None, created_by=None):
        """
        创建拼团活动

        Args:
            name: 活动名称
            product_id: 商品ID
            product_name: 商品名称
            product_image: 商品图片
            original_price: 原价
            group_price: 拼团价
            min_people: 最小成团人数
            max_people: 最大参与人数
            valid_hours: 拼团有效时长(小时)
            ec_id: 企业ID
            project_id: 项目ID
            created_by: 创建人

        Returns:
            dict: 创建结果
        """
        activity_no = f"GROUP{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

        try:
            db.execute(
                """INSERT INTO business_group_activities
                   (activity_no, name, product_id, product_name, product_image,
                    original_price, group_price, min_people, max_people, valid_hours,
                    status, ec_id, project_id, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s)""",
                [activity_no, name, product_id, product_name, product_image,
                 original_price, group_price, min_people, max_people, valid_hours,
                 ec_id, project_id, created_by]
            )

            logger.info(f"拼团活动创建成功: {activity_no}, product={product_name}")
            return {'success': True, 'data': {'activity_no': activity_no}}

        except Exception as e:
            logger.error(f"创建拼团活动失败: {e}")
            return {'success': False, 'msg': '创建失败'}

    @staticmethod
    def get_activities(ec_id=None, project_id=None, status=None, page=1, page_size=20):
        """
        获取拼团活动列表

        Args:
            ec_id: 企业ID
            project_id: 项目ID
            status: 状态筛选
            page: 页码
            page_size: 每页数量

        Returns:
            dict: 活动列表
        """
        where_clauses = ["deleted=0"]
        params = []

        if ec_id:
            where_clauses.append("ec_id=%s")
            params.append(ec_id)
        if project_id:
            where_clauses.append("project_id=%s")
            params.append(project_id)
        if status:
            where_clauses.append("status=%s")
            params.append(status)

        where = " AND ".join(where_clauses)

        # 查询总数
        total = db.get_one(f"SELECT COUNT(*) as cnt FROM business_group_activities WHERE {where}", params)
        total_count = total['cnt'] if total else 0

        # 分页查询
        offset = (page - 1) * page_size
        activities = db.get_all(
            f"""SELECT * FROM business_group_activities
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s""",
            params + [page_size, offset]
        )

        return {
            'success': True,
            'data': {
                'items': activities or [],
                'total': total_count,
                'page': page,
                'page_size': page_size,
            }
        }

    @staticmethod
    def get_activity_detail(activity_no, ec_id=None, project_id=None):
        """获取拼团活动详情"""
        activity = db.get_one(
            """SELECT * FROM business_group_activities
               WHERE activity_no=%s AND deleted=0""",
            [activity_no]
        )

        if not activity:
            return {'success': False, 'msg': '活动不存在'}

        # 获取当前参与人数
        current_count = db.get_one(
            """SELECT COUNT(*) as cnt FROM business_group_orders
               WHERE activity_no=%s AND status IN ('paid')""",
            [activity_no]
        )
        activity['current_people'] = current_count['cnt'] if current_count else 0

        return {'success': True, 'data': activity}

    @staticmethod
    def join_group(activity_no, user_id, user_name, user_phone,
                   address_id=None, ec_id=None, project_id=None):
        """
        参与拼团

        Args:
            activity_no: 活动编号
            user_id: 用户ID
            user_name: 用户姓名
            user_phone: 用户电话
            address_id: 地址ID
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 参与结果，包含订单信息
        """
        # 获取活动详情
        activity = db.get_one(
            """SELECT * FROM business_group_activities
               WHERE activity_no=%s AND status='ongoing' AND deleted=0""",
            [activity_no]
        )

        if not activity:
            return {'success': False, 'msg': '拼团活动不存在或未开始'}

        # 检查是否已参与
        existing = db.get_one(
            """SELECT id FROM business_group_orders
               WHERE activity_no=%s AND user_id=%s AND status IN ('paid', 'pending')""",
            [activity_no, user_id]
        )

        if existing:
            return {'success': False, 'msg': '您已参与此拼团'}

        # 检查是否已满团
        if activity['current_people'] >= activity['max_people']:
            return {'success': False, 'msg': '拼团人数已满'}

        # 创建拼团订单
        order_no = f"GO{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

        # 获取用户地址
        address_info = ''
        if address_id:
            addr = db.get_one(
                "SELECT * FROM business_user_addresses WHERE id=%s AND user_id=%s",
                [address_id, user_id]
            )
            if addr:
                address_info = json.dumps({
                    'name': addr.get('contact_name'),
                    'phone': addr.get('contact_phone'),
                    'address': addr.get('address'),
                }, ensure_ascii=False)

        try:
            db.execute(
                """INSERT INTO business_group_orders
                   (order_no, activity_no, activity_name, product_id, product_name, product_image,
                    group_price, user_id, user_name, user_phone, address_info,
                    status, ec_id, project_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)""",
                [order_no, activity_no, activity['name'], activity['product_id'],
                 activity['product_name'], activity['product_image'], activity['group_price'],
                 user_id, user_name, user_phone, address_info, ec_id, project_id]
            )

            # 更新活动当前人数
            db.execute(
                """UPDATE business_group_activities
                   SET current_people = current_people + 1
                   WHERE activity_no=%s""",
                [activity_no]
            )

            logger.info(f"用户参与拼团: user_id={user_id}, activity={activity_no}, order={order_no}")

            return {
                'success': True,
                'data': {
                    'order_no': order_no,
                    'activity_no': activity_no,
                    'group_price': activity['group_price'],
                    'valid_hours': activity['valid_hours'],
                }
            }

        except Exception as e:
            logger.error(f"参与拼团失败: {e}")
            return {'success': False, 'msg': '参与失败'}

    @staticmethod
    def get_my_groups(user_id, ec_id=None, project_id=None):
        """获取我的拼团订单"""
        orders = db.get_all(
            """SELECT o.*, a.product_image, a.group_price, a.min_people, a.current_people, a.valid_hours
               FROM business_group_orders o
               LEFT JOIN business_group_activities a ON o.activity_no = a.activity_no
               WHERE o.user_id=%s AND o.deleted=0
               ORDER BY o.created_at DESC""",
            [user_id]
        )

        return {'success': True, 'data': orders or []}

    @staticmethod
    def confirm_group_success(activity_no):
        """确认拼团成功（定时任务或支付回调触发）"""
        activity = db.get_one(
            """SELECT * FROM business_group_activities
               WHERE activity_no=%s AND status='ongoing'""",
            [activity_no]
        )

        if not activity:
            return {'success': False, 'msg': '活动不存在'}

        # 统计成团人数
        count_result = db.get_one(
            """SELECT COUNT(*) as cnt FROM business_group_orders
               WHERE activity_no=%s AND status='paid'""",
            [activity_no]
        )
        current_count = count_result['cnt'] if count_result else 0

        if current_count >= activity['min_people']:
            # 成团成功
            db.execute(
                """UPDATE business_group_activities SET status='success'
                   WHERE activity_no=%s""",
                [activity_no]
            )

            # 通知所有参与用户
            logger.info(f"拼团成功: {activity_no}, 成团人数={current_count}")
            return {'success': True, 'msg': '成团成功', 'is_success': True}
        else:
            # 成团失败
            db.execute(
                """UPDATE business_group_activities SET status='failed'
                   WHERE activity_no=%s""",
                [activity_no]
            )

            # 自动退款
            failed_orders = db.get_all(
                """SELECT * FROM business_group_orders
                   WHERE activity_no=%s AND status='paid'""",
                [activity_no]
            )

            for order in (failed_orders or []):
                # 记录退款
                db.execute(
                    """UPDATE business_group_orders SET status='refunded'
                       WHERE id=%s""",
                    [order['id']]
                )
                # TODO: 实际退款到原支付渠道

            logger.info(f"拼团失败: {activity_no}, 成团人数={current_count}, 已自动退款")
            return {'success': True, 'msg': '成团失败，已退款', 'is_success': False}

    @staticmethod
    def check_and_expire_groups():
        """检查并处理过期拼团（定时任务）"""
        expired_activities = db.get_all(
            """SELECT * FROM business_group_activities
               WHERE status='ongoing'
               AND DATE_ADD(created_at, INTERVAL valid_hours HOUR) < NOW()"""
        )

        for activity in (expired_activities or []):
            result = GroupBuyService.confirm_group_success(activity['activity_no'])
            logger.info(f"拼团过期处理: {activity['activity_no']}, result={result.get('is_success')}")

        return len(expired_activities or [])


# 便捷实例
group_buy = GroupBuyService()