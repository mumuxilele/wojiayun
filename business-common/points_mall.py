"""
积分商城服务模块 V23.0
功能:
  - 积分商品管理（管理员上架/下架）
  - 积分兑换商品（用户用积分兑换实物/虚拟商品）
  - 兑换订单管理（发货/确认收货/退款）
  - 兑换记录查询
"""
import json
import logging
import time
from datetime import datetime
from . import db

logger = logging.getLogger(__name__)


class PointsMallService:
    """积分商城服务"""

    @staticmethod
    def get_products(ec_id=None, project_id=None, page=1, page_size=20, category=None, status='active'):
        """
        获取积分商品列表

        Args:
            ec_id: 企业ID
            project_id: 项目ID
            page: 页码
            page_size: 每页数量
            category: 商品分类
            status: 商品状态 (active/sold_out/off_shelf)

        Returns:
            商品列表 + 分页信息
        """
        where = "deleted=0"
        params = []

        if status == 'active':
            where += " AND status='active' AND stock > 0"
        elif status:
            where += " AND status=%s"
            params.append(status)

        if ec_id:
            where += " AND (ec_id=%s OR ec_id IS NULL)"
            params.append(ec_id)
        if project_id:
            where += " AND (project_id=%s OR project_id IS NULL)"
            params.append(project_id)
        if category:
            where += " AND category=%s"
            params.append(category)

        total = db.get_total(f"SELECT COUNT(*) FROM business_points_goods WHERE {where}", params)
        offset = (page - 1) * page_size
        items = db.get_all(
            f"""SELECT id, goods_name, goods_image, category, points_price, original_price,
                       stock, total_stock, sold_count, description, status,
                       sort_order, created_at
                FROM business_points_goods WHERE {where}
                ORDER BY sort_order ASC, sold_count DESC
                LIMIT %s OFFSET %s""",
            params + [page_size, offset]
        )

        return {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }

    @staticmethod
    def get_product_detail(goods_id):
        """获取积分商品详情"""
        goods = db.get_one(
            "SELECT * FROM business_points_goods WHERE id=%s AND deleted=0",
            [goods_id]
        )
        if not goods:
            return None

        # 兑换记录数量
        try:
            exchange_count = db.get_total(
                "SELECT COUNT(*) FROM business_points_exchanges WHERE goods_id=%s AND status IN ('paid','shipped','completed')",
                [goods_id]
            )
            goods['exchange_count'] = exchange_count
        except Exception:
            goods['exchange_count'] = goods.get('sold_count', 0)

        return goods

    @staticmethod
    def exchange_goods(user_id, user_name, goods_id, quantity=1,
                       address_snapshot='', phone='', ec_id=None, project_id=None):
        """
        积分兑换商品

        Args:
            user_id: 用户ID
            user_name: 用户名
            goods_id: 商品ID
            quantity: 兑换数量
            address_snapshot: 收货地址快照
            phone: 联系电话
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 兑换结果
        """
        # 1. 查询商品信息
        goods = db.get_one(
            "SELECT * FROM business_points_goods WHERE id=%s AND status='active' AND deleted=0",
            [goods_id]
        )
        if not goods:
            return {'success': False, 'msg': '商品不存在或已下架'}

        if (goods.get('stock') or 0) < quantity:
            return {'success': False, 'msg': f'库存不足（当前库存 {goods.get("stock", 0)}）'}

        # 检查每人限兑数量
        per_limit = int(goods.get('per_limit') or 0)
        if per_limit > 0:
            user_exchange_count = db.get_total(
                "SELECT COALESCE(SUM(quantity),0) FROM business_points_exchanges "
                "WHERE user_id=%s AND goods_id=%s AND status IN ('paid','shipped','completed')",
                [user_id, goods_id]
            )
            if user_exchange_count + quantity > per_limit:
                return {'success': False, 'msg': f'每人限兑{per_limit}件，您已兑{user_exchange_count}件'}

        # 2. 计算所需积分
        points_price = int(goods.get('points_price') or 0)
        total_points = points_price * quantity

        # 3. 检查用户积分余额
        member = db.get_one(
            "SELECT points FROM business_members WHERE user_id=%s",
            [user_id]
        )
        if not member:
            return {'success': False, 'msg': '请先注册会员'}

        if (member.get('points') or 0) < total_points:
            return {'success': False, 'msg': f'积分不足，需要{total_points}积分，当前{member.get("points", 0)}积分'}

        # 4. 执行兑换（事务）
        exchange_no = f"EX{datetime.now().strftime('%Y%m%d%H%M%S')}{str(user_id)[-4:]}"
        conn = db.get_db()
        try:
            cursor = conn.cursor()
            conn.begin()

            # 扣减积分
            cursor.execute(
                "UPDATE business_members SET points=points-%s WHERE user_id=%s AND points>=%s",
                [total_points, user_id, total_points]
            )
            if cursor.rowcount == 0:
                conn.rollback()
                return {'success': False, 'msg': '积分扣减失败，请重试'}

            # 扣减库存
            cursor.execute(
                "UPDATE business_points_goods SET stock=stock-%s, sold_count=sold_count+%s "
                "WHERE id=%s AND stock>=%s",
                [quantity, quantity, goods_id, quantity]
            )
            if cursor.rowcount == 0:
                conn.rollback()
                return {'success': False, 'msg': '库存扣减失败，请重试'}

            # 创建兑换订单
            cursor.execute(
                """INSERT INTO business_points_exchanges
                   (exchange_no, user_id, user_name, goods_id, goods_name, goods_image,
                    points_price, quantity, total_points, address_snapshot, phone,
                    status, ec_id, project_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'paid',%s,%s)""",
                [exchange_no, user_id, user_name, goods_id, goods.get('goods_name', ''),
                 goods.get('goods_image', ''), points_price, quantity, total_points,
                 address_snapshot, phone, ec_id, project_id]
            )
            exchange_id = cursor.lastrowid

            # 记录积分日志
            cursor.execute(
                """INSERT INTO business_points_log
                   (user_id, user_name, log_type, points, balance_after, description, ec_id, project_id)
                   SELECT %s, %s, 'exchange', -%s, points, %s, %s, %s
                   FROM business_members WHERE user_id=%s""",
                [user_id, user_name, total_points,
                 f'积分兑换：{goods.get("goods_name", "")} x{quantity}',
                 ec_id, project_id, user_id]
            )

            conn.commit()

            logger.info(f"积分兑换成功: user={user_id}, goods={goods_id}, points={total_points}")

            # 发送通知
            try:
                from .notification import send_notification
                send_notification(
                    user_id=user_id,
                    title='兑换成功',
                    content=f'您已成功兑换「{goods.get("goods_name", "")}」x{quantity}，消耗{total_points}积分',
                    notify_type='points',
                    ref_id=str(exchange_id),
                    ref_type='exchange',
                    ec_id=ec_id,
                    project_id=project_id
                )
            except Exception as e:
                logger.warning(f"兑换通知发送失败: {e}")

            return {
                'success': True,
                'msg': '兑换成功',
                'data': {
                    'exchange_id': exchange_id,
                    'exchange_no': exchange_no,
                    'total_points': total_points,
                    'goods_name': goods.get('goods_name', '')
                }
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"积分兑换失败: user={user_id}, goods={goods_id}, error={e}")
            return {'success': False, 'msg': '兑换失败，请稍后重试'}
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    @staticmethod
    def get_user_exchanges(user_id, page=1, page_size=20, status=None):
        """获取用户兑换记录"""
        where = "user_id=%s AND deleted=0"
        params = [user_id]
        if status:
            where += " AND status=%s"
            params.append(status)

        total = db.get_total(f"SELECT COUNT(*) FROM business_points_exchanges WHERE {where}", params)
        offset = (page - 1) * page_size
        items = db.get_all(
            f"""SELECT id, exchange_no, goods_name, goods_image, points_price, quantity,
                       total_points, status, address_snapshot, tracking_no, logistics_company,
                       created_at, shipped_at, completed_at
                FROM business_points_exchanges WHERE {where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s""",
            params + [page_size, offset]
        )

        return {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size
        }

    @staticmethod
    def confirm_exchange(user_id, exchange_id):
        """用户确认收货"""
        exchange = db.get_one(
            "SELECT * FROM business_points_exchanges WHERE id=%s AND user_id=%s AND deleted=0",
            [exchange_id, user_id]
        )
        if not exchange:
            return {'success': False, 'msg': '兑换记录不存在'}
        if exchange.get('status') != 'shipped':
            return {'success': False, 'msg': '只有已发货的订单才能确认收货'}

        db.execute(
            "UPDATE business_points_exchanges SET status='completed', completed_at=NOW() WHERE id=%s",
            [exchange_id]
        )
        return {'success': True, 'msg': '已确认收货'}

    @staticmethod
    def get_exchange_stats(ec_id=None, project_id=None):
        """获取积分商城统计（管理端）"""
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)

        stats = db.get_one(f"""
            SELECT
                COUNT(*) as total_exchanges,
                COALESCE(SUM(total_points), 0) as total_points_consumed,
                COUNT(CASE WHEN status='paid' THEN 1 END) as pending_ship,
                COUNT(CASE WHEN status='shipped' THEN 1 END) as shipped,
                COUNT(CASE WHEN status='completed' THEN 1 END) as completed
            FROM business_points_exchanges WHERE {where}
        """, params)

        # 热门兑换商品TOP10
        hot_goods = db.get_all(f"""
            SELECT goods_id, goods_name, goods_image,
                   SUM(quantity) as total_qty, SUM(total_points) as total_points
            FROM business_points_exchanges WHERE {where}
            GROUP BY goods_id ORDER BY total_qty DESC LIMIT 10
        """, params)

        return {
            'stats': stats,
            'hot_goods': hot_goods or []
        }

    @staticmethod
    def create_goods(data, admin_user):
        """管理员创建积分商品"""
        from .utils import generate_no

        goods_name = data.get('goods_name', '').strip()
        if not goods_name:
            return {'success': False, 'msg': '商品名称不能为空'}

        try:
            goods_id = db.execute(
                """INSERT INTO business_points_goods
                   (goods_name, goods_image, category, points_price, original_price,
                    stock, total_stock, description, per_limit, status, sort_order,
                    ec_id, project_id, created_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,%s,%s,%s)""",
                [goods_name, data.get('goods_image', ''), data.get('category', ''),
                 int(data.get('points_price', 0)), float(data.get('original_price', 0) or 0),
                 int(data.get('stock', 0)), int(data.get('stock', 0)),
                 data.get('description', ''), int(data.get('per_limit', 0)),
                 int(data.get('sort_order', 0)),
                 admin_user.get('ec_id'), admin_user.get('project_id'),
                 admin_user.get('user_id')]
            )
            return {'success': True, 'msg': '创建成功', 'data': {'id': goods_id}}
        except Exception as e:
            logger.error(f"创建积分商品失败: {e}")
            return {'success': False, 'msg': '创建失败'}

    @staticmethod
    def update_goods(goods_id, data, admin_user):
        """管理员更新积分商品"""
        updates = []
        params = []
        updatable = {
            'goods_name': 'str', 'goods_image': 'str', 'category': 'str',
            'points_price': 'int', 'original_price': 'float',
            'stock': 'int', 'description': 'str', 'per_limit': 'int',
            'status': 'str', 'sort_order': 'int'
        }
        for field, field_type in updatable.items():
            val = data.get(field)
            if val is not None:
                if field_type == 'int':
                    val = int(val)
                elif field_type == 'float':
                    val = float(val)
                updates.append(f"{field}=%s")
                params.append(val)

        if not updates:
            return {'success': False, 'msg': '没有更新内容'}

        updates.append("updated_at=NOW()")
        params.append(goods_id)
        db.execute(
            f"UPDATE business_points_goods SET {', '.join(updates)} WHERE id=%s",
            params
        )
        return {'success': True, 'msg': '更新成功'}

    @staticmethod
    def ship_exchange(exchange_id, tracking_no, logistics_company, admin_user):
        """管理员发货"""
        exchange = db.get_one(
            "SELECT * FROM business_points_exchanges WHERE id=%s AND status='paid' AND deleted=0",
            [exchange_id]
        )
        if not exchange:
            return {'success': False, 'msg': '兑换记录不存在或状态不正确'}

        db.execute(
            """UPDATE business_points_exchanges
               SET status='shipped', tracking_no=%s, logistics_company=%s,
                   shipped_at=NOW(), shipped_by=%s
               WHERE id=%s""",
            [tracking_no, logistics_company, admin_user.get('user_name', ''), exchange_id]
        )

        # 发送通知给用户
        try:
            from .notification import send_notification
            send_notification(
                user_id=exchange['user_id'],
                title='兑换商品已发货',
                content=f'您兑换的「{exchange.get("goods_name", "")}」已发货，快递：{logistics_company}，单号：{tracking_no}',
                notify_type='points',
                ref_id=str(exchange_id),
                ref_type='exchange'
            )
        except Exception:
            pass

        return {'success': True, 'msg': '发货成功'}
