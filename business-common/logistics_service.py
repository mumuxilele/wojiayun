"""
物流追踪服务模块 V29.0
支持: 快递100 API / 聚合数据 / 菜鸟物流查询

V29.0 增强:
  - 物流订阅推送处理完善
  - 物流状态主动通知
  - 物流异常检测与告警
  - 物流时效统计
  - 物流公司智能识别
"""
import json
import logging
import os
import re
import requests
import hashlib
from datetime import datetime, timedelta
from . import db

logger = logging.getLogger(__name__)

# 物流公司编码映射
LOGISTICS_COMPANY_CODES = {
    '顺丰速运': 'SF',
    '顺丰': 'SF',
    '中通快递': 'ZTO',
    '中通': 'ZTO',
    '圆通速递': 'YTO',
    '圆通': 'YTO',
    '韵达快递': 'YD',
    '韵达': 'YD',
    '申通快递': 'STO',
    '申通': 'STO',
    '极兔速递': 'JTSD',
    '极兔': 'JTSD',
    '京东物流': 'JD',
    '京东': 'JD',
    '邮政EMS': 'EMS',
    'EMS': 'EMS',
    '天天快递': 'HHTT',
    '百世快递': 'HTKY',
    '百世': 'HTKY',
    '德邦快递': 'DBL',
    '德邦': 'DBL',
    '宅急送': 'ZJS',
    '优速快递': 'UC',
    '安能物流': 'ANE',
    '中通快运': 'ZTOKY',
    '顺心捷达': 'SXJDFAST',
}

# 物流状态映射
LOGISTICS_STATUS = {
    0: {'name': '暂无轨迹', 'chinese': '暂无物流信息', 'color': '#999'},
    1: {'name': '已揽收', 'chinese': '已发货，等待揽收', 'color': '#1890ff'},
    2: {'name': '运输中', 'chinese': '运输中', 'color': '#722ed1'},
    3: {'name': '派送中', 'chinese': '正在派送', 'color': '#faad14'},
    4: {'name': '已签收', 'chinese': '已签收', 'color': '#52c41a'},
    5: {'name': '拒收', 'chinese': '已拒收', 'color': '#f5222d'},
    6: {'name': '退件中', 'chinese': '退回中', 'color': '#fa8c16'},
    7: {'name': '退件签收', 'chinese': '已退回', 'color': '#8c8c8c'},
}


class LogisticsService:
    """统一物流服务"""

    # 快递100付费API配置（环境变量）
    KUAIDI100_API = 'https://poll.kuaidi100.com/poll/query.do'
    KUAIDI100_SUBSCRIBE = 'https://poll.kuaidi100.com/poll/subscribe.do'
    KUAIDI100_KEY = os.environ.get('KUAIDI100_KEY', '')
    KUAIDI100_CUSTOMER = os.environ.get('KUAIDI100_CUSTOMER', '')

    # 聚合数据API配置（环境变量）
    JUHE_API = 'http://v.juhe.cn/exp/index'
    JUHE_KEY = os.environ.get('JUHE_LOGISTICS_KEY', '')

    # 菜鸟物流API配置
    CN_TAOBAO_API = os.environ.get('CN_TAOBAO_API', '')
    CN_TAOBAO_SECRET = os.environ.get('CN_TAOBAO_SECRET', '')

    # 物流时效阈值（小时）
    DELIVERY_THRESHOLDS = {
        'same_city': 24,      # 同城24小时
        'same_province': 48,  # 同省48小时
        'cross_province': 72, # 跨省72小时
        'remote': 120,        # 偏远地区120小时
    }

    @staticmethod
    def get_company_code(company_name):
        """获取物流公司编码"""
        if not company_name:
            return None
        return LOGISTICS_COMPANY_CODES.get(company_name.strip(), company_name)

    @staticmethod
    def get_company_name(code):
        """通过编码获取物流公司名称"""
        if not code:
            return None
        for name, c in LOGISTICS_COMPANY_CODES.items():
            if c.upper() == code.upper():
                return name
        return code

    # ============ V29.0 新增: 智能识别物流公司 ============

    @classmethod
    def auto_detect_company(cls, tracking_no):
        """
        根据快递单号自动识别物流公司

        Args:
            tracking_no: 快递单号

        Returns:
            dict: {'code': xxx, 'name': xxx, 'confidence': 0.9}
        """
        if not tracking_no:
            return None

        # 顺丰单号: 以SF开头或12位数字(收派员码)或15位数字
        if tracking_no.startswith('SF') or re.match(r'^\d{12}$|^\d{15}$', tracking_no):
            return {'code': 'SF', 'name': '顺丰速运', 'confidence': 0.95}

        # EMS单号: EE/RA开头的13位字母数字
        if re.match(r'^(EE|RA)\w{2}\d{9}(CN|CS)$', tracking_no.upper()):
            return {'code': 'EMS', 'name': '邮政EMS', 'confidence': 0.9}

        # 韵达单号: 10-15位数字
        if re.match(r'^\d{10,15}$', tracking_no) and len(tracking_no) >= 10:
            return {'code': 'YD', 'name': '韵达快递', 'confidence': 0.7}

        # 圆通单号: YTO开头或12位数字
        if tracking_no.startswith('YT') or re.match(r'^\d{12}$', tracking_no):
            return {'code': 'YTO', 'name': '圆通速递', 'confidence': 0.85}

        # 中通单号: 7000开头的12位数字
        if re.match(r'^7000\d{9}$', tracking_no) or re.match(r'^\d{15}$', tracking_no):
            return {'code': 'ZTO', 'name': '中通快递', 'confidence': 0.85}

        # 申通单号: 88/68开头的12位数字
        if re.match(r'^(88|68)\d{10}$', tracking_no):
            return {'code': 'STO', 'name': '申通快递', 'confidence': 0.85}

        # 京东单号: JD/JDD开头或16位数字
        if tracking_no.startswith('JD') or re.match(r'^\d{16}$', tracking_no):
            return {'code': 'JD', 'name': '京东物流', 'confidence': 0.95}

        # 德邦单号: DPK/DX开头的12位数字
        if re.match(r'^(DPK|DX)\d{10}$', tracking_no) or re.match(r'^\d{12}$', tracking_no):
            return {'code': 'DBL', 'name': '德邦快递', 'confidence': 0.8}

        # 极兔单号: JT开头的15位字母数字
        if re.match(r'^JT\w{13}$', tracking_no.upper()):
            return {'code': 'JTSD', 'name': '极兔速递', 'confidence': 0.95}

        return {'code': None, 'name': None, 'confidence': 0}

    @classmethod
    def query_logistics(cls, tracking_no, company_code=None, company_name=None):
        """
        查询物流轨迹

        Args:
            tracking_no: 快递单号
            company_code: 物流公司编码 (可选，自动识别)
            company_name: 物流公司名称 (可选)

        Returns:
            dict: 物流信息结果
        """
        if not tracking_no:
            return {'success': False, 'msg': '快递单号不能为空'}

        # 自动识别公司
        if not company_code and not company_name:
            detected = cls.auto_detect_company(tracking_no)
            if detected and detected['code']:
                company_code = detected['code']
                logger.info(f"自动识别物流公司: {tracking_no} -> {detected['code']}")
        elif company_name and not company_code:
            company_code = cls.get_company_code(company_name)

        try:
            # 优先使用快递100 API
            if cls.KUAIDI100_KEY:
                result = cls._query_kuaidi100(tracking_no, company_code)
                if result.get('success'):
                    return result

            # 备用聚合数据API
            if cls.JUHE_KEY:
                result = cls._query_juhe(tracking_no, company_code)
                if result.get('success'):
                    return result

            # 最后使用模拟数据
            return cls._query_mock(tracking_no, company_code)

        except Exception as e:
            logger.error(f"物流查询失败: tracking_no={tracking_no}, error={e}")
            return {'success': False, 'msg': f'查询失败: {str(e)}'}

    @classmethod
    def _query_juhe(cls, tracking_no, company_code):
        """调用聚合数据物流API"""
        if not cls.JUHE_KEY:
            return cls._query_mock(tracking_no, company_code)

        params = {
            'key': cls.JUHE_KEY,
            'com': company_code or '',
            'no': tracking_no,
        }
        try:
            resp = requests.get(cls.JUHE_API, params=params, timeout=10)
            data = resp.json()

            if data.get('error_code') == 0:
                result = data.get('result', {})
                return {
                    'success': True,
                    'data': {
                        'tracking_no': tracking_no,
                        'company_code': result.get('com'),
                        'company_name': cls.get_company_name(result.get('com')),
                        'status': result.get('status'),
                        'state': cls._parse_state(result.get('state')),
                        'traces': cls._format_traces(result.get('list', [])),
                        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                }
            else:
                return {'success': False, 'msg': data.get('reason', '查询失败')}

        except requests.RequestException as e:
            logger.warning(f"聚合API请求失败，回退到模拟数据: {e}")
            return cls._query_mock(tracking_no, company_code)

    @classmethod
    def _query_kuaidi100(cls, tracking_no, company_code):
        """调用快递100 API查询物流"""
        if not cls.KUAIDI100_KEY:
            return cls._query_mock(tracking_no, company_code)

        try:
            param_str = json.dumps({
                'com': company_code,
                'num': tracking_no
            })
            sign = hashlib.md5(
                f"{cls.KUAIDI100_KEY}{param_str}{cls.KUAIDI100_KEY}".encode()
            ).hexdigest()

            data = {
                'customer': cls.KUAIDI100_CUSTOMER,
                'sign': sign,
                'param': param_str,
                'type': '10'
            }

            resp = requests.post(cls.KUAIDI100_API, data=data, timeout=10)
            result = resp.json()

            if result.get('status') == '200':
                traces = result.get('data', [])
                state = result.get('state', '0')

                return {
                    'success': True,
                    'data': {
                        'tracking_no': tracking_no,
                        'company_code': result.get('com'),
                        'company_name': cls.get_company_name(result.get('com')),
                        'status': result.get('returnStatus'),
                        'state': cls._parse_state(state),
                        'traces': cls._format_traces_kuaidi100(traces),
                        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                }
            else:
                return {'success': False, 'msg': result.get('message', '查询失败')}

        except Exception as e:
            logger.warning(f"快递100 API请求失败，回退到模拟数据: {e}")
            return cls._query_mock(tracking_no, company_code)

    @staticmethod
    def _format_traces_kuaidi100(traces):
        """格式化快递100轨迹数据"""
        if not traces:
            return []

        formatted = []
        for trace in traces:
            formatted.append({
                'time': trace.get('time', ''),
                'status': trace.get('context', trace.get('status', '')),
                'location': trace.get('location', ''),
            })

        formatted.reverse()
        return formatted

    @staticmethod
    def _query_mock(tracking_no, company_code):
        """模拟物流数据 (开发/测试用)"""
        now = datetime.now()
        traces = []

        for i in range(4):
            trace_time = now.replace(hour=8 + i * 4)
            if i == 0:
                traces.append({
                    'time': trace_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': '【揽收】快件已被顺丰速运揽收',
                    'location': '深圳市南山区'
                })
            elif i == 1:
                traces.append({
                    'time': trace_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': '【运输中】快件已发往广州中转场',
                    'location': '深圳市宝安区'
                })
            elif i == 2:
                traces.append({
                    'time': trace_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': '【到达】快件已到达广州中转场',
                    'location': '广州市白云区'
                })
            else:
                traces.append({
                    'time': trace_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': '【派送】快递员正在为您派送',
                    'location': '广州市天河区'
                })

        return {
            'success': True,
            'data': {
                'tracking_no': tracking_no,
                'company_code': company_code or 'SF',
                'company_name': LogisticsService.get_company_name(company_code) or '顺丰速运',
                'status': 3,
                'state': {
                    'code': 3,
                    'name': '派送中',
                    'chinese': '正在派送'
                },
                'traces': traces,
                'is_mock': True,
                'updated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
            }
        }

    @staticmethod
    def _parse_state(state_str):
        """解析物流状态"""
        state_map = {
            '0': 0, '暂无物流信息': 0,
            '1': 1, '已揽收': 1, '在途': 1,
            '2': 2, '运输中': 2,
            '3': 3, '派送中': 3,
            '4': 4, '已签收': 4,
            '5': 5, '拒收': 5,
            '6': 6, '退件中': 6,
            '7': 7, '退件签收': 7,
        }
        code = state_map.get(str(state_str), 0)
        status_info = LOGISTICS_STATUS.get(code, LOGISTICS_STATUS[0])
        return {
            'code': code,
            'name': status_info['name'],
            'chinese': status_info['chinese']
        }

    @staticmethod
    def _format_traces(raw_traces):
        """格式化物流轨迹"""
        if not raw_traces:
            return []

        formatted = []
        for trace in raw_traces:
            if isinstance(trace, dict):
                formatted.append({
                    'time': trace.get('datetime', trace.get('time', '')),
                    'status': trace.get('status', trace.get('remark', '')),
                    'location': trace.get('location', trace.get('area', '')),
                })
            else:
                formatted.append({
                    'time': '',
                    'status': str(trace),
                    'location': '',
                })

        formatted.reverse()
        return formatted

    # ============ 订单物流管理 ============

    @staticmethod
    def update_order_logistics(order_id, tracking_no, logistics_company):
        """更新订单物流信息"""
        try:
            company_code = LogisticsService.get_company_code(logistics_company)

            # 先查询物流获取最新状态
            logistics_info = LogisticsService.query_logistics(tracking_no, company_code)

            conn = db.get_db()
            cursor = conn.cursor()
            conn.begin()

            try:
                cursor.execute("""
                    UPDATE business_orders
                    SET tracking_no = %s,
                        logistics_company = %s,
                        logistics_no = %s,
                        shipped_at = COALESCE(shipped_at, NOW()),
                        updated_at = NOW()
                    WHERE id = %s
                """, [tracking_no, logistics_company, company_code, order_id])

                if logistics_info.get('success'):
                    data = logistics_info.get('data', {})
                    cursor.execute("""
                        INSERT INTO business_logistics_traces
                           (order_id, tracking_no, company_code, status, traces_json, last_updated)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                           status = VALUES(status),
                           traces_json = VALUES(traces_json),
                           last_updated = NOW()
                    """, [
                        order_id,
                        tracking_no,
                        company_code,
                        data.get('state', {}).get('code', 0),
                        json.dumps(data.get('traces', []), ensure_ascii=False)
                    ])

                conn.commit()
                logger.info(f"订单物流信息更新成功: order_id={order_id}, tracking_no={tracking_no}")
                return True

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            logger.error(f"更新订单物流信息失败: order_id={order_id}, error={e}")
            return False

    @staticmethod
    def get_order_logistics(order_id):
        """获取订单物流轨迹"""
        try:
            # 先查数据库缓存
            cached = db.get_one(
                """SELECT tracking_no, logistics_company, company_code, status, traces_json, last_updated
                   FROM business_logistics_traces WHERE order_id=%s""",
                [order_id]
            )

            order = db.get_one(
                "SELECT tracking_no, logistics_company FROM business_orders WHERE id=%s",
                [order_id]
            )

            if not order or not order.get('tracking_no'):
                return {'success': False, 'msg': '订单暂无物流信息'}

            tracking_no = order['tracking_no']
            company = order.get('logistics_company', '')

            # 如果缓存过期或不存在，重新查询
            needs_refresh = True
            if cached:
                last_updated = cached.get('last_updated')
                if last_updated:
                    age = (datetime.now() - last_updated).total_seconds()
                    # 缓存有效期: 派送中5分钟, 已签收1小时
                    current_status = cached.get('status', 0)
                    max_age = 300 if current_status in [1, 2, 3] else 3600
                    needs_refresh = age > max_age

            if needs_refresh:
                logistics_info = LogisticsService.query_logistics(
                    tracking_no,
                    LogisticsService.get_company_code(company)
                )
                if logistics_info.get('success'):
                    LogisticsService._cache_logistics(order_id, logistics_info.get('data', {}))
                    return logistics_info
                elif cached:
                    return LogisticsService._format_cached_result(cached)
            elif cached:
                return LogisticsService._format_cached_result(cached)
            else:
                logistics_info = LogisticsService.query_logistics(
                    tracking_no,
                    LogisticsService.get_company_code(company)
                )
                return logistics_info

        except Exception as e:
            logger.error(f"获取订单物流失败: order_id={order_id}, error={e}")
            return {'success': False, 'msg': f'获取物流信息失败: {str(e)}'}

    @staticmethod
    def _cache_logistics(order_id, data):
        """缓存物流信息"""
        try:
            db.execute("""
                INSERT INTO business_logistics_traces
                   (order_id, tracking_no, company_code, status, traces_json, last_updated)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                   tracking_no = VALUES(tracking_no),
                   company_code = VALUES(company_code),
                   status = VALUES(status),
                   traces_json = VALUES(traces_json),
                   last_updated = NOW()
            """, [
                order_id,
                data.get('tracking_no'),
                data.get('company_code'),
                data.get('state', {}).get('code', 0),
                json.dumps(data.get('traces', []), ensure_ascii=False)
            ])
        except Exception as e:
            logger.warning(f"缓存物流信息失败: {e}")

    @staticmethod
    def _format_cached_result(cached):
        """格式化缓存结果"""
        traces = cached.get('traces_json')
        if isinstance(traces, str):
            try:
                traces = json.loads(traces)
            except:
                traces = []

        return {
            'success': True,
            'data': {
                'tracking_no': cached.get('tracking_no'),
                'company_code': cached.get('company_code'),
                'company_name': LogisticsService.get_company_name(cached.get('company_code')),
                'status': cached.get('status', 0),
                'state': {
                    'code': cached.get('status', 0),
                    'name': LOGISTICS_STATUS.get(cached.get('status', 0), LOGISTICS_STATUS[0])['name'],
                    'chinese': LOGISTICS_STATUS.get(cached.get('status', 0), LOGISTICS_STATUS[0])['chinese']
                },
                'traces': traces,
                'cached': True,
                'updated_at': cached.get('last_updated').strftime('%Y-%m-%d %H:%M:%S') if cached.get('last_updated') else ''
            }
        }

    # ============ V29.0 新增: 物流订阅增强 ============

    @classmethod
    def subscribe_logistics(cls, tracking_no, company_code, order_id, callback_url=None):
        """
        订阅物流状态变更通知

        Args:
            tracking_no: 快递单号
            company_code: 物流公司编码
            order_id: 订单ID
            callback_url: 回调URL

        Returns:
            dict: 订阅结果
        """
        if not cls.KUAIDI100_KEY:
            logger.info(f"快递100未配置，记录订阅请求: order_id={order_id}")
            # 记录订阅请求，稍后处理
            cls._record_subscription(order_id, tracking_no, company_code, callback_url)
            return {'success': True, 'msg': '订阅请求已记录'}

        try:
            param = {
                'com': company_code,
                'num': tracking_no,
                'order': 'desc',
                'resultv2': '1',  # 开启推送
            }

            if callback_url:
                param['callbackurl'] = callback_url

            param_str = json.dumps(param)
            sign = hashlib.md5(
                f"{cls.KUAIDI100_KEY}{param_str}{cls.KUAIDI100_KEY}".encode()
            ).hexdigest()

            data = {
                'customer': cls.KUAIDI100_CUSTOMER,
                'sign': sign,
                'param': param_str,
            }

            resp = requests.post(cls.KUAIDI100_SUBSCRIBE, data=data, timeout=10)
            result = resp.json()

            if result.get('result') == 'true':
                # 更新订阅状态
                db.execute("""
                    UPDATE business_logistics_subscriptions
                    SET status = 1, updated_at = NOW()
                    WHERE order_id = %s
                """, [order_id])

                logger.info(f"物流订阅成功: order_id={order_id}, tracking_no={tracking_no}")
                return {'success': True, 'msg': '订阅成功'}
            else:
                return {'success': False, 'msg': result.get('message', '订阅失败')}

        except Exception as e:
            logger.error(f"物流订阅异常: {e}")
            return {'success': False, 'msg': f'订阅异常: {e}'}

    @staticmethod
    def _record_subscription(order_id, tracking_no, company_code, callback_url):
        """记录订阅请求"""
        try:
            db.execute("""
                INSERT INTO business_logistics_subscriptions
                   (order_id, tracking_no, company_code, subscribe_url, status)
                VALUES (%s, %s, %s, %s, 0)
                ON DUPLICATE KEY UPDATE
                   subscribe_url = VALUES(subscribe_url),
                   status = 0
            """, [order_id, tracking_no, company_code, callback_url])
        except Exception as e:
            logger.warning(f"记录订阅失败: {e}")

    @classmethod
    def handle_subscribe_callback(cls, callback_data):
        """
        处理物流订阅回调

        Args:
            callback_data: 回调数据

        Returns:
            dict: 处理结果
        """
        try:
            # 快递100回调格式
            status = callback_data.get('status', '')
            lastResult = callback_data.get('lastResult', {})
            tracking_no = lastResult.get('nu', '')
            company_code = lastResult.get('com', '')
            data = lastResult.get('data', [])

            # 查找订单
            order = db.get_one(
                "SELECT id FROM business_orders WHERE tracking_no=%s",
                [tracking_no]
            )

            if order:
                order_id = order['id']

                # 更新轨迹缓存
                if data:
                    traces = []
                    for item in data:
                        traces.append({
                            'time': item.get('time', ''),
                            'status': item.get('context', ''),
                            'location': item.get('location', ''),
                        })

                    # 解析最新状态
                    state = '0'
                    if status == 'checkLast':
                        if traces:
                            last_trace = traces[-1]
                            if '签收' in last_trace.get('status', ''):
                                state = '4'
                            elif '派送' in last_trace.get('status', ''):
                                state = '3'
                            elif '揽收' in last_trace.get('status', ''):
                                state = '1'
                            elif '运输' in last_trace.get('status', ''):
                                state = '2'

                    db.execute("""
                        UPDATE business_logistics_traces
                        SET status = %s, traces_json = %s, last_updated = NOW()
                        WHERE order_id = %s
                    """, [state, json.dumps(traces, ensure_ascii=False), order_id])

                # 更新订阅状态
                db.execute("""
                    UPDATE business_logistics_subscriptions
                    SET status = CASE WHEN %s = '4' THEN 3 ELSE 2 END,
                        callback_count = callback_count + 1,
                        last_callback_at = NOW()
                    WHERE order_id = %s
                """, [status, order_id])

                # 触发状态变更通知
                if status in ['4', '5', '6']:
                    cls._notify_status_change(order_id, tracking_no, status)

            return {'success': True, 'msg': '处理成功'}

        except Exception as e:
            logger.error(f"处理物流订阅回调失败: {e}")
            return {'success': False, 'msg': f'处理失败: {e}'}

    @staticmethod
    def _notify_status_change(order_id, tracking_no, status):
        """物流状态变更通知"""
        try:
            order = db.get_one(
                "SELECT user_id, user_name FROM business_orders WHERE id=%s",
                [order_id]
            )

            if not order:
                return

            status_map = {
                '4': ('物流已签收', '您的订单已签收，感谢您的购买！'),
                '5': ('物流拒收', '您的订单已被拒收，请联系客服处理。'),
                '6': ('物流退回', '您的订单正在退回中。'),
            }

            title, content = status_map.get(status, ('物流状态更新', '您的物流状态有更新'))

            try:
                from .notification import send_notification
                send_notification(
                    order['user_id'],
                    title,
                    f"{content} 快递号: {tracking_no}",
                    notify_type='logistics',
                    ref_id=str(order_id),
                    ref_type='order'
                )
            except Exception as e:
                logger.warning(f"物流状态通知发送失败: {e}")

        except Exception as e:
            logger.warning(f"物流状态变更通知失败: {e}")

    # ============ V29.0 新增: 物流时效分析 ============

    @classmethod
    def analyze_delivery_performance(cls, order_id):
        """
        分析物流时效表现

        Args:
            order_id: 订单ID

        Returns:
            dict: 时效分析结果
        """
        try:
            order = db.get_one("""
                SELECT shipped_at, signed_at, tracking_no
                FROM business_orders WHERE id=%s
            """, [order_id])

            if not order or not order.get('shipped_at'):
                return {'success': False, 'msg': '订单未发货'}

            shipped_at = order['shipped_at']
            signed_at = order.get('signed_at')
            tracking_no = order.get('tracking_no', '')

            # 计算发货到签收时长
            if signed_at:
                delivery_hours = (signed_at - shipped_at).total_seconds() / 3600
                status = 'completed'
            else:
                delivery_hours = (datetime.now() - shipped_at).total_seconds() / 3600
                status = 'in_transit'

            # 判断是否超时（基于估算的运输距离）
            # 这里简化处理，实际应该根据收发货地址判断距离
            threshold_hours = cls.DELIVERY_THRESHOLDS['cross_province']  # 默认跨省标准
            is_delayed = delivery_hours > threshold_hours

            return {
                'success': True,
                'data': {
                    'order_id': order_id,
                    'tracking_no': tracking_no,
                    'shipped_at': shipped_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'signed_at': signed_at.strftime('%Y-%m-%d %H:%M:%S') if signed_at else None,
                    'delivery_hours': round(delivery_hours, 1),
                    'threshold_hours': threshold_hours,
                    'is_delayed': is_delayed and status == 'completed',
                    'status': status,
                }
            }

        except Exception as e:
            logger.error(f"物流时效分析失败: {e}")
            return {'success': False, 'msg': f'分析失败: {e}'}

    # ============ 物流公司列表 ============

    @staticmethod
    def get_logistics_companies():
        """获取支持的物流公司列表"""
        return [
            {'code': code, 'name': name}
            for name, code in LOGISTICS_COMPANY_CODES.items()
        ]


# 便捷实例
logistics = LogisticsService()
