"""
Order Service
订单业务逻辑层
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_service import BaseService
from ..models.order import Order
from ..repositories.order_repository import OrderRepository
from ..repositories.product_repository import ProductRepository
from ..fid_utils import generate_business_fid

logger = logging.getLogger(__name__)


class OrderService(BaseService):
    """订单服务"""
    
    SERVICE_NAME = 'OrderService'
    ORDER_EXPIRE_MINUTES = 30  # 订单过期时间
    
    def __init__(self):
        super().__init__()
        self.order_repo = OrderRepository()
        self.product_repo = ProductRepository()
    
    # ============ 创建订单 ============
    
    def create_order(self,
                    user_id: str,
                    user_name: str,
                    items: List[Dict],
                    ec_id: str = None,
                    project_id: str = None,
                    receiver_name: str = None,
                    receiver_phone: str = None,
                    receiver_address: str = None,
                    remark: str = None) -> Dict[str, Any]:
        """
        创建订单
        
        Args:
            user_id: 用户ID
            user_name: 用户姓名
            items: 订单商品列表 [{'product_id': 1, 'quantity': 2, 'sku_id': ...}]
            ec_id: 企业ID
            project_id: 项目ID
            receiver_name: 收货人姓名
            receiver_phone: 收货人电话
            receiver_address: 收货地址
            remark: 备注
            
        Returns:
            {'success': True/False, 'msg': '...', 'data': {...}}
        """
        try:
            # 参数校验
            if not items or not isinstance(items, list):
                return self.error('订单商品不能为空')
            
            # 检查库存并计算价格
            total_amount = 0
            actual_amount = 0
            order_items = []
            
            for item in items:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 1)
                
                if not product_id or quantity <= 0:
                    continue
                
                # 查询商品
                product_data = self.product_repo.find_detail_by_id(product_id)
                if not product_data:
                    return self.error(f'商品不存在: {product_id}')
                
                if product_data.get('stock', 0) < quantity:
                    return self.error(f'商品库存不足: {product_data.get("product_name")}')
                
                # 计算金额
                price = float(product_data.get('price', 0))
                item_total = price * quantity
                total_amount += item_total
                actual_amount += item_total
                
                order_items.append({
                    'product_id': product_id,
                    'product_name': product_data.get('product_name'),
                    'quantity': quantity,
                    'price': price,
                    'total': item_total
                })
            
            if not order_items:
                return self.error('订单商品无效')
            
            # 生成订单号
            fid = generate_business_fid('order')
            today = datetime.now().strftime('%Y%m%d')
            order_no = f"ORD{today}{datetime.now().strftime('%H%M%S')}{user_id[-4:]}"
            
            # 构建数据
            data = {
                'fid': fid,
                'order_no': order_no,
                'user_id': user_id,
                'user_name': user_name,
                'ec_id': ec_id,
                'project_id': project_id,
                'total_amount': total_amount,
                'actual_amount': actual_amount,
                'discount_amount': 0,
                'status': Order.STATUS_PENDING_PAYMENT,
                'pay_status': 0,
                'items': order_items,
                'receiver_name': receiver_name,
                'receiver_phone': receiver_phone,
                'receiver_address': receiver_address,
                'remark': remark
            }
            
            # 扣减库存
            for item in items:
                success = self.product_repo.decrease_stock(
                    item['product_id'], 
                    item['quantity']
                )
                if not success:
                    # 库存扣减失败，回滚已扣减的库存
                    for rolled in order_items:
                        if rolled['product_id'] != item['product_id']:
                            self.product_repo.increase_stock(
                                rolled['product_id'],
                                rolled['quantity']
                            )
                    return self.error(f'商品库存不足')
            
            # 序列化 items
            import json
            data['items'] = json.dumps(order_items, ensure_ascii=False)
            
            # 插入数据库
            order_id = self.order_repo.insert(data)
            
            if not order_id:
                # 回滚库存
                for item in order_items:
                    self.product_repo.increase_stock(item['product_id'], item['quantity'])
                return self.error('创建订单失败')
            
            self.logger.info(f"创建订单成功: id={order_id}, user_id={user_id}")
            
            return self.success({
                'id': order_id,
                'fid': fid,
                'order_no': order_no,
                'total_amount': total_amount,
                'actual_amount': actual_amount,
                'status': Order.STATUS_PENDING_PAYMENT
            }, '订单创建成功')
            
        except Exception as e:
            self.logger.error(f"创建订单失败: {e}")
            return self.error(f'创建失败: {str(e)}')
    
    # ============ 查询订单 ============
    
    def get_user_orders(self,
                       user_id: str,
                       status: str = None,
                       page: int = 1,
                       page_size: int = 20) -> Dict[str, Any]:
        """获取用户订单列表"""
        try:
            result = self.order_repo.find_by_user(
                user_id=user_id,
                status=status,
                page=page,
                page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error(f"查询订单列表失败: {e}")
            return self.error('查询失败')
    
    def get_order_detail(self,
                        order_id: int,
                        user_id: str = None) -> Dict[str, Any]:
        """获取订单详情"""
        try:
            data = self.order_repo.find_detail_by_id(order_id, user_id)
            
            if not data:
                return self.error('订单不存在')
            
            # 转换为 Order 对象
            order = Order.from_dict(data)
            return self.success(order.to_dict() if order else data)
            
        except Exception as e:
            self.logger.error(f"查询订单详情失败: {e}")
            return self.error('查询失败')
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户订单统计"""
        try:
            stats = self.order_repo.get_user_order_stats(user_id)
            return self.success(stats)
        except Exception as e:
            self.logger.error(f"获取用户统计失败: {e}")
            return self.error('获取统计失败')
    
    # ============ 订单操作 ============
    
    def cancel_order(self,
                    order_id: int,
                    user_id: str) -> Dict[str, Any]:
        """取消订单"""
        try:
            # 查询订单
            order_data = self.order_repo.find_detail_by_id(order_id, user_id)
            
            if not order_data:
                return self.error('订单不存在')
            
            order = Order.from_dict(order_data)
            
            if not order.can_cancel:
                return self.error('该订单状态不允许取消')
            
            # 恢复库存
            items = order.items or []
            for item in items:
                self.product_repo.increase_stock(
                    item['product_id'],
                    item['quantity']
                )
            
            # 更新订单状态
            affected = self.order_repo.update_status(order_id, Order.STATUS_CANCELLED)
            
            if affected > 0:
                self.logger.info(f"取消订单成功: id={order_id}, user_id={user_id}")
                return self.success(msg='订单已取消')
            else:
                return self.error('取消失败')
                
        except Exception as e:
            self.logger.error(f"取消订单失败: {e}")
            return self.error(f'取消失败: {str(e)}')
    
    # ============ 支付相关 ============
    
    def pay_order(self,
                 order_id: int,
                 user_id: str) -> Dict[str, Any]:
        """支付订单（简化版）"""
        try:
            order_data = self.order_repo.find_detail_by_id(order_id, user_id)
            
            if not order_data:
                return self.error('订单不存在')
            
            order = Order.from_dict(order_data)
            
            if order.status != Order.STATUS_PENDING_PAYMENT:
                return self.error('订单状态不允许支付')
            
            # 更新支付状态
            data = {
                'status': Order.STATUS_PAID,
                'pay_status': 1,
                'pay_time': datetime.now()
            }
            affected = self.order_repo.update(order_id, data)
            
            if affected > 0:
                self.logger.info(f"支付订单成功: id={order_id}, user_id={user_id}")
                return self.success(msg='支付成功')
            else:
                return self.error('支付失败')
                
        except Exception as e:
            self.logger.error(f"支付订单失败: {e}")
            return self.error(f'支付失败: {str(e)}')
