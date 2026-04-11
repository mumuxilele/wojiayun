"""
售后服务中心 V43.0

功能：
1. 退货退款完整流程
2. 换货流程
3. 售后工单追踪
4. 退款原因分类统计
5. 售后进度可视化

售后类型：
- refund: 仅退款
- return_refund: 退货退款
- exchange: 换货
- repair: 维修
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

from . import db
from .notification import send_notification

logger = logging.getLogger(__name__)


class AftersalesStatus(Enum):
    """售后状态"""
    PENDING = 'pending'           # 待审核
    APPROVED = 'approved'         # 已同意
    REJECTED = 'rejected'         # 已拒绝
    WAITING_RETURN = 'waiting_return'  # 等待退货
    RETURNED = 'returned'         # 已退货
    RECEIVED = 'received'         # 已收货
    PROCESSING = 'processing'     # 处理中
    COMPLETED = 'completed'       # 已完成
    CLOSED = 'closed'             # 已关闭


class AftersalesService:
    """售后服务中心"""

    # 售后原因分类
    REFUND_REASONS = {
        'quality_issue': {'name': '质量问题', 'type': 'product'},
        'wrong_item': {'name': '发错货', 'type': 'merchant'},
        'not_as_described': {'name': '与描述不符', 'type': 'product'},
        'seven_days': {'name': '七天无理由', 'type': 'user'},
        'damaged': {'name': '商品破损', 'type': 'logistics'},
        'missing': {'name': '少件/漏发', 'type': 'merchant'},
        'other': {'name': '其他原因', 'type': 'other'},
    }

    # 自动关闭时间（天）
    AUTO_CLOSE_DAYS = {
        'pending': 7,      # 待审核7天自动关闭
        'waiting_return': 7,  # 等待退货7天自动关闭
        'completed': 7,    # 完成后7天自动关闭售后单
    }

    def __init__(self):
        self._init_tables()

    def _init_tables(self):
        """初始化售后相关表"""
        try:
            # 售后申请表
            result = db.get_one("SHOW TABLES LIKE 'business_aftersales'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_aftersales (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        aftersales_no VARCHAR(50) NOT NULL COMMENT '售后单号',
                        order_id INT NOT NULL COMMENT '订单ID',
                        order_no VARCHAR(50) NOT NULL COMMENT '订单编号',
                        user_id INT NOT NULL COMMENT '用户ID',
                        type VARCHAR(20) NOT NULL COMMENT '类型:refund/return_refund/exchange/repair',
                        status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
                        reason_code VARCHAR(30) COMMENT '原因代码',
                        reason_desc VARCHAR(200) COMMENT '原因描述',
                        refund_amount DECIMAL(10,2) COMMENT '退款金额',
                        apply_images TEXT COMMENT '申请图片JSON',
                        apply_desc VARCHAR(500) COMMENT '申请说明',
                        tracking_no VARCHAR(50) COMMENT '退货运单号',
                        carrier_name VARCHAR(50) COMMENT '退货快递公司',
                        return_address TEXT COMMENT '退货地址',
                        handler_id INT COMMENT '处理人ID',
                        handler_name VARCHAR(50) COMMENT '处理人姓名',
                        handle_remark VARCHAR(500) COMMENT '处理备注',
                        handle_time DATETIME COMMENT '处理时间',
                        completed_time DATETIME COMMENT '完成时间',
                        close_time DATETIME COMMENT '关闭时间',
                        auto_close_at DATETIME COMMENT '自动关闭时间',
                        ec_id INT COMMENT '企业ID',
                        project_id INT COMMENT '项目ID',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_aftersales_no (aftersales_no),
                        INDEX idx_order (order_id),
                        INDEX idx_user (user_id),
                        INDEX idx_status (status),
                        INDEX idx_type (type),
                        INDEX idx_auto_close (auto_close_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='售后申请表';
                """)
                logger.info("[Aftersales] 创建 business_aftersales 表成功")

            # 售后商品明细表
            result = db.get_one("SHOW TABLES LIKE 'business_aftersales_items'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_aftersales_items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        aftersales_id INT NOT NULL COMMENT '售后单ID',
                        order_item_id INT COMMENT '订单明细ID',
                        product_id INT NOT NULL COMMENT '商品ID',
                        product_name VARCHAR(200) COMMENT '商品名称',
                        sku_id INT COMMENT 'SKU ID',
                        sku_name VARCHAR(200) COMMENT 'SKU名称',
                        quantity INT NOT NULL COMMENT '数量',
                        price DECIMAL(10,2) COMMENT '单价',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_aftersales (aftersales_id),
                        INDEX idx_product (product_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='售后商品明细表';
                """)
                logger.info("[Aftersales] 创建 business_aftersales_items 表成功")

            # 售后进度日志表
            result = db.get_one("SHOW TABLES LIKE 'business_aftersales_logs'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_aftersales_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        aftersales_id INT NOT NULL COMMENT '售后单ID',
                        from_status VARCHAR(20) COMMENT '原状态',
                        to_status VARCHAR(20) NOT NULL COMMENT '新状态',
                        operator_type VARCHAR(20) COMMENT '操作者类型:user/staff/system',
                        operator_id INT COMMENT '操作者ID',
                        operator_name VARCHAR(50) COMMENT '操作者姓名',
                        remark VARCHAR(500) COMMENT '备注',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_aftersales (aftersales_id),
                        INDEX idx_created (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='售后进度日志表';
                """)
                logger.info("[Aftersales] 创建 business_aftersales_logs 表成功")

        except Exception as e:
            logger.error(f"[Aftersales] 初始化表失败: {e}")

    def apply_aftersales(self, user_id: int, order_id: int, 
                         apply_type: str, reason_code: str,
                         items: List[Dict], refund_amount: float = None,
                         apply_desc: str = '', images: List[str] = None,
                         ec_id: int = None, project_id: int = None) -> Dict:
        """
        申请售后

        Args:
            user_id: 用户ID
            order_id: 订单ID
            apply_type: 售后类型 refund/return_refund/exchange/repair
            reason_code: 原因代码
            items: 申请商品 [{product_id, quantity, price}]
            refund_amount: 退款金额
            apply_desc: 申请说明
            images: 申请图片
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            Dict: 申请结果
        """
        try:
            # 检查订单是否存在且可售后
            order = db.get_one("""
                SELECT * FROM business_orders 
                WHERE id=%s AND user_id=%s AND order_status IN ('paid','completed')
            """, [order_id, user_id])

            if not order:
                return {'success': False, 'msg': '订单不存在或不可售后'}

            # 检查是否已有进行中的售后
            existing = db.get_one("""
                SELECT id FROM business_aftersales 
                WHERE order_id=%s AND status NOT IN ('completed','closed','rejected')
            """, [order_id])

            if existing:
                return {'success': False, 'msg': '该订单已有进行中的售后申请'}

            # 生成售后单号
            aftersales_no = f"AS{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id:06d}"

            # 计算退款金额
            if refund_amount is None:
                refund_amount = sum(item['price'] * item['quantity'] for item in items)

            # 创建售后单
            aftersales_id = db.execute("""
                INSERT INTO business_aftersales 
                (aftersales_no, order_id, order_no, user_id, type, status, 
                 reason_code, reason_desc, refund_amount, apply_images, apply_desc,
                 auto_close_at, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, 'pending',
                        %s, %s, %s, %s, %s,
                        DATE_ADD(NOW(), INTERVAL %s DAY), %s, %s)
            """, [
                aftersales_no, order_id, order['order_no'], user_id, apply_type,
                reason_code, self.REFUND_REASONS.get(reason_code, {}).get('name', reason_code),
                refund_amount, json.dumps(images or []), apply_desc,
                self.AUTO_CLOSE_DAYS['pending'], ec_id, project_id
            ])

            # 创建售后商品明细
            for item in items:
                db.execute("""
                    INSERT INTO business_aftersales_items 
                    (aftersales_id, product_id, product_name, sku_id, sku_name, quantity, price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [
                    aftersales_id, item['product_id'], item.get('product_name', ''),
                    item.get('sku_id'), item.get('sku_name', ''),
                    item['quantity'], item['price']
                ])

            # 记录日志
            self._log_progress(aftersales_id, None, 'pending', 'user', user_id, 
                             order.get('user_name'), '提交售后申请')

            logger.info(f"[Aftersales] 提交售后申请: aftersales_no={aftersales_no}")

            return {
                'success': True,
                'aftersales_id': aftersales_id,
                'aftersales_no': aftersales_no,
                'msg': '申请已提交，等待审核'
            }

        except Exception as e:
            logger.error(f"[Aftersales] 提交申请失败: {e}")
            return {'success': False, 'msg': str(e)}

    def handle_apply(self, aftersales_id: int, action: str, 
                     handler_id: int, handler_name: str,
                     remark: str = '', return_address: str = '') -> Dict:
        """
        处理售后申请

        Args:
            aftersales_id: 售后单ID
            action: 处理动作 approve/reject
            handler_id: 处理人ID
            handler_name: 处理人姓名
            remark: 处理备注
            return_address: 退货地址（退货退款时）

        Returns:
            Dict: 处理结果
        """
        try:
            aftersales = db.get_one(
                "SELECT * FROM business_aftersales WHERE id=%s",
                [aftersales_id]
            )

            if not aftersales:
                return {'success': False, 'msg': '售后单不存在'}

            if aftersales['status'] != 'pending':
                return {'success': False, 'msg': '该申请已处理'}

            if action == 'approve':
                # 同意申请
                new_status = 'waiting_return' if aftersales['type'] in ['return_refund', 'exchange'] else 'processing'
                
                db.execute("""
                    UPDATE business_aftersales 
                    SET status=%s, handler_id=%s, handler_name=%s, 
                        handle_remark=%s, return_address=%s, handle_time=NOW(),
                        auto_close_at=DATE_ADD(NOW(), INTERVAL %s DAY)
                    WHERE id=%s
                """, [new_status, handler_id, handler_name, remark, return_address,
                      self.AUTO_CLOSE_DAYS.get(new_status, 7), aftersales_id])

                # 记录日志
                self._log_progress(aftersales_id, 'pending', new_status, 
                                 'staff', handler_id, handler_name, f'同意申请: {remark}')

                msg = '申请已同意'

            else:
                # 拒绝申请
                db.execute("""
                    UPDATE business_aftersales 
                    SET status='rejected', handler_id=%s, handler_name=%s, 
                        handle_remark=%s, handle_time=NOW()
                    WHERE id=%s
                """, [handler_id, handler_name, remark, aftersales_id])

                # 记录日志
                self._log_progress(aftersales_id, 'pending', 'rejected',
                                 'staff', handler_id, handler_name, f'拒绝申请: {remark}')

                msg = '申请已拒绝'

            return {'success': True, 'msg': msg}

        except Exception as e:
            logger.error(f"[Aftersales] 处理申请失败: {e}")
            return {'success': False, 'msg': str(e)}

    def submit_return(self, aftersales_id: int, user_id: int,
                      tracking_no: str, carrier_name: str) -> Dict:
        """
        提交退货物流信息

        Args:
            aftersales_id: 售后单ID
            user_id: 用户ID
            tracking_no: 运单号
            carrier_name: 快递公司

        Returns:
            Dict: 提交结果
        """
        try:
            aftersales = db.get_one(
                "SELECT * FROM business_aftersales WHERE id=%s AND user_id=%s",
                [aftersales_id, user_id]
            )

            if not aftersales:
                return {'success': False, 'msg': '售后单不存在'}

            if aftersales['status'] != 'waiting_return':
                return {'success': False, 'msg': '当前状态不可提交退货'}

            db.execute("""
                UPDATE business_aftersales 
                SET tracking_no=%s, carrier_name=%s, status='returned',
                    updated_at=NOW()
                WHERE id=%s
            """, [tracking_no, carrier_name, aftersales_id])

            # 记录日志
            self._log_progress(aftersales_id, 'waiting_return', 'returned',
                             'user', user_id, '', f'提交退货物流: {carrier_name} {tracking_no}')

            return {'success': True, 'msg': '退货信息已提交'}

        except Exception as e:
            logger.error(f"[Aftersales] 提交退货失败: {e}")
            return {'success': False, 'msg': str(e)}

    def confirm_receive(self, aftersales_id: int, staff_id: int, staff_name: str) -> Dict:
        """
        确认收货

        Args:
            aftersales_id: 售后单ID
            staff_id: 员工ID
            staff_name: 员工姓名

        Returns:
            Dict: 确认结果
        """
        try:
            aftersales = db.get_one(
                "SELECT * FROM business_aftersales WHERE id=%s",
                [aftersales_id]
            )

            if not aftersales:
                return {'success': False, 'msg': '售后单不存在'}

            if aftersales['status'] != 'returned':
                return {'success': False, 'msg': '当前状态不可确认收货'}

            db.execute("""
                UPDATE business_aftersales 
                SET status='processing', updated_at=NOW()
                WHERE id=%s
            """, [aftersales_id])

            # 记录日志
            self._log_progress(aftersales_id, 'returned', 'processing',
                             'staff', staff_id, staff_name, '确认收货')

            # 如果是仅退款，直接完成
            if aftersales['type'] == 'refund':
                return self.complete_aftersales(aftersales_id, staff_id, staff_name)

            return {'success': True, 'msg': '已确认收货，等待处理'}

        except Exception as e:
            logger.error(f"[Aftersales] 确认收货失败: {e}")
            return {'success': False, 'msg': str(e)}

    def complete_aftersales(self, aftersales_id: int, staff_id: int, staff_name: str,
                          refund_transaction_no: str = '') -> Dict:
        """
        完成售后（退款/换货）

        Args:
            aftersales_id: 售后单ID
            staff_id: 员工ID
            staff_name: 员工姓名
            refund_transaction_no: 退款交易号

        Returns:
            Dict: 完成结果
        """
        try:
            aftersales = db.get_one(
                "SELECT * FROM business_aftersales WHERE id=%s",
                [aftersales_id]
            )

            if not aftersales:
                return {'success': False, 'msg': '售后单不存在'}

            db.execute("""
                UPDATE business_aftersales 
                SET status='completed', completed_time=NOW(),
                    auto_close_at=DATE_ADD(NOW(), INTERVAL %s DAY)
                WHERE id=%s
            """, [self.AUTO_CLOSE_DAYS['completed'], aftersales_id])

            # 记录日志
            self._log_progress(aftersales_id, aftersales['status'], 'completed',
                             'staff', staff_id, staff_name, '售后完成')

            # 处理退款
            if aftersales['type'] in ['refund', 'return_refund']:
                # 这里调用退款服务
                logger.info(f"[Aftersales] 执行退款: aftersales_id={aftersales_id}, amount={aftersales['refund_amount']}")

            logger.info(f"[Aftersales] 售后完成: aftersales_id={aftersales_id}")

            return {'success': True, 'msg': '售后已完成'}

        except Exception as e:
            logger.error(f"[Aftersales] 完成售后失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_aftersales_detail(self, aftersales_id: int, user_id: int = None) -> Dict:
        """
        获取售后详情

        Args:
            aftersales_id: 售后单ID
            user_id: 用户ID（可选，用于权限校验）

        Returns:
            Dict: 售后详情
        """
        try:
            where = "id=%s"
            params = [aftersales_id]
            
            if user_id:
                where += " AND user_id=%s"
                params.append(user_id)

            aftersales = db.get_one(f"""
                SELECT a.*, o.product_name as order_product_name
                FROM business_aftersales a
                LEFT JOIN business_orders o ON a.order_id = o.id
                WHERE {where}
            """, params)

            if not aftersales:
                return {'success': False, 'msg': '售后单不存在'}

            # 获取商品明细
            items = db.get_all("""
                SELECT * FROM business_aftersales_items 
                WHERE aftersales_id=%s
            """, [aftersales_id])

            # 获取进度日志
            logs = db.get_all("""
                SELECT * FROM business_aftersales_logs 
                WHERE aftersales_id=%s 
                ORDER BY created_at ASC
            """, [aftersales_id])

            return {
                'success': True,
                'data': {
                    'aftersales_id': aftersales['id'],
                    'aftersales_no': aftersales['aftersales_no'],
                    'type': aftersales['type'],
                    'type_name': self._get_type_name(aftersales['type']),
                    'status': aftersales['status'],
                    'status_name': self._get_status_name(aftersales['status']),
                    'reason': {
                        'code': aftersales['reason_code'],
                        'name': aftersales['reason_desc']
                    },
                    'refund_amount': float(aftersales['refund_amount']) if aftersales['refund_amount'] else 0,
                    'apply_desc': aftersales['apply_desc'],
                    'images': json.loads(aftersales['apply_images']) if aftersales['apply_images'] else [],
                    'tracking_no': aftersales['tracking_no'],
                    'carrier_name': aftersales['carrier_name'],
                    'return_address': aftersales['return_address'],
                    'handler_name': aftersales['handler_name'],
                    'handle_remark': aftersales['handle_remark'],
                    'items': items or [],
                    'logs': logs or [],
                    'created_at': str(aftersales['created_at']),
                    'completed_time': str(aftersales['completed_time']) if aftersales['completed_time'] else None,
                }
            }

        except Exception as e:
            logger.error(f"[Aftersales] 获取详情失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_user_aftersales_list(self, user_id: int, page: int = 1, 
                                  page_size: int = 10) -> Dict:
        """
        获取用户售后列表

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量

        Returns:
            Dict: 列表数据
        """
        try:
            offset = (page - 1) * page_size
            
            total = db.get_total(
                "SELECT COUNT(*) FROM business_aftersales WHERE user_id=%s",
                [user_id]
            )

            items = db.get_all("""
                SELECT a.*, o.product_name
                FROM business_aftersales a
                LEFT JOIN business_orders o ON a.order_id = o.id
                WHERE a.user_id=%s
                ORDER BY a.created_at DESC
                LIMIT %s OFFSET %s
            """, [user_id, page_size, offset])

            result = []
            for item in items:
                result.append({
                    'aftersales_id': item['id'],
                    'aftersales_no': item['aftersales_no'],
                    'type': item['type'],
                    'type_name': self._get_type_name(item['type']),
                    'status': item['status'],
                    'status_name': self._get_status_name(item['status']),
                    'refund_amount': float(item['refund_amount']) if item['refund_amount'] else 0,
                    'created_at': str(item['created_at']),
                })

            return {
                'success': True,
                'data': {
                    'items': result,
                    'total': total,
                    'page': page,
                    'page_size': page_size
                }
            }

        except Exception as e:
            logger.error(f"[Aftersales] 获取列表失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_aftersales_stats(self, ec_id: int = None, project_id: int = None,
                             date_from: str = None, date_to: str = None) -> Dict:
        """
        获取售后统计

        Args:
            ec_id: 企业ID
            project_id: 项目ID
            date_from: 开始日期
            date_to: 结束日期

        Returns:
            Dict: 统计数据
        """
        try:
            where = "1=1"
            params = []

            if ec_id:
                where += " AND ec_id=%s"
                params.append(ec_id)
            if project_id:
                where += " AND project_id=%s"
                params.append(project_id)
            if date_from:
                where += " AND created_at>=%s"
                params.append(date_from)
            if date_to:
                where += " AND created_at<=%s"
                params.append(date_to + ' 23:59:59')

            # 总体统计
            stats = db.get_one(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) as rejected,
                    COALESCE(SUM(refund_amount), 0) as total_refund
                FROM business_aftersales
                WHERE {where}
            """, params)

            # 原因统计
            reason_stats = db.get_all(f"""
                SELECT reason_code, COUNT(*) as count
                FROM business_aftersales
                WHERE {where}
                GROUP BY reason_code
                ORDER BY count DESC
            """, params.copy())

            # 类型统计
            type_stats = db.get_all(f"""
                SELECT type, COUNT(*) as count
                FROM business_aftersales
                WHERE {where}
                GROUP BY type
                ORDER BY count DESC
            """, params.copy())

            return {
                'success': True,
                'data': {
                    'overview': {
                        'total': stats['total'] or 0,
                        'pending': stats['pending'] or 0,
                        'completed': stats['completed'] or 0,
                        'rejected': stats['rejected'] or 0,
                        'total_refund': float(stats['total_refund'] or 0),
                    },
                    'reason_stats': [
                        {
                            'code': r['reason_code'],
                            'name': self.REFUND_REASONS.get(r['reason_code'], {}).get('name', r['reason_code']),
                            'count': r['count']
                        } for r in (reason_stats or [])
                    ],
                    'type_stats': [
                        {
                            'type': t['type'],
                            'name': self._get_type_name(t['type']),
                            'count': t['count']
                        } for t in (type_stats or [])
                    ]
                }
            }

        except Exception as e:
            logger.error(f"[Aftersales] 获取统计失败: {e}")
            return {'success': False, 'msg': str(e)}

    def auto_close_aftersales(self) -> Dict:
        """
        自动关闭超时售后单
        由定时任务调用

        Returns:
            Dict: 处理结果
        """
        try:
            # 查询超时的售后单
            orders = db.get_all("""
                SELECT id, status
                FROM business_aftersales
                WHERE auto_close_at <= NOW()
                  AND status NOT IN ('completed', 'closed')
            """)

            if not orders:
                return {'success': True, 'closed': 0}

            closed_count = 0
            for order in orders:
                try:
                    db.execute("""
                        UPDATE business_aftersales 
                        SET status='closed', close_time=NOW()
                        WHERE id=%s
                    """, [order['id']])

                    # 记录日志
                    self._log_progress(order['id'], order['status'], 'closed',
                                     'system', None, '', '超时自动关闭')

                    closed_count += 1
                    logger.info(f"[Aftersales] 自动关闭售后单: aftersales_id={order['id']}")

                except Exception as e:
                    logger.error(f"[Aftersales] 自动关闭失败 aftersales_id={order['id']}: {e}")

            return {'success': True, 'closed': closed_count}

        except Exception as e:
            logger.error(f"[Aftersales] 自动关闭任务失败: {e}")
            return {'success': False, 'msg': str(e)}

    def _log_progress(self, aftersales_id: int, from_status: str, to_status: str,
                      operator_type: str, operator_id: int, operator_name: str,
                      remark: str = ''):
        """记录进度日志"""
        try:
            db.execute("""
                INSERT INTO business_aftersales_logs 
                (aftersales_id, from_status, to_status, operator_type, operator_id, operator_name, remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [aftersales_id, from_status, to_status, operator_type, 
                  operator_id, operator_name, remark])
        except Exception as e:
            logger.warning(f"[Aftersales] 记录日志失败: {e}")

    def _get_type_name(self, type_code: str) -> str:
        """获取类型名称"""
        names = {
            'refund': '仅退款',
            'return_refund': '退货退款',
            'exchange': '换货',
            'repair': '维修',
        }
        return names.get(type_code, type_code)

    def _get_status_name(self, status_code: str) -> str:
        """获取状态名称"""
        names = {
            'pending': '待审核',
            'approved': '已同意',
            'rejected': '已拒绝',
            'waiting_return': '等待退货',
            'returned': '已退货',
            'received': '已收货',
            'processing': '处理中',
            'completed': '已完成',
            'closed': '已关闭',
        }
        return names.get(status_code, status_code)


# 单例实例
aftersales_service = AftersalesService()
