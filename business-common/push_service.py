"""
消息推送中心 V32.0
功能:
  - 统一推送渠道管理（站内信/短信/微信模板消息/邮件）
  - 消息模板管理
  - 定时/触发推送
  - 推送记录与统计
"""
import logging
import json
import re
import os
from datetime import datetime, timedelta
from urllib import request as urllib_request
from urllib import error as urllib_error

from . import db
from .user_settings_service import user_settings_service


logger = logging.getLogger(__name__)


class PushService:
    """统一消息推送服务"""

    # 推送渠道
    CHANNELS = {
        'in_app': '站内信',
        'sms': '短信',
        'wechat': '微信模板消息',
        'email': '邮件'
    }

    # 消息类型
    MSG_TYPES = {
        'order': '订单通知',
        'payment': '支付通知',
        'refund': '退款通知',
        'delivery': '配送通知',
        'marketing': '营销通知',
        'system': '系统通知',
        'activity': '活动通知'
    }

    # 默认模板
    DEFAULT_TEMPLATES = {
        'order_created': {
            'title': '订单已创建',
            'content': '您的订单 {order_no} 已创建，金额 {amount} 元',
            'channels': ['in_app'],
            'msg_type': 'order'
        },
        'order_paid': {
            'title': '支付成功',
            'content': '您的订单 {order_no} 已支付成功，金额 {amount} 元',
            'channels': ['in_app', 'wechat'],
            'msg_type': 'payment'
        },
        'order_shipped': {
            'title': '订单已发货',
            'content': '您的订单 {order_no} 已发货，快递 {express_name}，单号 {tracking_no}',
            'channels': ['in_app', 'wechat'],
            'msg_type': 'delivery'
        },
        'order_delivered': {
            'title': '订单已送达',
            'content': '您的订单 {order_no} 已送达，请确认收货',
            'channels': ['in_app'],
            'msg_type': 'delivery'
        },
        'refund_approved': {
            'title': '退款已处理',
            'content': '您的退款申请已通过，金额 {amount} 元将退还至您的账户',
            'channels': ['in_app', 'wechat'],
            'msg_type': 'refund'
        },
        'reminder': {
            'title': '待处理提醒',
            'content': '{content}',
            'channels': ['in_app'],
            'msg_type': 'system'
        },
        'promotion': {
            'title': '{title}',
            'content': '{content}',
            'channels': ['in_app'],
            'msg_type': 'marketing'
        }
    }

    @classmethod
    def get_templates(cls, ec_id=None, project_id=None):
        """获取消息模板列表"""
        try:
            where = "deleted=0"
            params = []

            if ec_id:
                where += " AND (ec_id=%s OR ec_id IS NULL)"
                params.append(ec_id)
            if project_id:
                where += " AND (project_id=%s OR project_id IS NULL)"
                params.append(project_id)

            templates = db.get_all(f"""
                SELECT id, template_code, template_name, title_template,
                       content_template, channels, msg_type, status,
                       created_at, updated_at
                FROM business_push_templates
                WHERE {where}
                ORDER BY id DESC
            """, params)

            # 解析channels字段
            for t in (templates or []):
                if t.get('channels'):
                    try:
                        t['channels'] = json.loads(t['channels']) if isinstance(t['channels'], str) else t['channels']
                    except:
                        t['channels'] = []
                else:
                    t['channels'] = []

            return templates or []

        except Exception as e:
            logger.error(f"获取推送模板失败: {e}")
            return []

    @classmethod
    def get_template(cls, template_code, ec_id=None, project_id=None):
        """获取指定模板"""
        try:
            sql = """
                SELECT * FROM business_push_templates
                WHERE template_code=%s AND deleted=0 AND status='active'
            """
            params = [template_code]

            if ec_id:
                sql += " AND (ec_id=%s OR ec_id IS NULL)"
                params.append(ec_id)
            if project_id:
                sql += " AND (project_id=%s OR project_id IS NULL)"
                params.append(project_id)

            sql += " ORDER BY ec_id DESC LIMIT 1"  # 优先返回企业定制模板

            template = db.get_one(sql, params)

            # 如果没有找到定制模板，返回默认模板
            if not template and template_code in cls.DEFAULT_TEMPLATES:
                default = cls.DEFAULT_TEMPLATES[template_code]
                template = {
                    'template_code': template_code,
                    'template_name': template_code,
                    'title_template': default['title'],
                    'content_template': default['content'],
                    'channels': default['channels'],
                    'msg_type': default['msg_type'],
                    'is_default': True
                }

            return template

        except Exception as e:
            logger.error(f"获取推送模板失败: template_code={template_code}, error={e}")
            return None

    @classmethod
    def create_template(cls, template_code, template_name, title_template, content_template,
                       channels, msg_type, ec_id=None, project_id=None, created_by=None):
        """创建推送模板"""
        try:
            # 检查模板代码是否已存在
            existing = db.get_one("""
                SELECT id FROM business_push_templates
                WHERE template_code=%s AND (ec_id=%s OR ec_id IS NULL)
            """, [template_code, ec_id])

            if existing:
                return {'success': False, 'msg': '模板代码已存在'}

            db.execute("""
                INSERT INTO business_push_templates
                (template_code, template_name, title_template, content_template,
                 channels, msg_type, ec_id, project_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [template_code, template_name, title_template, content_template,
                  json.dumps(channels), msg_type, ec_id, project_id, created_by])

            return {'success': True, 'msg': '模板创建成功'}

        except Exception as e:
            logger.error(f"创建推送模板失败: {e}")
            return {'success': False, 'msg': '创建失败'}

    @classmethod
    def send_message(cls, template_code, user_id, params, channels=None,
                    ec_id=None, project_id=None, priority='normal'):
        """
        发送消息

        Args:
            template_code: 模板代码
            user_id: 用户ID
            params: 模板参数
            channels: 推送渠道列表（默认使用模板配置的渠道）
            ec_id: 企业ID
            project_id: 项目ID
            priority: 优先级 (high/normal/low)

        Returns:
            dict: {'success': bool, 'msg': str, 'message_id': int}
        """
        try:
            # 获取模板
            template = cls.get_template(template_code, ec_id, project_id)

            if not template:
                return {'success': False, 'msg': f'未找到模板: {template_code}'}

            # 解析标题和内容
            title = cls._render_template(template.get('title_template', ''), params)
            content = cls._render_template(template.get('content_template', ''), params)

            # 确定推送渠道
            if channels is None:
                channels = template.get('channels', ['in_app'])
            if isinstance(channels, str):
                channels = [channels]

            msg_type = template.get('msg_type', 'system')
            channels = cls._filter_channels_by_preference(user_id, msg_type, channels, ec_id, project_id)
            if not channels:
                logger.info(f"用户已关闭相关通知或无可用渠道: user_id={user_id}, msg_type={msg_type}")
                return {
                    'success': True,
                    'msg': '用户已关闭该类通知或未开启可用渠道',
                    'message_id': None,
                    'results': {},
                    'skipped': True
                }

            # 消息编号
            msg_no = f'PUSH{datetime.now().strftime("%Y%m%d%H%M%S")}'

            # 创建消息记录
            msg_id = db.execute("""
                INSERT INTO business_push_messages
                (msg_no, user_id, title, content, template_code, channels,
                 msg_type, priority, status, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)
            """, [msg_no, user_id, title, content, template_code,
                  json.dumps(channels), msg_type,
                  priority, ec_id, project_id])

            # 根据渠道发送
            results = {}
            for channel in channels:
                try:
                    result = cls._send_by_channel(channel, user_id, title, content, msg_id, params, ec_id, project_id)
                    results[channel] = result
                except Exception as e:
                    logger.error(f"渠道 {channel} 推送失败: {e}")
                    results[channel] = {'success': False, 'error': str(e)}

            # 更新消息状态
            all_success = all(r.get('success', False) for r in results.values())
            db.execute("""
                UPDATE business_push_messages
                SET status=%s, sent_at=NOW(), result=%s
                WHERE id=%s
            """, ['sent' if all_success else 'partial', json.dumps(results, ensure_ascii=False), msg_id])

            return {
                'success': True,
                'msg': '消息发送成功',
                'message_id': msg_id,
                'results': results
            }


        except Exception as e:
            logger.error(f"发送消息失败: template_code={template_code}, user_id={user_id}, error={e}")
            return {'success': False, 'msg': '发送失败'}

    @classmethod
    def _render_template(cls, template_str, params):
        """渲染模板，替换变量"""
        if not template_str:
            return ''

        result = template_str
        for key, value in params.items():
            placeholder = f'{{{key}}}'
            result = result.replace(placeholder, str(value))

        return result

    @classmethod
    def _filter_channels_by_preference(cls, user_id, msg_type, channels, ec_id=None, project_id=None):
        """根据用户偏好过滤渠道"""
        try:
            return user_settings_service.filter_channels(user_id, msg_type, channels, ec_id, project_id)
        except Exception as e:
            logger.warning(f"读取用户通知偏好失败，回退默认渠道: user_id={user_id}, error={e}")
            return channels or ['in_app']

    @classmethod
    def _send_by_channel(cls, channel, user_id, title, content, msg_id, params, ec_id=None, project_id=None):
        """根据渠道发送消息"""
        if channel == 'in_app':
            return cls._send_in_app(user_id, title, content, msg_id)
        if channel == 'wechat':
            return cls._send_wechat(user_id, title, content, params, ec_id, project_id)
        if channel == 'sms':
            return cls._send_sms(user_id, content, params, ec_id, project_id)
        if channel == 'email':
            return cls._send_email(user_id, title, content, params, ec_id, project_id)
        return {'success': False, 'error': f'不支持的渠道: {channel}'}

    @classmethod
    def _send_in_app(cls, user_id, title, content, msg_id):
        """发送站内信"""
        try:
            from .notification import send_notification
            send_notification(
                user_id=user_id,
                title=title,
                content=content,
                notify_type='push_message',
                ref_id=str(msg_id),
                ref_type='push_message'
            )
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @classmethod
    def _send_via_webhook(cls, channel, payload, env_key):
        """通过可配置Webhook发送外部渠道消息"""
        webhook_url = os.environ.get(env_key, '').strip()
        if not webhook_url:
            logger.info(f"{channel}渠道未配置Webhook: env={env_key}")
            return {'success': False, 'skipped': True, 'note': f'{channel}渠道未配置'}

        try:
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            req = urllib_request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib_request.urlopen(req, timeout=8) as resp:
                response_text = resp.read().decode('utf-8', errors='ignore')
            return {
                'success': True,
                'status_code': getattr(resp, 'status', 200),
                'response': response_text[:500]
            }
        except urllib_error.HTTPError as e:
            return {'success': False, 'error': f'HTTP {e.code}: {e.reason}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @classmethod
    def _send_wechat(cls, user_id, title, content, params, ec_id=None, project_id=None):
        """发送微信模板消息（Webhook适配）"""
        contacts = user_settings_service.get_contact_info(user_id, ec_id, project_id)
        if not contacts.get('wechat_openid'):
            return {'success': False, 'skipped': True, 'note': '用户未绑定微信OpenID'}

        payload = {
            'channel': 'wechat',
            'user_id': user_id,
            'openid': contacts.get('wechat_openid'),
            'title': title,
            'content': content,
            'params': params or {}
        }
        return cls._send_via_webhook('wechat', payload, 'PUSH_WECHAT_WEBHOOK_URL')

    @classmethod
    def _send_sms(cls, user_id, content, params, ec_id=None, project_id=None):
        """发送短信（Webhook适配）"""
        contacts = user_settings_service.get_contact_info(user_id, ec_id, project_id)
        if not contacts.get('phone'):
            return {'success': False, 'skipped': True, 'note': '用户未绑定手机号'}

        payload = {
            'channel': 'sms',
            'user_id': user_id,
            'phone': contacts.get('phone'),
            'content': content,
            'params': params or {}
        }
        return cls._send_via_webhook('sms', payload, 'PUSH_SMS_WEBHOOK_URL')

    @classmethod
    def _send_email(cls, user_id, title, content, params, ec_id=None, project_id=None):
        """发送邮件（Webhook适配）"""
        contacts = user_settings_service.get_contact_info(user_id, ec_id, project_id)
        if not contacts.get('email'):
            return {'success': False, 'skipped': True, 'note': '用户未绑定邮箱'}

        payload = {
            'channel': 'email',
            'user_id': user_id,
            'email': contacts.get('email'),
            'title': title,
            'content': content,
            'params': params or {}
        }
        return cls._send_via_webhook('email', payload, 'PUSH_EMAIL_WEBHOOK_URL')


    @classmethod
    def batch_send(cls, template_code, user_ids, params, channels=None,
                  ec_id=None, project_id=None, priority='normal'):
        """
        批量发送消息

        Args:
            template_code: 模板代码
            user_ids: 用户ID列表
            params: 模板参数
            channels: 推送渠道
            ec_id: 企业ID
            project_id: 项目ID
            priority: 优先级

        Returns:
            dict: {'success': bool, 'total': int, 'sent': int, 'failed': int}
        """
        sent = 0
        failed = 0

        for user_id in user_ids:
            result = cls.send_message(template_code, user_id, params, channels, ec_id, project_id, priority)
            if result.get('success'):
                sent += 1
            else:
                failed += 1

        return {
            'success': True,
            'total': len(user_ids),
            'sent': sent,
            'failed': failed
        }

    @classmethod
    def schedule_message(cls, template_code, user_ids, params, send_at,
                       channels=None, ec_id=None, project_id=None, created_by=None):
        """
        定时发送消息

        Args:
            template_code: 模板代码
            user_ids: 用户ID列表
            params: 模板参数
            send_at: 发送时间
            channels: 推送渠道
            ec_id: 企业ID
            project_id: 项目ID
            created_by: 创建人

        Returns:
            dict: {'success': bool, 'msg': str, 'task_id': int}
        """
        try:
            task_no = f'SCH{datetime.now().strftime("%Y%m%d%H%M%S")}'
            task_id = db.execute("""
                INSERT INTO business_push_tasks
                (task_no, template_code, user_ids, params, channels,
                 send_at, status, ec_id, project_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s)
            """, [task_no, template_code, json.dumps(user_ids), json.dumps(params),
                  json.dumps(channels or []), send_at, ec_id, project_id, created_by])

            return {'success': True, 'msg': '定时任务已创建', 'task_id': task_id}

        except Exception as e:
            logger.error(f"创建定时任务失败: {e}")
            return {'success': False, 'msg': '创建失败'}

    @classmethod
    def get_message_history(cls, user_id, page=1, page_size=20):
        """获取用户消息历史"""
        try:
            total = db.get_total("""
                SELECT COUNT(*) FROM business_push_messages
                WHERE user_id=%s
            """, [user_id])

            messages = db.get_all("""
                SELECT id, msg_no, title, content, channels, status, created_at
                FROM business_push_messages
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, [user_id, page_size, (page - 1) * page_size])

            # 解析channels
            for msg in (messages or []):
                if msg.get('channels'):
                    try:
                        msg['channels'] = json.loads(msg['channels']) if isinstance(msg['channels'], str) else msg['channels']
                    except:
                        msg['channels'] = []

            return {
                'items': messages or [],
                'total': total,
                'page': page,
                'page_size': page_size
            }

        except Exception as e:
            logger.error(f"获取消息历史失败: user_id={user_id}, error={e}")
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size}

    @classmethod
    def get_push_stats(cls, ec_id=None, project_id=None, days=7):
        """获取推送统计"""
        try:
            date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            where = f"created_at >= '{date_from}'"
            params = []

            if ec_id:
                where += " AND ec_id=%s"
                params.append(ec_id)
            if project_id:
                where += " AND project_id=%s"
                params.append(project_id)

            # 统计
            stats = db.get_one(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='sent' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                    COUNT(DISTINCT user_id) as users
                FROM business_push_messages
                WHERE {where}
            """, params)

            # 按模板统计
            by_template = db.get_all(f"""
                SELECT template_code, COUNT(*) as cnt
                FROM business_push_messages
                WHERE {where}
                GROUP BY template_code
                ORDER BY cnt DESC
                LIMIT 10
            """, params)

            return {
                'period_days': days,
                'total_sent': stats.get('total', 0) or 0,
                'delivered': stats.get('sent', 0) or 0,
                'failed': stats.get('failed', 0) or 0,
                'unique_users': stats.get('users', 0) or 0,
                'by_template': by_template or []
            }

        except Exception as e:
            logger.error(f"获取推送统计失败: {e}")
            return {
                'period_days': days,
                'total_sent': 0,
                'delivered': 0,
                'failed': 0,
                'unique_users': 0,
                'by_template': []
            }

    @classmethod
    def mark_as_read(cls, user_id, message_ids=None):
        """标记消息为已读"""
        try:
            if message_ids:
                placeholders = ','.join(['%s'] * len(message_ids))
                db.execute(f"""
                    UPDATE business_push_messages
                    SET is_read=1, read_at=NOW()
                    WHERE user_id=%s AND id IN ({placeholders})
                """, [user_id] + message_ids)
            else:
                # 全部标记已读
                db.execute("""
                    UPDATE business_push_messages
                    SET is_read=1, read_at=NOW()
                    WHERE user_id=%s AND is_read=0
                """, [user_id])

            return {'success': True, 'msg': '已标记已读'}

        except Exception as e:
            logger.error(f"标记已读失败: {e}")
            return {'success': False, 'msg': '操作失败'}


# 便捷实例
push_service = PushService()
