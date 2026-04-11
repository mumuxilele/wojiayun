"""
订单全链路追踪服务 V43.0

功能：
1. 物流节点可视化追踪
2. 预计送达时间计算
3. 物流异常自动识别
4. 签收自动确认收货
5. 履约全流程监控

依赖：
- logistics_service: 物流查询
- notification: 通知服务
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from . import db
from .logistics_service import logistics
from .notification import send_notification

logger = logging.getLogger(__name__)


class TrackingStatus(Enum):
    """物流节点状态"""
    PENDING = 'pending'           # 待发货
    PICKUP = 'pickup'            # 已揽件
    TRANSIT = 'transit'          # 运输中
    DELIVERY = 'delivery'        # 派送中
    SIGNED = 'signed'            # 已签收
    EXCEPTION = 'exception'      # 异常件
    RETURNED = 'returned'        # 已退回


class OrderTrackingService:
    """订单履约追踪服务"""

    # 签收后自动确认收货时间（天）
    AUTO_CONFIRM_DAYS = 7

    # 物流异常类型
    EXCEPTION_TYPES = {
        'delay': {'name': '运输延误', 'threshold_hours': 72},
        'undeliverable': {'name': '无法派送', 'keywords': ['无法派送', '地址不详', '联系不上']},
        'returning': {'name': '退回中', 'keywords': ['退回', '拒收']},
        'lost': {'name': '疑似丢失', 'threshold_hours': 168},  # 7天无更新
    }

    def __init__(self):
        self._init_tables()

    def _init_tables(self):
        """初始化追踪相关表"""
        try:
            # 订单追踪表
            result = db.get_one("SHOW TABLES LIKE 'business_order_tracking'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_order_tracking (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL COMMENT '订单ID',
                        order_no VARCHAR(50) NOT NULL COMMENT '订单编号',
                        tracking_no VARCHAR(50) COMMENT '物流单号',
                        carrier_code VARCHAR(20) COMMENT '快递公司代码',
                        carrier_name VARCHAR(50) COMMENT '快递公司名称',
                        current_status VARCHAR(20) DEFAULT 'pending' COMMENT '当前状态',
                        tracking_nodes TEXT COMMENT '物流节点JSON',
                        estimated_delivery DATE COMMENT '预计送达日期',
                        shipped_at DATETIME COMMENT '发货时间',
                        delivered_at DATETIME COMMENT '送达时间',
                        signed_at DATETIME COMMENT '签收时间',
                        confirmed_at DATETIME COMMENT '确认收货时间',
                        exception_type VARCHAR(20) COMMENT '异常类型',
                        exception_desc VARCHAR(200) COMMENT '异常描述',
                        last_check_at DATETIME COMMENT '最后查询时间',
                        check_count INT DEFAULT 0 COMMENT '查询次数',
                        auto_confirm_scheduled_at DATETIME COMMENT '自动确认时间',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_order (order_id),
                        INDEX idx_tracking_no (tracking_no),
                        INDEX idx_status (current_status),
                        INDEX idx_exception (exception_type),
                        INDEX idx_auto_confirm (auto_confirm_scheduled_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '订单追踪表';
                """)
                logger.info("[OrderTracking] 创建 business_order_tracking 表成功")

            # 履约事件日志表
            result = db.get_one("SHOW TABLES LIKE 'business_fulfillment_logs'")
            if not result:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS business_fulfillment_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL COMMENT '订单ID',
                        event_type VARCHAR(30) NOT NULL COMMENT '事件类型',
                        event_data TEXT COMMENT '事件数据JSON',
                        operator_type VARCHAR(20) COMMENT '操作者类型:user/system',
                        operator_id INT COMMENT '操作者ID',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_order (order_id),
                        INDEX idx_event (event_type),
                        INDEX idx_created (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '履约事件日志表';
                """)
                logger.info("[OrderTracking] 创建 business_fulfillment_logs 表成功")

        except Exception as e:
            logger.error(f"[OrderTracking] 初始化表失败: {e}")

    def create_tracking(self, order_id: int, order_no: str, 
                        tracking_no: str = None, carrier_code: str = None,
                        carrier_name: str = None) -> Dict:
        """
        创建订单追踪记录

        Args:
            order_id: 订单ID
            order_no: 订单编号
            tracking_no: 物流单号
            carrier_code: 快递公司代码
            carrier_name: 快递公司名称

        Returns:
            Dict: 创建结果
        """
        try:
            # 检查是否已存在
            existing = db.get_one(
                "SELECT id FROM business_order_tracking WHERE order_id=%s",
                [order_id]
            )
            if existing:
                return {'success': True, 'msg': '追踪记录已存在', 'tracking_id': existing['id']}

            tracking_id = db.execute(
                """INSERT INTO business_order_tracking 
                   (order_id, order_no, tracking_no, carrier_code, carrier_name, current_status)
                   VALUES (%s, %s, %s, %s, %s, 'pending')""",
                [order_id, order_no, tracking_no, carrier_code, carrier_name]
            )

            # 记录事件
            self._log_event(order_id, 'tracking_created', {
                'tracking_no': tracking_no,
                'carrier': carrier_name
            })

            logger.info(f"[OrderTracking] 创建追踪记录: order_id={order_id}")
            return {'success': True, 'tracking_id': tracking_id}

        except Exception as e:
            logger.error(f"[OrderTracking] 创建追踪记录失败: {e}")
            return {'success': False, 'msg': str(e)}

    def update_shipment(self, order_id: int, tracking_no: str,
                        carrier_code: str, carrier_name: str) -> Dict:
        """
        更新发货信息

        Args:
            order_id: 订单ID
            tracking_no: 物流单号
            carrier_code: 快递公司代码
            carrier_name: 快递公司名称

        Returns:
            Dict: 更新结果
        """
        try:
            shipped_at = datetime.now()
            
            # 计算预计送达时间（通常3-5天）
            estimated_delivery = (shipped_at + timedelta(days=3)).date()

            db.execute("""
                UPDATE business_order_tracking 
                SET tracking_no=%s, carrier_code=%s, carrier_name=%s,
                    current_status='pickup', shipped_at=%s, estimated_delivery=%s,
                    updated_at=NOW()
                WHERE order_id=%s
            """, [tracking_no, carrier_code, carrier_name, shipped_at, estimated_delivery, order_id])

            # 记录事件
            self._log_event(order_id, 'shipped', {
                'tracking_no': tracking_no,
                'carrier': carrier_name,
                'estimated_delivery': str(estimated_delivery)
            })

            # 订阅物流推送
            try:
                logistics.subscribe_tracking(tracking_no, carrier_code)
            except Exception as e:
                logger.warning(f"订阅物流推送失败: {e}")

            logger.info(f"[OrderTracking] 更新发货信息: order_id={order_id}, tracking_no={tracking_no}")
            return {'success': True, 'estimated_delivery': str(estimated_delivery)}

        except Exception as e:
            logger.error(f"[OrderTracking] 更新发货信息失败: {e}")
            return {'success': False, 'msg': str(e)}

    def sync_tracking(self, order_id: int = None, tracking_no: str = None) -> Dict:
        """
        同步物流信息

        Args:
            order_id: 订单ID（优先）
            tracking_no: 物流单号

        Returns:
            Dict: 同步结果
        """
        try:
            # 获取追踪记录
            if order_id:
                tracking = db.get_one(
                    "SELECT * FROM business_order_tracking WHERE order_id=%s",
                    [order_id]
                )
            else:
                tracking = db.get_one(
                    "SELECT * FROM business_order_tracking WHERE tracking_no=%s",
                    [tracking_no]
                )

            if not tracking:
                return {'success': False, 'msg': '追踪记录不存在'}

            tracking_no = tracking['tracking_no']
            carrier_code = tracking['carrier_code']

            if not tracking_no or not carrier_code:
                return {'success': False, 'msg': '物流信息不完整'}

            # 查询物流轨迹
            trace_result = logistics.query_trace(tracking_no, carrier_code)
            
            if not trace_result.get('success'):
                return {'success': False, 'msg': trace_result.get('msg', '查询失败')}

            traces = trace_result.get('traces', [])
            if not traces:
                return {'success': True, 'msg': '暂无物流信息', 'nodes': []}

            # 解析物流节点
            nodes = self._parse_tracking_nodes(traces)
            current_status = self._determine_status(nodes)

            # 更新数据库
            delivered_at = None
            signed_at = None
            auto_confirm_at = None

            if current_status == TrackingStatus.DELIVERY.value:
                # 派送中，计算自动确认时间
                auto_confirm_at = datetime.now() + timedelta(days=self.AUTO_CONFIRM_DAYS)
            elif current_status == TrackingStatus.SIGNED.value:
                # 已签收
                signed_at = datetime.now()
                auto_confirm_at = datetime.now() + timedelta(days=self.AUTO_CONFIRM_DAYS)

            db.execute("""
                UPDATE business_order_tracking 
                SET tracking_nodes=%s, current_status=%s, last_check_at=NOW(),
                    check_count=check_count+1, delivered_at=%s, signed_at=%s,
                    auto_confirm_scheduled_at=%s, updated_at=NOW()
                WHERE id=%s
            """, [
                json.dumps(nodes, ensure_ascii=False),
                current_status,
                delivered_at,
                signed_at,
                auto_confirm_at,
                tracking['id']
            ])

            # 检查异常
            exception = self._detect_exception(nodes, current_status)
            if exception:
                self._update_exception(tracking['id'], exception)

            logger.info(f"[OrderTracking] 同步物流: order_id={tracking['order_id']}, status={current_status}")
            
            return {
                'success': True,
                'current_status': current_status,
                'nodes': nodes,
                'estimated_delivery': str(tracking['estimated_delivery']) if tracking['estimated_delivery'] else None,
                'auto_confirm_at': str(auto_confirm_at) if auto_confirm_at else None
            }

        except Exception as e:
            logger.error(f"[OrderTracking] 同步物流失败: {e}")
            return {'success': False, 'msg': str(e)}

    def _parse_tracking_nodes(self, traces: List[Dict]) -> List[Dict]:
        """解析物流节点"""
        nodes = []
        for trace in traces:
            node = {
                'time': trace.get('time'),
                'content': trace.get('content'),
                'location': trace.get('location', ''),
                'operator': trace.get('operator', ''),
                'action_code': self._parse_action_code(trace.get('content', ''))
            }
            nodes.append(node)
        return nodes

    def _parse_action_code(self, content: str) -> str:
        """解析物流动作代码"""
        content = content.lower()
        if any(kw in content for kw in ['揽收', '揽件', '收件']):
            return 'pickup'
        elif any(kw in content for kw in ['运输', '发往', '到达']):
            return 'transit'
        elif any(kw in content for kw in ['派送', '配送', '正在派']):
            return 'delivery'
        elif any(kw in content for kw in ['签收', '已签收', '代签收']):
            return 'signed'
        elif any(kw in content for kw in ['异常', '滞留', '疑难']):
            return 'exception'
        elif any(kw in content for kw in ['退回', '拒收']):
            return 'returned'
        return 'other'

    def _determine_status(self, nodes: List[Dict]) -> str:
        """根据节点确定当前状态"""
        if not nodes:
            return TrackingStatus.PENDING.value

        # 按时间倒序，取最新节点
        latest = nodes[0]
        action = latest.get('action_code', 'other')

        status_map = {
            'pickup': TrackingStatus.PICKUP.value,
            'transit': TrackingStatus.TRANSIT.value,
            'delivery': TrackingStatus.DELIVERY.value,
            'signed': TrackingStatus.SIGNED.value,
            'exception': TrackingStatus.EXCEPTION.value,
            'returned': TrackingStatus.RETURNED.value,
        }

        return status_map.get(action, TrackingStatus.TRANSIT.value)

    def _detect_exception(self, nodes: List[Dict], current_status: str) -> Optional[Dict]:
        """检测物流异常"""
        if not nodes:
            return None

        latest = nodes[0]
        content = latest.get('content', '')
        latest_time = datetime.strptime(latest.get('time', ''), '%Y-%m-%d %H:%M:%S') if latest.get('time') else None

        # 检测退回
        if any(kw in content for kw in self.EXCEPTION_TYPES['returning']['keywords']):
            return {'type': 'returning', 'desc': '包裹正在退回'}

        # 检测无法派送
        if any(kw in content for kw in self.EXCEPTION_TYPES['undeliverable']['keywords']):
            return {'type': 'undeliverable', 'desc': '包裹无法派送，请联系快递员'}

        # 检测延误（超过72小时无更新）
        if current_status == TrackingStatus.TRANSIT.value and latest_time:
            hours_since_update = (datetime.now() - latest_time).total_seconds() / 3600
            if hours_since_update > self.EXCEPTION_TYPES['delay']['threshold_hours']:
                return {'type': 'delay', 'desc': f'物流超过{self.EXCEPTION_TYPES["delay"]["threshold_hours"]}小时未更新'}

        # 检测疑似丢失（超过7天无签收）
        if current_status in [TrackingStatus.TRANSIT.value, TrackingStatus.DELIVERY.value] and latest_time:
            hours_since_update = (datetime.now() - latest_time).total_seconds() / 3600
            if hours_since_update > self.EXCEPTION_TYPES['lost']['threshold_hours']:
                return {'type': 'lost', 'desc': '物流长时间未更新，疑似丢失'}

        return None

    def _update_exception(self, tracking_id: int, exception: Dict):
        """更新异常信息"""
        try:
            db.execute("""
                UPDATE business_order_tracking 
                SET exception_type=%s, exception_desc=%s, current_status='exception'
                WHERE id=%s
            """, [exception['type'], exception['desc'], tracking_id])

            logger.warning(f"[OrderTracking] 检测到物流异常: tracking_id={tracking_id}, type={exception['type']}")
        except Exception as e:
            logger.error(f"[OrderTracking] 更新异常信息失败: {e}")

    def get_tracking_info(self, order_id: int) -> Dict:
        """
        获取订单追踪信息

        Args:
            order_id: 订单ID

        Returns:
            Dict: 追踪信息
        """
        try:
            tracking = db.get_one(
                "SELECT * FROM business_order_tracking WHERE order_id=%s",
                [order_id]
            )

            if not tracking:
                return {'success': False, 'msg': '追踪记录不存在'}

            nodes = []
            if tracking.get('tracking_nodes'):
                try:
                    nodes = json.loads(tracking['tracking_nodes'])
                except:
                    pass

            return {
                'success': True,
                'data': {
                    'tracking_no': tracking['tracking_no'],
                    'carrier_name': tracking['carrier_name'],
                    'current_status': tracking['current_status'],
                    'current_status_name': self._get_status_name(tracking['current_status']),
                    'nodes': nodes,
                    'estimated_delivery': str(tracking['estimated_delivery']) if tracking['estimated_delivery'] else None,
                    'shipped_at': str(tracking['shipped_at']) if tracking['shipped_at'] else None,
                    'signed_at': str(tracking['signed_at']) if tracking['signed_at'] else None,
                    'auto_confirm_at': str(tracking['auto_confirm_scheduled_at']) if tracking['auto_confirm_scheduled_at'] else None,
                    'exception_type': tracking['exception_type'],
                    'exception_desc': tracking['exception_desc'],
                }
            }

        except Exception as e:
            logger.error(f"[OrderTracking] 获取追踪信息失败: {e}")
            return {'success': False, 'msg': str(e)}

    def _get_status_name(self, status: str) -> str:
        """获取状态名称"""
        names = {
            'pending': '待发货',
            'pickup': '已揽件',
            'transit': '运输中',
            'delivery': '派送中',
            'signed': '已签收',
            'exception': '异常件',
            'returned': '已退回',
        }
        return names.get(status, '未知')

    def auto_confirm_orders(self) -> Dict:
        """
        自动确认收货
        由定时任务调用

        Returns:
            Dict: 处理结果
        """
        try:
            # 查询已到自动确认时间的订单
            orders = db.get_all("""
                SELECT id, order_id, order_no, auto_confirm_scheduled_at
                FROM business_order_tracking
                WHERE auto_confirm_scheduled_at <= NOW()
                  AND current_status IN ('signed', 'delivery')
                  AND confirmed_at IS NULL
            """)

            if not orders:
                return {'success': True, 'processed': 0}

            confirmed_count = 0
            for order in orders:
                try:
                    # 更新订单状态为已完成
                    db.execute("""
                        UPDATE business_orders 
                        SET order_status='completed', updated_at=NOW()
                        WHERE id=%s
                    """, [order['order_id']])

                    # 更新追踪记录
                    db.execute("""
                        UPDATE business_order_tracking 
                        SET confirmed_at=NOW(), current_status='completed', updated_at=NOW()
                        WHERE id=%s
                    """, [order['id']])

                    # 记录事件
                    self._log_event(order['order_id'], 'auto_confirmed', {
                        'tracking_id': order['id'],
                        'scheduled_at': str(order['auto_confirm_scheduled_at'])
                    })

                    confirmed_count += 1
                    logger.info(f"[OrderTracking] 自动确认收货: order_id={order['order_id']}")

                except Exception as e:
                    logger.error(f"[OrderTracking] 自动确认订单失败 order_id={order['order_id']}: {e}")

            return {'success': True, 'processed': confirmed_count}

        except Exception as e:
            logger.error(f"[OrderTracking] 自动确认任务失败: {e}")
            return {'success': False, 'msg': str(e)}

    def _log_event(self, order_id: int, event_type: str, event_data: Dict,
                   operator_type: str = 'system', operator_id: int = None):
        """记录履约事件"""
        try:
            db.execute(
                """INSERT INTO business_fulfillment_logs 
                   (order_id, event_type, event_data, operator_type, operator_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                [order_id, event_type, json.dumps(event_data, ensure_ascii=False), operator_type, operator_id]
            )
        except Exception as e:
            logger.warning(f"[OrderTracking] 记录事件失败: {e}")

    def get_fulfillment_timeline(self, order_id: int) -> List[Dict]:
        """
        获取履约时间线

        Args:
            order_id: 订单ID

        Returns:
            List[Dict]: 时间线事件
        """
        try:
            events = db.get_all("""
                SELECT * FROM business_fulfillment_logs 
                WHERE order_id=%s 
                ORDER BY created_at ASC
            """, [order_id])

            timeline = []
            for event in events:
                data = {}
                if event.get('event_data'):
                    try:
                        data = json.loads(event['event_data'])
                    except:
                        pass

                timeline.append({
                    'event_type': event['event_type'],
                    'event_name': self._get_event_name(event['event_type']),
                    'data': data,
                    'operator_type': event['operator_type'],
                    'created_at': str(event['created_at'])
                })

            return timeline

        except Exception as e:
            logger.error(f"[OrderTracking] 获取时间线失败: {e}")
            return []

    def _get_event_name(self, event_type: str) -> str:
        """获取事件名称"""
        names = {
            'tracking_created': '创建追踪',
            'shipped': '商家发货',
            'synced': '物流同步',
            'auto_confirmed': '自动确认收货',
            'confirmed': '确认收货',
            'exception_detected': '异常检测',
        }
        return names.get(event_type, event_type)

    def get_overdue_orders(self, days: int = 7) -> List[Dict]:
        """
        获取超期未确认订单

        Args:
            days: 超期天数

        Returns:
            List[Dict]: 超期订单列表
        """
        try:
            orders = db.get_all("""
                SELECT t.*, o.user_id, o.user_name, o.user_phone
                FROM business_order_tracking t
                JOIN business_orders o ON t.order_id = o.id
                WHERE t.current_status = 'signed'
                  AND t.signed_at <= DATE_SUB(NOW(), INTERVAL %s DAY)
                  AND t.confirmed_at IS NULL
            """, [days])

            return orders or []

        except Exception as e:
            logger.error(f"[OrderTracking] 获取超期订单失败: {e}")
            return []

    def batch_sync_tracking(self, limit: int = 100) -> Dict:
        """
        批量同步物流信息
        由定时任务调用

        Args:
            limit: 每次处理数量

        Returns:
            Dict: 处理结果
        """
        try:
            # 获取需要同步的订单（已发货但未签收/异常）
            orders = db.get_all("""
                SELECT order_id, tracking_no, carrier_code
                FROM business_order_tracking
                WHERE current_status IN ('pickup', 'transit', 'delivery')
                  AND (last_check_at IS NULL OR last_check_at <= DATE_SUB(NOW(), INTERVAL 2 HOUR))
                LIMIT %s
            """, [limit])

            if not orders:
                return {'success': True, 'synced': 0}

            synced_count = 0
            for order in orders:
                try:
                    result = self.sync_tracking(order_id=order['order_id'])
                    if result.get('success'):
                        synced_count += 1
                except Exception as e:
                    logger.error(f"[OrderTracking] 同步订单失败 order_id={order['order_id']}: {e}")

            return {'success': True, 'synced': synced_count, 'total': len(orders)}

        except Exception as e:
            logger.error(f"[OrderTracking] 批量同步失败: {e}")
            return {'success': False, 'msg': str(e)}


# 单例实例
order_tracking = OrderTrackingService()
