#!/usr/bin/env python3
"""
订单打印服务模块 V28.0
"""
import json
import logging
from . import db

logger = logging.getLogger(__name__)


class PrintService:
    """打印服务"""
    
    LOGISTICS_COMPANIES = {
        'SF': '顺丰速运', 'YTO': '圆通速递', 'ZTO': '中通快递',
        'STO': '申通快递', 'YD': '韵达快递', 'JTSD': '极兔速递',
        'EMS': '中国邮政EMS', 'YZPY': '邮政快递包裹', 'JD': '京东物流',
        'DBL': '德邦快递', 'OTHER': '其他'
    }

    @staticmethod
    def get_logistics_companies():
        return [{'code': k, 'name': v} for k, v in PrintService.LOGISTICS_COMPANIES.items()]

    @staticmethod
    def generate_express_template(order):
        address = order.get('shipping_address') or ''
        address_parts = address.split('|')
        if len(address_parts) >= 3:
            receiver_name = address_parts[0]
            receiver_phone = address_parts[1]
            receiver_address = address_parts[2]
        else:
            receiver_name = order.get('user_name', '')
            receiver_phone = ''
            receiver_address = address

        items = db.get_all(
            "SELECT product_name, quantity FROM business_order_items WHERE order_id=%s",
            [order.get('id')]
        ) or []
        goods_detail = ' '.join([f"{item.get('product_name', '')}x{item.get('quantity', 1)}" for item in items[:3]])

        return {
            'template_type': 'express',
            'order_no': order.get('order_no', ''),
            'sender': {'name': '社区商业', 'phone': '400-888-8888', 'address': '上海市浦东新区'},
            'receiver': {'name': receiver_name, 'phone': receiver_phone, 'address': receiver_address},
            'goods_detail': goods_detail,
            'remark': order.get('remark') or ''
        }

    @staticmethod
    def generate_picking_template(order):
        items = db.get_all(
            """SELECT oi.product_name, oi.sku_name, oi.quantity, p.stock
               FROM business_order_items oi
               LEFT JOIN business_products p ON p.id = oi.product_id
               WHERE oi.order_id=%s""",
            [order.get('id')]
        ) or []
        
        address = order.get('shipping_address') or ''
        address_parts = address.split('|')
        
        return {
            'template_type': 'picking',
            'order_no': order.get('order_no', ''),
            'receiver_name': address_parts[0] if address_parts else order.get('user_name', ''),
            'receiver_phone': address_parts[1] if len(address_parts) > 1 else '',
            'receiver_address': address_parts[2] if len(address_parts) > 2 else '',
            'items': [{'product_name': i.get('product_name', ''), 'sku_name': i.get('sku_name') or '', 
                      'quantity': i.get('quantity', 1)} for i in items],
            'total_quantity': sum(i.get('quantity', 1) for i in items),
            'total_amount': float(order.get('actual_amount') or 0),
            'remark': order.get('remark') or ''
        }

    @staticmethod
    def log_print(order_id, order_no, print_type, print_content, operator_id=None, operator_name='', copies=1):
        try:
            db.execute(
                """INSERT INTO business_print_logs
                   (order_id, order_no, print_type, print_content, copies, operator_id, operator_name)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                [order_id, order_no, print_type, json.dumps(print_content, ensure_ascii=False),
                 copies, operator_id, operator_name]
            )
            result = db.get_one("SELECT LAST_INSERT_ID() as id")
            return result.get('id') if result else 0
        except Exception as e:
            logger.error(f"记录打印日志失败: {e}")
            return 0

    @staticmethod
    def get_print_history(order_id, limit=10):
        logs = db.get_all(
            """SELECT id, print_type, copies, printer_name, operator_name, created_at
               FROM business_print_logs WHERE order_id=%s ORDER BY created_at DESC LIMIT %s""",
            [order_id, limit]
        )
        type_names = {'express': '快递单', 'picking': '配货单', 'invoice': '发票'}
        for log in logs or []:
            log['type_name'] = type_names.get(log.get('print_type'), log.get('print_type'))
        return logs or []

    @staticmethod
    def update_tracking_info(order_id, logistics_company, tracking_no, operator_id=None):
        if not order_id or not tracking_no:
            return {'success': False, 'msg': '订单ID和物流单号不能为空'}
        try:
            db.execute(
                "UPDATE business_orders SET logistics_company=%s, tracking_no=%s, updated_at=NOW() WHERE id=%s",
                [logistics_company, tracking_no, order_id]
            )
            order = db.get_one("SELECT order_no FROM business_orders WHERE id=%s", [order_id])
            PrintService.log_print(order_id, order.get('order_no', ''), 'express',
                                 {'logistics_company': logistics_company, 'tracking_no': tracking_no}, operator_id)
            return {'success': True, 'msg': '物流信息已更新'}
        except Exception as e:
            logger.error(f"更新物流信息失败: {e}")
            return {'success': False, 'msg': '更新失败'}
