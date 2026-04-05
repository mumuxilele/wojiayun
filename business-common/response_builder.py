"""
统一错误码与响应构建器 V23.0
建立标准化的错误码体系，统一API响应格式，便于前端统一处理。

错误码分段:
  10000-10999: 通用错误（参数、认证、权限、限流）
  11000-11999: 用户端业务错误（订单、支付、购物车、评价）
  12000-12999: 积分与会员相关错误
  13000-13999: 营销活动相关错误
  20000-20999: 员工端业务错误
  30000-30999: 管理端业务错误
"""
import logging
from flask import jsonify

logger = logging.getLogger(__name__)


# ============ 错误码定义 ============

class ErrorCode:
    """统一错误码"""

    # 通用错误 10xxx
    SUCCESS = (0, '成功')
    PARAM_MISSING = (10001, '缺少必要参数')
    PARAM_INVALID = (10002, '参数格式不正确')
    AUTH_REQUIRED = (10003, '请先登录')
    AUTH_EXPIRED = (10004, '登录已过期，请重新登录')
    PERMISSION_DENIED = (10005, '无权访问')
    RATE_LIMITED = (10006, '操作过于频繁，请稍后重试')
    NOT_FOUND = (10007, '资源不存在')
    SERVER_ERROR = (10008, '服务器内部错误')
    DATA_CONFLICT = (10009, '数据冲突')
    OPERATION_FAILED = (10010, '操作失败，请稍后重试')
    CONTENT_UNSAFE = (10011, '内容包含违规信息')

    # 用户端业务 11xxx
    ORDER_NOT_FOUND = (11001, '订单不存在')
    ORDER_STATUS_INVALID = (11002, '订单状态不允许此操作')
    ORDER_CANCELLED = (11003, '订单已取消')
    ORDER_PAID = (11004, '订单已支付')
    STOCK_NOT_ENOUGH = (11005, '库存不足')
    PRODUCT_OFF_SHELF = (11006, '商品已下架')
    CART_EMPTY = (11007, '购物车为空')
    COUPON_INVALID = (11008, '优惠券无效')
    COUPON_USED = (11009, '优惠券已使用')
    COUPON_EXPIRED = (11010, '优惠券已过期')
    REVIEW_DUPLICATED = (11011, '已评价，不能重复评价')
    ADDRESS_NOT_FOUND = (11012, '地址不存在')
    BOOKING_CONFLICT = (11013, '该时段已被预约')
    BOOKING_NOT_FOUND = (11014, '预约不存在')
    AMOUNT_MISMATCH = (11015, '金额校验失败')

    # 积分与会员 12xxx
    POINTS_NOT_ENOUGH = (12001, '积分不足')
    MEMBER_NOT_FOUND = (12002, '会员不存在')
    EXCHANGE_LIMIT = (12003, '超出兑换限制')
    EXCHANGE_GOODS_UNAVAILABLE = (12004, '兑换商品不可用')

    # 营销活动 13xxx
    SECKILL_NOT_STARTED = (13001, '活动未开始')
    SECKILL_ENDED = (13002, '活动已结束')
    SECKILL_SOLD_OUT = (13003, '已抢光')
    SECKILL_LIMIT = (13004, '超出限购数量')

    # 员工端 20xxx
    APPLICATION_NOT_FOUND = (20001, '申请单不存在')
    REFUND_INVALID = (20002, '退款状态异常')

    # 管理端 30xxx
    ADMIN_AUTH_REQUIRED = (30001, '请使用管理员账号登录')


class ResponseBuilder:
    """统一响应构建器"""

    @staticmethod
    def success(data=None, msg='操作成功'):
        """成功响应"""
        return jsonify({
            'success': True,
            'code': 0,
            'msg': msg,
            'data': data
        })

    @staticmethod
    def error(error_code, msg=None, data=None):
        """错误响应"""
        if isinstance(error_code, tuple):
            code, default_msg = error_code
            msg = msg or default_msg
        else:
            code = error_code
            msg = msg or '操作失败'

        response = {
            'success': False,
            'code': code,
            'msg': msg,
        }
        if data is not None:
            response['data'] = data

        return jsonify(response)

    @staticmethod
    def paginated(items, total, page, page_size):
        """分页响应"""
        return jsonify({
            'success': True,
            'code': 0,
            'data': {
                'items': items or [],
                'total': total,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size if total else 0
            }
        })

    @staticmethod
    def server_error(msg='服务器内部错误'):
        """服务器错误"""
        logger.error(f"Server error: {msg}")
        return jsonify({
            'success': False,
            'code': ErrorCode.SERVER_ERROR[0],
            'msg': msg,
        })


def success_resp(data=None, msg='操作成功'):
    """快捷成功响应"""
    return ResponseBuilder.success(data, msg)


def error_resp(error_code, msg=None, data=None):
    """快捷错误响应"""
    return ResponseBuilder.error(error_code, msg, data)


def paginated_resp(items, total, page, page_size):
    """快捷分页响应"""
    return ResponseBuilder.paginated(items, total, page, page_size)
