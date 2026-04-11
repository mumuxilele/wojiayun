"""
购物车服务 V32.0
功能:
  - 购物车数量管理
  - SKU规格选择
  - 立即购买(跳过购物车)
  - 购物车合并(登录时)
  - 价格实时计算
"""
import logging
import json
from datetime import datetime
from . import db
from .cache_service import cache_delete
from .exception_handler import try_except, handle_unknown_error

logger = logging.getLogger(__name__)


class CartService:
    """购物车服务"""

    MAX_CART_ITEMS = 50  # 单用户最大购物车商品数
    MAX_QUANTITY_PER_ITEM = 99  # 单商品最大购买数量

    @classmethod
    def get_cart(cls, user_id, ec_id=None, project_id=None):
        """
        获取用户购物车详情

        Returns:
            dict: {
                'items': [...],  # 购物车商品列表
                'total_count': 10,  # 商品种数
                'total_quantity': 15,  # 商品总数量
                'original_price': 299.00,  # 原价总金额
                'discount': 30.00,  # 优惠金额
                'total_price': 269.00,  # 最终价格
                'expired_items': [],  # 失效商品(下架/库存为0)
            }
        """
        try:
            # 查询购物车商品
            sql = """
                SELECT c.id, c.product_id, c.sku_id, c.quantity, c.selected,
                       p.product_name, p.shop_id, p.ec_id, p.project_id,
                       p.price as product_price, p.original_price,
                       p.stock as product_stock, p.status as product_status,
                       p.images as product_images,
                       s.shop_name,
                       sk.id as sku_id, sk.sku_name, sk.sku_code, sk.specs,
                       sk.price as sku_price, sk.original_price as sku_original_price,
                       sk.stock as sku_stock
                FROM business_cart c
                JOIN business_products p ON c.product_id = p.id
                LEFT JOIN business_shops s ON p.shop_id = s.id
                LEFT JOIN business_product_skus sk ON c.sku_id = sk.id AND sk.deleted=0
                WHERE c.user_id=%s AND c.deleted=0
            """
            params = [user_id]

            if ec_id:
                sql += " AND p.ec_id=%s"
                params.append(ec_id)
            if project_id:
                sql += " AND p.project_id=%s"
                params.append(project_id)

            sql += " ORDER BY c.created_at DESC"

            items = db.get_all(sql, params) or []

            result_items = []
            expired_items = []
            total_quantity = 0
            original_price = 0.0
            discount = 0.0

            for item in items:
                # 检查商品状态
                is_expired = False
                stock = item.get('sku_stock') if item.get('sku_id') else item.get('product_stock', 0)
                price = item.get('sku_price') if item.get('sku_id') else item.get('product_price', 0)
                original = item.get('sku_original_price') if item.get('sku_id') else item.get('original_price', 0)

                # 检查是否下架或库存为0
                if item.get('product_status') != 'active':
                    is_expired = True
                elif stock <= 0:
                    is_expired = True
                elif item.get('quantity', 0) > stock:
                    is_expired = True  # 数量超过库存也标记为失效

                # 解析图片
                images = []
                if item.get('product_images'):
                    try:
                        images = json.loads(item['product_images']) if isinstance(item['product_images'], str) else item.get('product_images', [])
                    except json.JSONDecodeError as e:
                        logger.warning(f"商品图片JSON解析失败: {e}")
                        images = []

                cart_item = {
                    'cart_id': item['id'],
                    'product_id': item['product_id'],
                    'sku_id': item.get('sku_id'),
                    'product_name': item['product_name'],
                    'shop_name': item.get('shop_name', ''),
                    'quantity': item['quantity'],
                    'selected': bool(item.get('selected', 1)),
                    'price': float(price) if price else 0,
                    'original_price': float(original) if original else float(price) if price else 0,
                    'stock': stock,
                    'images': images,
                    'is_expired': is_expired,
                }

                # 如果有SKU，添加SKU信息
                if item.get('sku_id'):
                    cart_item['sku_name'] = item.get('sku_name', '')
                    cart_item['sku_code'] = item.get('sku_code', '')
                    try:
                        cart_item['specs'] = json.loads(item.get('specs', '{}')) if item.get('specs') else {}
                    except json.JSONDecodeError as e:
                        logger.warning(f"SKU规格JSON解析失败: {e}")
                        cart_item['specs'] = {}

                if is_expired:
                    expired_items.append(cart_item)
                else:
                    result_items.append(cart_item)
                    total_quantity += item['quantity']
                    original_price += float(original or price or 0) * item['quantity']
                    discount += ((float(original or price or 0) - float(price or 0)) * item['quantity'])

            return {
                'items': result_items,
                'total_count': len(result_items),
                'total_quantity': total_quantity,
                'original_price': round(original_price, 2),
                'discount': round(max(0, discount), 2),
                'total_price': round(original_price - discount, 2),
                'expired_items': expired_items,
            }

        except Exception as e:
            logger.error(f"获取购物车失败: user_id={user_id}, error={e}")
            return {
                'items': [],
                'total_count': 0,
                'total_quantity': 0,
                'original_price': 0,
                'discount': 0,
                'total_price': 0,
                'expired_items': [],
            }

    @classmethod
    def add_to_cart(cls, user_id, product_id, quantity=1, sku_id=None,
                    ec_id=None, project_id=None):
        """
        添加商品到购物车

        Args:
            user_id: 用户ID
            product_id: 商品ID
            quantity: 数量
            sku_id: SKU ID (可选)
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: {'success': bool, 'msg': str, 'cart_count': int}
        """
        if quantity <= 0:
            return {'success': False, 'msg': '数量必须大于0', 'cart_count': 0}
        if quantity > cls.MAX_QUANTITY_PER_ITEM:
            return {'success': False, 'msg': f'单商品最多购买{cls.MAX_QUANTITY_PER_ITEM}件', 'cart_count': 0}

        try:
            # 校验商品
            product = db.get_one(
                "SELECT id, product_name, status, stock, price FROM business_products WHERE id=%s AND deleted=0",
                [product_id]
            )
            if not product:
                return {'success': False, 'msg': '商品不存在', 'cart_count': 0}
            if product.get('status') != 'active':
                return {'success': False, 'msg': '商品已下架', 'cart_count': 0}

            # 校验SKU
            stock = product.get('stock', 0)
            price = product.get('price', 0)
            if sku_id:
                sku = db.get_one(
                    "SELECT id, stock, price FROM business_product_skus WHERE id=%s AND product_id=%s AND status=1 AND deleted=0",
                    [sku_id, product_id]
                )
                if not sku:
                    return {'success': False, 'msg': 'SKU不存在', 'cart_count': 0}
                stock = sku.get('stock', 0)
                price = sku.get('price', 0)
            else:
                sku_id = None

            # 检查购物车中是否已有该商品
            existing = db.get_one(
                "SELECT id, quantity FROM business_cart WHERE user_id=%s AND product_id=%s AND sku_id=%s AND deleted=0",
                [user_id, product_id, sku_id]
            )

            new_quantity = quantity
            if existing:
                new_quantity = existing['quantity'] + quantity
                if new_quantity > stock:
                    return {'success': False, 'msg': f'库存不足，当前库存{stock}件', 'cart_count': 0}
                if new_quantity > cls.MAX_QUANTITY_PER_ITEM:
                    return {'success': False, 'msg': f'单商品最多购买{cls.MAX_QUANTITY_PER_ITEM}件', 'cart_count': 0}

                # 更新数量
                db.execute(
                    "UPDATE business_cart SET quantity=%s, updated_at=NOW() WHERE id=%s",
                    [new_quantity, existing['id']]
                )
                msg = f'已更新数量为{new_quantity}'
            else:
                # 检查购物车容量
                cart_count = db.get_total(
                    "SELECT COUNT(*) FROM business_cart WHERE user_id=%s AND deleted=0",
                    [user_id]
                )
                if cart_count >= cls.MAX_CART_ITEMS:
                    return {'success': False, 'msg': f'购物车最多{cls.MAX_CART_ITEMS}种商品', 'cart_count': cart_count}

                if quantity > stock:
                    return {'success': False, 'msg': f'库存不足，当前库存{stock}件', 'cart_count': cart_count}

                # 新增
                db.execute(
                    """INSERT INTO business_cart
                       (user_id, product_id, sku_id, quantity, selected, ec_id, project_id)
                       VALUES (%s, %s, %s, %s, 1, %s, %s)""",
                    [user_id, product_id, sku_id, quantity, ec_id, project_id]
                )
                msg = f'已加入购物车'

            # 清理缓存
            cache_delete(f'cart_{user_id}')

            # 返回购物车商品数
            cart_count = db.get_total(
                "SELECT COUNT(*) FROM business_cart WHERE user_id=%s AND deleted=0",
                [user_id]
            )

            return {'success': True, 'msg': msg, 'cart_count': cart_count}

        except Exception as e:
            logger.error(f"添加购物车失败: user_id={user_id}, product_id={product_id}, error={e}")
            return {'success': False, 'msg': '添加失败，请稍后重试', 'cart_count': 0}

    @classmethod
    def update_quantity(cls, user_id, cart_id, quantity):
        """
        更新购物车商品数量

        Args:
            user_id: 用户ID
            cart_id: 购物车项ID
            quantity: 新数量

        Returns:
            dict: {'success': bool, 'msg': str, 'subtotal': float}
        """
        if quantity <= 0:
            return cls.remove_from_cart(user_id, cart_id)

        if quantity > cls.MAX_QUANTITY_PER_ITEM:
            return {'success': False, 'msg': f'单商品最多购买{cls.MAX_QUANTITY_PER_ITEM}件', 'subtotal': 0}

        try:
            # 获取购物车项
            item = db.get_one(
                "SELECT id, product_id, sku_id, quantity FROM business_cart WHERE id=%s AND user_id=%s AND deleted=0",
                [cart_id, user_id]
            )
            if not item:
                return {'success': False, 'msg': '购物车项不存在', 'subtotal': 0}

            # 获取库存
            if item.get('sku_id'):
                stock_row = db.get_one(
                    "SELECT stock FROM business_product_skus WHERE id=%s AND status=1 AND deleted=0",
                    [item['sku_id']]
                )
            else:
                stock_row = db.get_one(
                    "SELECT stock FROM business_products WHERE id=%s AND status='active' AND deleted=0",
                    [item['product_id']]
                )

            stock = stock_row.get('stock', 0) if stock_row else 0
            if quantity > stock:
                return {'success': False, 'msg': f'库存不足，当前库存{stock}件', 'subtotal': 0}

            # 更新
            db.execute(
                "UPDATE business_cart SET quantity=%s, updated_at=NOW() WHERE id=%s",
                [quantity, cart_id]
            )

            # 清理缓存
            cache_delete(f'cart_{user_id}')

            # 计算小计
            subtotal = 0
            if item.get('sku_id'):
                price_row = db.get_one("SELECT price FROM business_product_skus WHERE id=%s", [item['sku_id']])
            else:
                price_row = db.get_one("SELECT price FROM business_products WHERE id=%s", [item['product_id']])
            if price_row:
                subtotal = float(price_row.get('price', 0)) * quantity

            return {'success': True, 'msg': '更新成功', 'subtotal': round(subtotal, 2)}

        except Exception as e:
            logger.error(f"更新购物车数量失败: cart_id={cart_id}, error={e}")
            return {'success': False, 'msg': '更新失败', 'subtotal': 0}

    @classmethod
    def remove_from_cart(cls, user_id, cart_id):
        """
        从购物车移除商品

        Returns:
            dict: {'success': bool, 'msg': str}
        """
        try:
            result = db.execute(
                "UPDATE business_cart SET deleted=1, updated_at=NOW() WHERE id=%s AND user_id=%s",
                [cart_id, user_id]
            )
            if result == 0:
                return {'success': False, 'msg': '购物车项不存在'}

            cache_delete(f'cart_{user_id}')
            return {'success': True, 'msg': '已移除'}

        except Exception as e:
            logger.error(f"移除购物车商品失败: cart_id={cart_id}, error={e}")
            return {'success': False, 'msg': '移除失败'}

    @classmethod
    def clear_cart(cls, user_id):
        """清空购物车"""
        try:
            db.execute(
                "UPDATE business_cart SET deleted=1, updated_at=NOW() WHERE user_id=%s AND deleted=0",
                [user_id]
            )
            cache_delete(f'cart_{user_id}')
            return {'success': True, 'msg': '购物车已清空'}
        except Exception as e:
            logger.error(f"清空购物车失败: user_id={user_id}, error={e}")
            return {'success': False, 'msg': '清空失败'}

    @classmethod
    def select_items(cls, user_id, cart_ids, selected=True):
        """
        选择/取消选择购物车商品

        Args:
            user_id: 用户ID
            cart_ids: 购物车项ID列表
            selected: 是否选中

        Returns:
            dict: {'success': bool, 'msg': str}
        """
        if not cart_ids:
            return {'success': False, 'msg': '请选择商品'}

        try:
            placeholders = ','.join(['%s'] * len(cart_ids))
            db.execute(
                f"UPDATE business_cart SET selected=%s, updated_at=NOW() WHERE id IN ({placeholders}) AND user_id=%s",
                [1 if selected else 0, user_id] + cart_ids
            )
            cache_delete(f'cart_{user_id}')
            return {'success': True, 'msg': '操作成功'}
        except Exception as e:
            logger.error(f"选择购物车商品失败: error={e}")
            return {'success': False, 'msg': '操作失败'}

    @classmethod
    def get_selected_items(cls, user_id, ec_id=None, project_id=None):
        """
        获取已选择的购物车商品（用于结算）

        Returns:
            list: 已选商品列表
        """
        cart = cls.get_cart(user_id, ec_id, project_id)
        return [item for item in cart.get('items', []) if item.get('selected') and not item.get('is_expired')]

    @classmethod
    def merge_cart(cls, user_id, session_id=None, ec_id=None, project_id=None):
        """
        合并购物车（用户登录时调用）

        策略：
        1. 已有商品：累加数量（不超过库存和最大限制）
        2. 新商品：直接添加

        Args:
            user_id: 登录用户ID
            session_id: 游客会话ID（可选）

        Returns:
            dict: {'success': bool, 'msg': str, 'merged_count': int}
        """
        if not session_id:
            return {'success': True, 'msg': '无需合并', 'merged_count': 0}

        try:
            # 获取游客购物车
            guest_items = db.get_all(
                """SELECT product_id, sku_id, quantity FROM business_cart
                   WHERE session_id=%s AND user_id IS NULL AND deleted=0""",
                [session_id]
            )

            if not guest_items:
                return {'success': True, 'msg': '无需合并', 'merged_count': 0}

            merged_count = 0
            for item in guest_items:
                result = cls.add_to_cart(
                    user_id=user_id,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    sku_id=item.get('sku_id'),
                    ec_id=ec_id,
                    project_id=project_id
                )
                if result.get('success'):
                    merged_count += 1

            # 删除游客购物车
            db.execute(
                "UPDATE business_cart SET deleted=1 WHERE session_id=%s AND user_id IS NULL",
                [session_id]
            )

            cache_delete(f'cart_{user_id}')

            return {
                'success': True,
                'msg': f'已合并{merged_count}件商品',
                'merged_count': merged_count
            }

        except Exception as e:
            logger.error(f"合并购物车失败: user_id={user_id}, session_id={session_id}, error={e}")
            return {'success': False, 'msg': '合并失败', 'merged_count': 0}

    @classmethod
    def create_quick_order(cls, user_id, product_id, quantity=1, sku_id=None,
                          ec_id=None, project_id=None, address_id=None):
        """
        立即购买（跳过购物车直接下单）

        Returns:
            dict: {
                'success': bool,
                'order_data': {...},  # 可直接用于创建订单的预校验数据
            }
        """
        try:
            # 获取商品信息
            if sku_id:
                product = db.get_one("""
                    SELECT p.id, p.product_name, p.shop_id, p.ec_id, p.project_id,
                           p.images, sk.sku_name, sk.specs, sk.price, sk.stock
                    FROM business_products p
                    JOIN business_product_skus sk ON p.id = sk.product_id
                    WHERE sk.id=%s AND p.id=%s AND p.status='active' AND sk.status=1
                """, [sku_id, product_id])
            else:
                product = db.get_one("""
                    SELECT id, product_name, shop_id, ec_id, project_id,
                           images, price, stock
                    FROM business_products
                    WHERE id=%s AND status='active'
                """, [product_id])

            if not product:
                return {'success': False, 'msg': '商品不存在或已下架', 'order_data': None}

            if product.get('stock', 0) < quantity:
                return {'success': False, 'msg': f'库存不足，当前库存{product.get("stock", 0)}件', 'order_data': None}

            # 获取收货地址
            address = None
            if address_id:
                address = db.get_one(
                    "SELECT * FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
                    [address_id, user_id]
                )

            # 获取店铺信息
            shop = db.get_one("SELECT shop_name FROM business_shops WHERE id=%s", [product.get('shop_id')])

            # 构造订单预览数据
            order_preview = {
                'items': [{
                    'product_id': product['id'],
                    'product_name': product['product_name'],
                    'sku_id': sku_id,
                    'sku_name': product.get('sku_name', ''),
                    'specs': product.get('specs', {}),
                    'quantity': quantity,
                    'price': float(product.get('price', 0)),
                    'images': json.loads(product['images'])[0] if product.get('images') else '',
                }],
                'shop_name': shop.get('shop_name', '') if shop else '',
                'shop_id': product.get('shop_id'),
                'total_amount': float(product.get('price', 0)) * quantity,
                'actual_amount': float(product.get('price', 0)) * quantity,
                'address': address,
                'ec_id': ec_id or product.get('ec_id'),
                'project_id': project_id or product.get('project_id'),
            }

            return {
                'success': True,
                'msg': '可创建订单',
                'order_data': order_preview
            }

        except Exception as e:
            logger.error(f"立即购买预校验失败: user_id={user_id}, product_id={product_id}, error={e}")
            return {'success': False, 'msg': '创建订单预览失败', 'order_data': None}


# 便捷实例
cart = CartService()
