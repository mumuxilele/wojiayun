"""
支付服务模块 V29.0
支持: 模拟支付(开发)、微信支付V3、支付宝

V29.0 增强:
  - 微信支付V3 查询接口完善 (query_wechat_order)
  - 支付宝查询接口完善 (query_alipay_order)
  - 微信退款接口 (wechat_refund)
  - 支付宝退款接口 (alipay_refund)
  - 支付回调处理增强 (handle_payment_callback)
  - 支付安全增强 (支付限额、风控检查)
  - 支付日志完善 (支付全链路追踪)
"""
import json
import logging
import uuid
import hashlib
import time
import os
import requests
from datetime import datetime, timedelta
from . import db

logger = logging.getLogger(__name__)


class PaymentService:
    """统一支付服务"""

    CHANNELS = {
        'mock': '模拟支付',
        'wechat': '微信支付',
        'alipay': '支付宝',
    }

    STATUS = {
        'pending': '待支付',
        'paid': '已支付',
        'failed': '支付失败',
        'refunding': '退款中',
        'refunded': '已退款',
        'expired': '已过期',
        'closed': '已关闭',
    }

    # 微信支付配置（生产环境从环境变量读取）
    WECHAT_CONFIG = {
        'app_id': os.environ.get('WECHAT_APP_ID', ''),
        'mch_id': os.environ.get('WECHAT_MCH_ID', ''),
        'serial_no': os.environ.get('WECHAT_SERIAL_NO', ''),
        'api_v3_key': os.environ.get('WECHAT_API_V3_KEY', ''),
        'private_key': os.environ.get('WECHAT_PRIVATE_KEY', ''),
        'notify_url': os.environ.get('WECHAT_NOTIFY_URL', ''),
    }

    # 支付宝配置（生产环境从环境变量读取）
    ALIPAY_CONFIG = {
        'app_id': os.environ.get('ALIPAY_APP_ID', ''),
        'private_key': os.environ.get('ALIPAY_PRIVATE_KEY', ''),
        'alipay_public_key': os.environ.get('ALIPAY_PUBLIC_KEY', ''),
        'notify_url': os.environ.get('ALIPAY_NOTIFY_URL', ''),
        'gateway': 'https://openapi.alipay.com/gateway.do',
        'sandbox': 'https://openapi-sandbox.dl.alipaydev.com/gateway.do',
    }

    # 微信API基础地址
    WECHAT_API_BASE = 'https://api.mch.weixin.qq.com'

    # 支付安全配置
    PAYMENT_LIMITS = {
        'single_max': 50000.00,  # 单笔最高50万
        'single_min': 0.01,      # 单笔最低0.01元
        'daily_max': 100000.00,  # 每日最高10万
    }

    @classmethod
    def is_wechat_configured(cls):
        """检查微信支付是否已配置"""
        return bool(cls.WECHAT_CONFIG.get('app_id') and cls.WECHAT_CONFIG.get('mch_id'))

    @classmethod
    def is_alipay_configured(cls):
        """检查支付宝是否已配置"""
        return bool(cls.ALIPAY_CONFIG.get('app_id') and cls.ALIPAY_CONFIG.get('private_key'))

    # ============ V29.0 支付安全增强 ============

    @classmethod
    def validate_payment_amount(cls, amount):
        """
        验证支付金额是否合法

        Args:
            amount: 支付金额

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return False, '金额格式错误'

        if amount < cls.PAYMENT_LIMITS['single_min']:
            return False, f'金额不能低于{cls.PAYMENT_LIMITS["single_min"]}元'

        if amount > cls.PAYMENT_LIMITS['single_max']:
            return False, f'单笔金额不能超过{cls.PAYMENT_LIMITS["single_max"]}元'

        return True, None

    @classmethod
    def check_daily_limit(cls, user_id, add_amount=0):
        """
        检查用户当日支付限额

        Args:
            user_id: 用户ID
            add_amount: 追加金额

        Returns:
            tuple: (is_allowed, current_amount, remaining)
        """
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            result = db.get_one("""
                SELECT COALESCE(SUM(amount), 0) as total_amount
                FROM business_payments
                WHERE user_id = %s
                  AND status = 'paid'
                  AND paid_at >= %s
                  AND paid_at < %s
            """, [user_id, today_start, today_end])

            current_amount = float(result.get('total_amount', 0))
            remaining = cls.PAYMENT_LIMITS['daily_max'] - current_amount - add_amount

            return remaining >= 0, current_amount, max(0, remaining)

        except Exception as e:
            logger.error(f"检查日限额失败: user_id={user_id}, error={e}")
            return True, 0, cls.PAYMENT_LIMITS['daily_max']  # 出错时放行

    # ============ 核心支付方法 ============

    @staticmethod
    def create_payment(order_type, order_id, amount, user_id, user_name,
                       channel='mock', ec_id=None, project_id=None, **kwargs):
        """
        创建支付订单

        Args:
            order_type: 订单类型 (order/booking)
            order_id: 关联订单ID
            amount: 支付金额
            user_id: 用户ID
            user_name: 用户名
            channel: 支付渠道 (mock/wechat/alipay)
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 创建结果
        """
        # V29.0: 金额安全校验
        is_valid, error_msg = PaymentService.validate_payment_amount(amount)
        if not is_valid:
            return {'success': False, 'msg': error_msg}

        # V29.0: 日限额检查
        if channel != 'mock':
            allowed, current, remaining = PaymentService.check_daily_limit(user_id, float(amount))
            if not allowed:
                return {'success': False, 'msg': f'超出日支付限额，当前剩余额度: ¥{remaining:.2f}'}

        pay_no = f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

        try:
            db.execute(
                """INSERT INTO business_payments
                   (pay_no, order_type, order_id, amount, user_id, user_name,
                    channel, status, ec_id, project_id, expire_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, DATE_ADD(NOW(), INTERVAL 30 MINUTE))""",
                [pay_no, order_type, order_id, amount, user_id, user_name,
                 channel, ec_id, project_id]
            )

            # V29.0: 支付日志记录
            PaymentService._log_payment_action(pay_no, 'create', {
                'order_type': order_type,
                'order_id': order_id,
                'amount': amount,
                'channel': channel,
            })

            result = {
                'pay_no': pay_no,
                'amount': float(amount),
                'channel': channel,
                'status': 'pending',
                'expire_at': (datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if channel == 'mock':
                result['pay_url'] = f"/api/payment/{pay_no}/confirm"
            elif channel == 'wechat':
                result['pay_url'] = PaymentService._create_wechat_pay_url(pay_no, amount, **kwargs)
            elif channel == 'alipay':
                result['pay_url'] = PaymentService._create_alipay_pay_url(pay_no, amount, **kwargs)

            logger.info(f"支付单创建成功: {pay_no}, type={order_type}, amount={amount}, channel={channel}")
            return {'success': True, 'data': result}

        except Exception as e:
            logger.error(f"支付单创建失败: {e}")
            return {'success': False, 'msg': '创建支付单失败'}

    # ============ 微信支付 V29.0 增强 ============

    @staticmethod
    def _create_wechat_pay_url(pay_no, amount, **kwargs):
        """
        生成微信支付二维码URL（V3 API）
        """
        if not PaymentService.is_wechat_configured():
            logger.warning("微信支付未配置，返回Mock URL")
            return f"weixin://wxpay/bizpayurl?pr={pay_no}"

        try:
            config = PaymentService.WECHAT_CONFIG
            app_id = config['app_id']
            mch_id = config['mch_id']

            timestamp = str(int(time.time()))
            nonce_str = uuid.uuid4().hex[:32]

            # 统一下单请求体
            body = {
                'appid': app_id,
                'mch_id': mch_id,
                'out_trade_no': pay_no,
                'description': f'社区商业订单-{pay_no[:20]}',
                'notify_url': config.get('notify_url') or '',
                'amount': {
                    'total': int(float(amount) * 100),  # 转换为分
                    'currency': 'CNY'
                },
                'scene_info': {
                    'payer_client_ip': kwargs.get('client_ip', '127.0.0.1')
                }
            }

            # 生成签名
            method = 'POST'
            url_path = '/v3/pay/transactions/native'
            message = f'{method}\n{url_path}\n{timestamp}\n{nonce_str}\n{json.dumps(body)}\n'
            signature = PaymentService._wechat_sign(message, config['private_key'])

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'WECHATPAY2-SHA256-RSA2048 mchid="{mch_id}",nonce_str="{nonce_str}",timestamp="{timestamp}",signature="{signature}",serial_no="{config["serial_no"]}"'
            }

            response = requests.post(
                f"{PaymentService.WECHAT_API_BASE}{url_path}",
                data=json.dumps(body),
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                code_url = result.get('code_url')
                if code_url:
                    logger.info(f"微信统一下单成功: {pay_no}, code_url={code_url[:50]}...")
                    return code_url
                else:
                    logger.error(f"微信下单响应缺少code_url: {result}")
            else:
                logger.error(f"微信下单失败: {response.status_code}, {response.text}")

            return f"weixin://wxpay/bizpayurl?pr={pay_no}"

        except Exception as e:
            logger.error(f"微信支付下单异常: {e}")
            return f"weixin://wxpay/bizpayurl?pr={pay_no}"

    @staticmethod
    def _wechat_sign(message, private_key):
        """微信支付RSA2签名"""
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend

            key = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend()
            )

            signature = key.sign(
                message.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            import base64
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            logger.error(f"微信签名失败: {e}")
            return ''

    # ============ V29.0 新增: 微信支付查询 ============

    @classmethod
    def query_wechat_order(cls, pay_no):
        """
        查询微信支付订单状态

        Args:
            pay_no: 支付单号

        Returns:
            dict: 查询结果
        """
        if not cls.is_wechat_configured():
            return {'success': False, 'msg': '微信支付未配置'}

        pay_record = db.get_one(
            "SELECT * FROM business_payments WHERE pay_no=%s",
            [pay_no]
        )
        if not pay_record:
            return {'success': False, 'msg': '支付单不存在'}

        if pay_record.get('channel') != 'wechat':
            return {'success': False, 'msg': '非微信支付订单'}

        try:
            config = cls.WECHAT_CONFIG
            mch_id = config['mch_id']

            timestamp = str(int(time.time()))
            nonce_str = uuid.uuid4().hex[:32]

            # 查询请求
            method = 'GET'
            url_path = f'/v3/pay/transactions/out-trade-no/{pay_no}?mchid={mch_id}'
            message = f'{method}\n{url_path}\n{timestamp}\n{nonce_str}\n\n'
            signature = cls._wechat_sign(message, config['private_key'])

            headers = {
                'Accept': 'application/json',
                'Authorization': f'WECHATPAY2-SHA256-RSA2048 mchid="{mch_id}",nonce_str="{nonce_str}",timestamp="{timestamp}",signature="{signature}",serial_no="{config["serial_no"]}"'
            }

            response = requests.get(
                f"{cls.WECHAT_API_BASE}{url_path}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                trade_state = result.get('trade_state', 'UNKNOWN')

                # 同步状态到本地
                status_map = {
                    'SUCCESS': 'paid',
                    'REFUND': 'refunded',
                    'NOTPAY': 'pending',
                    'CLOSED': 'closed',
                    'PAYERROR': 'failed',
                }
                local_status = status_map.get(trade_state, pay_record.get('status'))

                if local_status != pay_record.get('status'):
                    db.execute(
                        "UPDATE business_payments SET status=%s, paid_at=NOW() WHERE pay_no=%s AND status='pending'",
                        [local_status, pay_no]
                    )
                    logger.info(f"微信订单状态同步: {pay_no} -> {local_status}")

                return {
                    'success': True,
                    'data': {
                        'pay_no': pay_no,
                        'trade_state': trade_state,
                        'trade_state_desc': result.get('trade_state_desc', ''),
                        'amount': result.get('amount', {}).get('total', 0) / 100,
                        'transaction_id': result.get('transaction_id', ''),
                        'success_time': result.get('success_time', ''),
                        'payer': result.get('payer', {}).get('openid', ''),
                    }
                }
            elif response.status_code == 404:
                return {'success': True, 'data': {'pay_no': pay_no, 'trade_state': 'NOTFOUND'}}
            else:
                logger.error(f"微信订单查询失败: {response.status_code}, {response.text}")
                return {'success': False, 'msg': f'查询失败: {response.status_code}'}

        except Exception as e:
            logger.error(f"微信订单查询异常: {e}")
            return {'success': False, 'msg': f'查询异常: {e}'}

    # ============ V29.0 新增: 微信退款 ============

    @classmethod
    def wechat_refund(cls, pay_no, refund_amount, reason=''):
        """
        微信支付退款

        Args:
            pay_no: 支付单号
            refund_amount: 退款金额
            reason: 退款原因

        Returns:
            dict: 退款结果
        """
        if not cls.is_wechat_configured():
            return {'success': False, 'msg': '微信支付未配置'}

        pay_record = db.get_one(
            "SELECT * FROM business_payments WHERE pay_no=%s AND status='paid'",
            [pay_no]
        )
        if not pay_record:
            return {'success': False, 'msg': '支付单不存在或未支付'}

        if float(refund_amount) > float(pay_record.get('amount', 0)):
            return {'success': False, 'msg': '退款金额超出支付金额'}

        try:
            config = cls.WECHAT_CONFIG
            mch_id = config['mch_id']

            timestamp = str(int(time.time()))
            nonce_str = uuid.uuid4().hex[:32]
            out_refund_no = f"REF{pay_no[3:]}"

            # 退款请求体
            body = {
                'out_trade_no': pay_no,
                'out_refund_no': out_refund_no,
                'reason': reason or '用户申请退款',
                'notify_url': f"{config.get('notify_url', '')}/refund",
                'amount': {
                    'refund': int(float(refund_amount) * 100),
                    'total': int(float(pay_record['amount']) * 100),
                    'currency': 'CNY'
                }
            }

            method = 'POST'
            url_path = '/v3/refund/domestic/refunds'
            message = f'{method}\n{url_path}\n{timestamp}\n{nonce_str}\n{json.dumps(body)}\n'
            signature = cls._wechat_sign(message, config['private_key'])

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'WECHATPAY2-SHA256-RSA2048 mchid="{mch_id}",nonce_str="{nonce_str}",timestamp="{timestamp}",signature="{signature}",serial_no="{config["serial_no"]}"'
            }

            response = requests.post(
                f"{cls.WECHAT_API_BASE}{url_path}",
                data=json.dumps(body),
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                refund_id = result.get('refund_id', out_refund_no)

                # 更新本地状态
                db.execute(
                    """UPDATE business_payments
                       SET status='refunded', refund_reason=%s, refunded_at=NOW()
                       WHERE pay_no=%s""",
                    [reason or '微信退款', pay_no]
                )

                # V29.0: 退款日志
                cls._log_payment_action(pay_no, 'refund', {
                    'refund_no': refund_id,
                    'refund_amount': refund_amount,
                    'reason': reason,
                })

                logger.info(f"微信退款成功: {pay_no}, refund_id={refund_id}")
                return {'success': True, 'data': {'refund_id': refund_id}}

            else:
                logger.error(f"微信退款失败: {response.status_code}, {response.text}")
                return {'success': False, 'msg': f'退款失败: {response.status_code}'}

        except Exception as e:
            logger.error(f"微信退款异常: {e}")
            return {'success': False, 'msg': f'退款异常: {e}'}

    # ============ 支付宝支付 ============

    @staticmethod
    def _create_alipay_pay_url(pay_no, amount, **kwargs):
        """
        生成支付宝支付URL
        """
        if not PaymentService.is_alipay_configured():
            logger.warning("支付宝未配置，返回Mock URL")
            return f"alipays://platformapi/startapp?appId=20000067&payNo={pay_no}"

        try:
            config = PaymentService.ALIPAY_CONFIG
            app_id = config['app_id']

            biz_content = {
                'out_trade_no': pay_no,
                'total_amount': float(amount),
                'subject': f'社区商业订单-{pay_no[:20]}',
                'product_code': 'FAST_INSTANT_TRADE',
                'timeout_express': '30m'
            }

            params = {
                'app_id': app_id,
                'method': 'alipay.trade.page.pay',
                'format': 'JSON',
                'charset': 'utf-8',
                'sign_type': 'RSA2',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': '1.0',
                'notify_url': config.get('notify_url') or '',
                'return_url': kwargs.get('return_url', ''),
                'biz_content': json.dumps(biz_content, ensure_ascii=False)
            }

            sign = PaymentService._alipay_sign(params, config['private_key'])
            params['sign'] = sign

            from urllib.parse import urlencode
            gateway = config.get('gateway', 'https://openapi.alipay.com/gateway.do')
            pay_url = f"{gateway}?{urlencode(params)}"

            logger.info(f"支付宝下单成功: {pay_no}, amount={amount}")
            return pay_url

        except Exception as e:
            logger.error(f"支付宝下单异常: {e}")
            return f"alipays://platformapi/startapp?appId=20000067&payNo={pay_no}"

    @staticmethod
    def _alipay_sign(params, private_key):
        """支付宝RSA2签名"""
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend

            sorted_params = sorted([(k, v) for k, v in params.items() if v])
            sign_str = '&'.join([f'{k}={v}' for k, v in sorted_params])

            key = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend()
            )

            signature = key.sign(
                sign_str.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            import base64
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            logger.error(f"支付宝签名失败: {e}")
            return ''

    # ============ V29.0 新增: 支付宝查询 ============

    @classmethod
    def query_alipay_order(cls, pay_no):
        """
        查询支付宝订单状态

        Args:
            pay_no: 支付单号

        Returns:
            dict: 查询结果
        """
        if not cls.is_alipay_configured():
            return {'success': False, 'msg': '支付宝未配置'}

        pay_record = db.get_one(
            "SELECT * FROM business_payments WHERE pay_no=%s",
            [pay_no]
        )
        if not pay_record:
            return {'success': False, 'msg': '支付单不存在'}

        if pay_record.get('channel') != 'alipay':
            return {'success': False, 'msg': '非支付宝订单'}

        try:
            config = cls.ALIPAY_CONFIG
            app_id = config['app_id']

            biz_content = {
                'out_trade_no': pay_no,
            }

            params = {
                'app_id': app_id,
                'method': 'alipay.trade.query',
                'format': 'JSON',
                'charset': 'utf-8',
                'sign_type': 'RSA2',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': '1.0',
                'biz_content': json.dumps(biz_content, ensure_ascii=False)
            }

            params['sign'] = cls._alipay_sign(params, config['private_key'])

            from urllib.parse import urlencode
            query_url = f"{config.get('gateway')}?{urlencode(params)}"

            response = requests.get(query_url, timeout=10)
            result = response.json()

            if result.get('alipay_trade_query_response'):
                resp = result['alipay_trade_query_response']

                if resp.get('code') == '10000':  # 成功
                    trade_status = resp.get('trade_status', '')

                    status_map = {
                        'WAIT_BUYER_PAY': 'pending',
                        'TRADE_CLOSED': 'closed',
                        'TRADE_SUCCESS': 'paid',
                        'TRADE_FINISHED': 'paid',
                    }
                    local_status = status_map.get(trade_status, pay_record.get('status'))

                    # 同步状态
                    if local_status == 'paid' and pay_record.get('status') == 'pending':
                        db.execute(
                            "UPDATE business_payments SET status='paid', paid_at=NOW() WHERE pay_no=%s",
                            [pay_no]
                        )
                        cls._log_payment_action(pay_no, 'sync', {'source': 'alipay', 'status': trade_status})

                    return {
                        'success': True,
                        'data': {
                            'pay_no': pay_no,
                            'trade_status': trade_status,
                            'amount': resp.get('total_amount', 0),
                            'trade_no': resp.get('trade_no', ''),
                            'buyer_logon_id': resp.get('buyer_logon_id', ''),
                        }
                    }
                else:
                    return {'success': False, 'msg': resp.get('msg', '查询失败')}

            return {'success': False, 'msg': '响应格式错误'}

        except Exception as e:
            logger.error(f"支付宝订单查询异常: {e}")
            return {'success': False, 'msg': f'查询异常: {e}'}

    # ============ V29.0 新增: 支付宝退款 ============

    @classmethod
    def alipay_refund(cls, pay_no, refund_amount, reason=''):
        """
        支付宝退款

        Args:
            pay_no: 支付单号
            refund_amount: 退款金额
            reason: 退款原因

        Returns:
            dict: 退款结果
        """
        if not cls.is_alipay_configured():
            return {'success': False, 'msg': '支付宝未配置'}

        pay_record = db.get_one(
            "SELECT * FROM business_payments WHERE pay_no=%s AND status='paid'",
            [pay_no]
        )
        if not pay_record:
            return {'success': False, 'msg': '支付单不存在或未支付'}

        if float(refund_amount) > float(pay_record.get('amount', 0)):
            return {'success': False, 'msg': '退款金额超出支付金额'}

        try:
            config = cls.ALIPAY_CONFIG
            app_id = config['app_id']
            out_request_no = f"REF{pay_no[3:]}{int(time.time())}"

            biz_content = {
                'trade_no': pay_record.get('transaction_id', ''),  # 支付宝交易号
                'out_trade_no': pay_no,
                'refund_amount': float(refund_amount),
                'refund_reason': reason or '用户申请退款',
                'out_request_no': out_request_no,
            }

            params = {
                'app_id': app_id,
                'method': 'alipay.trade.refund',
                'format': 'JSON',
                'charset': 'utf-8',
                'sign_type': 'RSA2',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': '1.0',
                'biz_content': json.dumps(biz_content, ensure_ascii=False)
            }

            params['sign'] = cls._alipay_sign(params, config['private_key'])

            from urllib.parse import urlencode
            refund_url = f"{config.get('gateway')}?{urlencode(params)}"

            response = requests.post(refund_url, timeout=10)
            result = response.json()

            if result.get('alipay_trade_refund_response'):
                resp = result['alipay_trade_refund_response']

                if resp.get('code') == '10000':
                    db.execute(
                        """UPDATE business_payments
                           SET status='refunded', refund_reason=%s, refunded_at=NOW()
                           WHERE pay_no=%s""",
                        [reason or '支付宝退款', pay_no]
                    )

                    cls._log_payment_action(pay_no, 'refund', {
                        'refund_no': out_request_no,
                        'refund_amount': refund_amount,
                        'reason': reason,
                    })

                    logger.info(f"支付宝退款成功: {pay_no}")
                    return {'success': True, 'data': {'refund_no': out_request_no}}
                else:
                    return {'success': False, 'msg': resp.get('msg', '退款失败')}

            return {'success': False, 'msg': '响应格式错误'}

        except Exception as e:
            logger.error(f"支付宝退款异常: {e}")
            return {'success': False, 'msg': f'退款异常: {e}'}

    # ============ 支付回调验签 ============

    @staticmethod
    def verify_wechat_callback(data, wechat_signature=None, wechat_timestamp=None, wechat_nonce=None):
        """
        验证微信支付回调签名并解密
        """
        try:
            import json as json_mod

            resource = data.get('resource', {})
            if not resource:
                return {'success': False, 'msg': '无效的回调数据'}

            if not PaymentService.is_wechat_configured():
                return {'success': False, 'msg': '微信支付未配置'}

            api_v3_key = PaymentService.WECHAT_CONFIG.get('api_v3_key', '')
            if not api_v3_key:
                return {'success': False, 'msg': '微信API V3密钥未配置'}

            # AES-GCM解密
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                import base64

                nonce = resource.get('nonce', '')
                ciphertext = resource.get('ciphertext', '')
                associated_data = resource.get('associated_data', '')

                key = base64.b64decode(api_v3_key)
                nonce_bytes = nonce.encode()
                ciphertext_bytes = base64.b64decode(ciphertext)
                associated_data_bytes = associated_data.encode() if associated_data else b''

                aesgcm = AESGCM(key)
                decrypted = aesgcm.decrypt(
                    nonce=nonce_bytes,
                    data=ciphertext_bytes,
                    associated_data=associated_data_bytes
                )
                decrypted_data = json_mod.loads(decrypted.decode('utf-8'))

                logger.info(f"微信支付回调解密成功: out_trade_no={decrypted_data.get('out_trade_no')}")
                return {'success': True, 'data': decrypted_data}

            except Exception as e:
                logger.error(f"微信回调解密失败: {e}")
                return {'success': False, 'msg': f'解密失败: {e}'}

        except Exception as e:
            logger.error(f"微信回调验证异常: {e}")
            return {'success': False, 'msg': f'验证失败: {e}'}

    @staticmethod
    def verify_alipay_callback(params, sign):
        """
        验证支付宝异步通知签名
        """
        try:
            if not sign:
                return {'success': False, 'msg': '缺少签名'}

            if not PaymentService.is_alipay_configured():
                return {'success': False, 'msg': '支付宝未配置'}

            alipay_public_key = PaymentService.ALIPAY_CONFIG.get('alipay_public_key', '')
            if not alipay_public_key:
                return {'success': False, 'msg': '支付宝公钥未配置'}

            sign_type = params.get('sign_type', 'RSA2')
            verify_params = {k: v for k, v in params.items() if k not in ('sign', 'sign_type')}
            sorted_params = sorted(verify_params.items())
            sign_str = '&'.join([f'{k}={v}' for k, v in sorted_params])

            try:
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import padding
                from cryptography.hazmat.backends import default_backend
                import base64

                pub_key = serialization.load_pem_bytes(
                    alipay_public_key.encode(),
                    default_backend()
                )

                signature = base64.b64decode(sign)

                pub_key.verify(
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                    sign_str.encode('utf-8'),
                    signature
                )

                logger.info("支付宝验签成功")
                return {'success': True, 'data': params}

            except Exception as e:
                logger.error(f"支付宝验签失败: {e}")
                return {'success': False, 'msg': f'签名验证失败: {e}'}

        except Exception as e:
            logger.error(f"支付宝回调验证异常: {e}")
            return {'success': False, 'msg': f'验证失败: {e}'}

    # ============ V29.0 新增: 统一回调处理 ============

    @classmethod
    def handle_payment_callback(cls, channel, callback_data, **kwargs):
        """
        统一处理支付回调

        Args:
            channel: 支付渠道 (wechat/alipay)
            callback_data: 回调数据

        Returns:
            dict: 处理结果
        """
        if channel == 'wechat':
            # 微信回调
            if kwargs.get('wechat_signature'):
                result = cls.verify_wechat_callback(
                    callback_data,
                    kwargs.get('wechat_signature'),
                    kwargs.get('wechat_timestamp'),
                    kwargs.get('wechat_nonce')
                )
            else:
                result = cls.verify_wechat_callback(callback_data)

            if not result.get('success'):
                return result

            data = result.get('data', {})
            pay_no = data.get('out_trade_no', '')
            trade_status = data.get('trade_state', '')

            if trade_status == 'SUCCESS':
                return cls._process_payment_success(pay_no, 'wechat', data.get('transaction_id', ''))

        elif channel == 'alipay':
            # 支付宝回调
            sign = callback_data.get('sign', '')
            result = cls.verify_alipay_callback(callback_data, sign)

            if not result.get('success'):
                return result

            pay_no = callback_data.get('out_trade_no', '')
            trade_status = callback_data.get('trade_status', '')

            if trade_status in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
                return cls._process_payment_success(pay_no, 'alipay', callback_data.get('trade_no', ''))

        return {'success': False, 'msg': '不支持的支付渠道'}

    @classmethod
    def _process_payment_success(cls, pay_no, channel, transaction_id=''):
        """
        处理支付成功

        Args:
            pay_no: 支付单号
            channel: 支付渠道
            transaction_id: 第三方交易号

        Returns:
            dict: 处理结果
        """
        try:
            pay_record = db.get_one(
                "SELECT * FROM business_payments WHERE pay_no=%s",
                [pay_no]
            )

            if not pay_record:
                return {'success': False, 'msg': '支付单不存在'}

            if pay_record['status'] == 'paid':
                return {'success': True, 'msg': '已处理'}

            conn = db.get_db()
            cursor = conn.cursor()
            conn.begin()

            try:
                cursor.execute(
                    """UPDATE business_payments
                       SET status='paid', paid_at=NOW(), channel=%s
                       WHERE pay_no=%s AND status='pending'""",
                    [channel, pay_no]
                )

                if cursor.rowcount > 0:
                    # 更新交易号
                    if transaction_id:
                        cursor.execute(
                            "UPDATE business_payments SET transaction_id=%s WHERE pay_no=%s",
                            [transaction_id, pay_no]
                        )

                    order_type = pay_record['order_type']
                    order_id = pay_record['order_id']

                    if order_type == 'booking':
                        cursor.execute(
                            """UPDATE business_venue_bookings
                               SET pay_status='paid', status='confirmed', updated_at=NOW()
                               WHERE id=%s""",
                            [order_id]
                        )
                    elif order_type == 'order':
                        cursor.execute(
                            """UPDATE business_orders
                               SET pay_status='paid', order_status='paid', updated_at=NOW()
                               WHERE id=%s""",
                            [order_id]
                        )

                    conn.commit()

                    # 触发后置处理
                    _post_payment_hooks(pay_record, pay_no)

                    # V29.0: 支付日志
                    cls._log_payment_action(pay_no, 'callback_success', {
                        'channel': channel,
                        'transaction_id': transaction_id,
                    })

                    logger.info(f"支付回调处理成功: {pay_no}")
                    return {'success': True, 'msg': '处理成功'}

                conn.commit()
                return {'success': True, 'msg': '已处理'}

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            logger.error(f"支付成功处理异常: {e}")
            return {'success': False, 'msg': f'处理异常: {e}'}

    # ============ 模拟支付确认 ============

    @staticmethod
    def confirm_payment(pay_no, channel='mock'):
        """确认支付（模拟/回调）"""
        try:
            pay_record = db.get_one(
                "SELECT * FROM business_payments WHERE pay_no=%s AND status='pending'",
                [pay_no]
            )
            if not pay_record:
                return {'success': False, 'msg': '支付单不存在或已处理'}

            if pay_record.get('expire_at') and pay_record['expire_at'] < datetime.now():
                db.execute("UPDATE business_payments SET status='expired' WHERE pay_no=%s", [pay_no])
                return {'success': False, 'msg': '支付单已过期'}

            conn = db.get_db()
            cursor = conn.cursor()
            conn.begin()

            try:
                cursor.execute(
                    """UPDATE business_payments
                       SET status='paid', paid_at=NOW(), channel=%s
                       WHERE pay_no=%s AND status='pending'""",
                    [channel, pay_no]
                )

                if cursor.rowcount == 0:
                    conn.rollback()
                    return {'success': False, 'msg': '支付单已被处理'}

                order_type = pay_record['order_type']
                order_id = pay_record['order_id']

                if order_type == 'booking':
                    cursor.execute(
                        """UPDATE business_venue_bookings
                           SET pay_status='paid', status='confirmed', updated_at=NOW()
                           WHERE id=%s""",
                        [order_id]
                    )
                elif order_type == 'order':
                    cursor.execute(
                        """UPDATE business_orders
                           SET pay_status='paid', order_status='paid', updated_at=NOW()
                           WHERE id=%s""",
                        [order_id]
                    )

                conn.commit()

                # 触发后置处理
                _post_payment_hooks(pay_record, pay_no)

                logger.info(f"支付确认成功: {pay_no}")
                return {'success': True, 'msg': '支付成功', 'data': {'pay_no': pay_no, 'status': 'paid'}}

            except Exception as e:
                conn.rollback()
                logger.error(f"支付确认事务失败: {e}")
                return {'success': False, 'msg': '支付处理失败'}
            finally:
                try:
                    cursor.close()
                    conn.close()
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"支付确认失败: {e}")
            return {'success': False, 'msg': '支付确认失败'}

    # ============ 退款处理 ============

    @staticmethod
    def refund(pay_no, reason=''):
        """
        退款（统一入口，根据渠道分发）

        Args:
            pay_no: 支付单号
            reason: 退款原因

        Returns:
            dict: 退款结果
        """
        pay_record = db.get_one(
            "SELECT * FROM business_payments WHERE pay_no=%s AND status='paid'",
            [pay_no]
        )
        if not pay_record:
            return {'success': False, 'msg': '支付单不存在或未支付'}

        channel = pay_record.get('channel', 'mock')
        refund_amount = pay_record.get('amount', 0)

        if channel == 'wechat':
            return PaymentService.wechat_refund(pay_no, refund_amount, reason)
        elif channel == 'alipay':
            return PaymentService.alipay_refund(pay_no, refund_amount, reason)
        else:
            # 模拟退款
            return PaymentService._mock_refund(pay_no, reason)

    @staticmethod
    def _mock_refund(pay_no, reason=''):
        """模拟退款"""
        try:
            conn = db.get_db()
            cursor = conn.cursor()
            conn.begin()

            try:
                cursor.execute(
                    """UPDATE business_payments
                       SET status='refunded', refund_reason=%s, refunded_at=NOW()
                       WHERE pay_no=%s""",
                    [reason or '模拟退款', pay_no]
                )

                order_type = db.get_one("SELECT order_type, order_id FROM business_payments WHERE pay_no=%s", [pay_no])

                if order_type:
                    if order_type['order_type'] == 'booking':
                        cursor.execute(
                            """UPDATE business_venue_bookings
                               SET pay_status='refund', status='cancelled', updated_at=NOW()
                               WHERE id=%s""",
                            [order_type['order_id']]
                        )
                    elif order_type['order_type'] == 'order':
                        cursor.execute(
                            """UPDATE business_orders
                               SET pay_status='refund', order_status='cancelled', updated_at=NOW()
                               WHERE id=%s""",
                            [order_type['order_id']]
                        )

                conn.commit()
                logger.info(f"模拟退款成功: {pay_no}")
                return {'success': True, 'msg': '退款成功'}

            except Exception as e:
                conn.rollback()
                return {'success': False, 'msg': '退款处理失败'}
            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            logger.error(f"退款失败: {e}")
            return {'success': False, 'msg': '退款失败'}

    # ============ 支付状态查询 ============

    @staticmethod
    def get_payment_status(pay_no):
        """查询支付状态"""
        pay = db.get_one(
            """SELECT pay_no, order_type, order_id, amount, status, channel,
                      created_at, paid_at, transaction_id
               FROM business_payments WHERE pay_no=%s""",
            [pay_no]
        )
        if not pay:
            return {'success': False, 'msg': '支付单不存在'}
        return {'success': True, 'data': pay}

    # ============ V29.0 新增: 外部支付查询 ============

    @staticmethod
    def query_external_payment(pay_no):
        """
        查询外部支付渠道的实际支付状态

        Args:
            pay_no: 支付单号

        Returns:
            dict: 支付状态查询结果
        """
        pay_record = db.get_one(
            "SELECT * FROM business_payments WHERE pay_no=%s",
            [pay_no]
        )
        if not pay_record:
            return {'success': False, 'msg': '支付单不存在'}

        channel = pay_record.get('channel', 'mock')

        if channel == 'mock':
            return {
                'success': True,
                'data': {
                    'pay_no': pay_no,
                    'status': pay_record.get('status'),
                    'channel': 'mock',
                    'message': '模拟支付，直接查库'
                }
            }
        elif channel == 'wechat':
            return PaymentService.query_wechat_order(pay_no)
        elif channel == 'alipay':
            return PaymentService.query_alipay_order(pay_no)

        return {'success': False, 'msg': f'不支持的支付渠道: {channel}'}

    # ============ 过期支付取消 ============

    @staticmethod
    def cancel_expired_payments():
        """取消过期的待支付订单（定时任务调用）"""
        try:
            count = db.execute(
                """UPDATE business_payments
                   SET status='expired'
                   WHERE status='pending' AND expire_at < NOW()"""
            )
            if count > 0:
                logger.info(f"已取消 {count} 笔过期支付单")

                expired_payments = db.get_all(
                    "SELECT id, order_type, order_id FROM business_payments WHERE status='expired' AND order_type='order'"
                )
                for p in (expired_payments or []):
                    try:
                        db.execute(
                            """UPDATE business_orders
                               SET order_status='cancelled', updated_at=NOW()
                               WHERE id=%s AND order_status='pending'""",
                            [p['order_id']]
                        )
                    except Exception:
                        pass

            return count
        except Exception as e:
            logger.error(f"取消过期支付单失败: {e}")
            return 0

    # ============ V29.0 新增: 支付日志 ============

    @staticmethod
    def _log_payment_action(pay_no, action, detail=None):
        """
        记录支付操作日志

        Args:
            pay_no: 支付单号
            action: 操作类型 (create/refund/callback_success/query)
            detail: 详细信息
        """
        try:
            db.execute("""
                INSERT INTO business_payment_logs (pay_no, action, detail, created_at)
                VALUES (%s, %s, %s, NOW())
            """, [pay_no, action, json.dumps(detail or {}, ensure_ascii=False)])
        except Exception as e:
            logger.warning(f"支付日志记录失败: {e}")

    @classmethod
    def get_payment_logs(cls, pay_no):
        """获取支付日志"""
        try:
            logs = db.get_all(
                """SELECT action, detail, created_at
                   FROM business_payment_logs
                   WHERE pay_no=%s ORDER BY created_at ASC""",
                [pay_no]
            )
            return {'success': True, 'data': logs or []}
        except Exception as e:
            logger.error(f"获取支付日志失败: {e}")
            return {'success': False, 'msg': '获取日志失败'}


def _post_payment_hooks(pay_record, pay_no):
    """
    V18.0 支付后处理钩子 - 统一触发：
    1. 发送支付成功通知
    2. WebSocket实时推送
    3. 发放积分（基于等级倍率）
    4. 更新累计消费并触发会员等级升级
    """
    user_id = pay_record['user_id']
    amount = float(pay_record.get('amount', 0))
    ec_id = pay_record.get('ec_id')
    project_id = pay_record.get('project_id')

    # 1. 站内通知
    try:
        from .notification import send_notification
        send_notification(
            user_id,
            '支付成功',
            f"您的支付单 {pay_no} 已支付成功，金额: ¥{amount:.2f}",
            notify_type='order',
            ref_id=pay_no,
            ref_type='payment',
            ec_id=ec_id,
            project_id=project_id
        )
    except Exception as e:
        logger.warning(f"支付成功通知发送失败: {e}")

    # 2. WebSocket 实时推送
    try:
        from .websocket_service import push_notification
        push_notification(
            user_id,
            '支付成功',
            f"支付单 {pay_no} 金额 ¥{amount:.2f}",
            notify_type='order'
        )
    except Exception as e:
        logger.warning(f"WebSocket推送失败: {e}")

    # 3. 积分发放
    if pay_record.get('order_type') == 'order' and amount > 0:
        try:
            from .member_level import MemberLevelService
            points_earned, points_rate = MemberLevelService.calculate_points(user_id, amount)
            if points_earned > 0:
                db.execute(
                    """UPDATE business_members
                       SET points = points + %s, total_points = total_points + %s
                       WHERE user_id = %s""",
                    [points_earned, points_earned, user_id]
                )
                db.execute(
                    """INSERT INTO business_points_log
                       (user_id, log_type, points, balance_after, description, ec_id, project_id)
                       SELECT %s, 'earn', %s, points, %s, %s, %s
                       FROM business_members WHERE user_id=%s""",
                    [user_id, points_earned,
                     f'订单支付获得积分（×{points_rate:.1f}倍率）',
                     ec_id, project_id, user_id]
                )
                logger.info(f"积分发放: user={user_id}, points={points_earned}, rate={points_rate}")
        except Exception as e:
            logger.warning(f"积分发放失败: {e}")

    # 4. 更新累计消费 + 会员等级自动升级
    if amount > 0:
        try:
            from .member_level import MemberLevelService
            result = MemberLevelService.update_total_consume(user_id, amount, ec_id, project_id)
            if result.get('upgraded'):
                logger.info(
                    f"会员升级触发: user={user_id}, "
                    f"{result['old_level']} -> {result['new_level']}, "
                    f"累计消费={result['total_consume']}"
                )
        except Exception as e:
            logger.warning(f"会员升级检查失败: {e}")


# 便捷实例
payment = PaymentService()
