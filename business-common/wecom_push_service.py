#!/usr/bin/env python3
"""
企业微信推送服务模块 V44.0
功能：
  - 审批结果企微推送
  - 申请提醒推送
  - 到期提醒推送
"""
import json
import logging
import requests
from datetime import datetime
from . import db

logger = logging.getLogger(__name__)


class WeComPushService:
    """企业微信推送服务"""

    # 企微机器人Webhook地址（从环境变量读取）
    # WECOM_WEBHOOK_URL = https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
    WECOM_WEBHOOK_URL = ''  # 生产环境配置

    # 企微应用配置
    WECOM_CORP_ID = ''  # 企业ID
    WECOM_AGENT_ID = ''  # 应用AgentId
    WECOM_SECRET = ''  # 应用Secret

    @staticmethod
    def send_message(user_ids, title, content, msg_type='text', **kwargs):
        """
        发送企微消息

        Args:
            user_ids: 用户ID列表（企微用户ID）
            title: 消息标题
            content: 消息内容
            msg_type: 消息类型 (text/markdown/card)
            **kwargs: 其他参数

        Returns:
            dict: 发送结果
        """
        if not WeComPushService.WECOM_WEBHOOK_URL:
            logger.warning("企微Webhook未配置，跳过推送")
            return {'success': False, 'msg': '企微推送未配置'}

        try:
            # 构建消息体
            if msg_type == 'text':
                data = {
                    'msgtype': 'text',
                    'text': {
                        'content': f'{title}\n{content}',
                        'mentioned_list': user_ids if isinstance(user_ids, list) else [user_ids]
                    }
                }
            elif msg_type == 'markdown':
                data = {
                    'msgtype': 'markdown',
                    'markdown': {
                        'content': f'## {title}\n{content}'
                    }
                }
            elif msg_type == 'card':
                data = {
                    'msgtype': 'template_card',
                    'template_card': {
                        'card_type': 'text_notice',
                        'main_title': {'title': title},
                        'sub_title_text': content,
                        **kwargs.get('card_extra', {})
                    }
                }
            else:
                data = {
                    'msgtype': 'text',
                    'text': {'content': f'{title}\n{content}'}
                }

            # 发送请求
            resp = requests.post(
                WeComPushService.WECOM_WEBHOOK_URL,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            result = resp.json()
            if result.get('errcode') == 0:
                logger.info(f"企微推送成功: user_ids={user_ids}, title={title}")
                return {'success': True, 'msg': '推送成功'}
            else:
                logger.error(f"企微推送失败: {result}")
                return {'success': False, 'msg': result.get('errmsg', '推送失败')}

        except requests.RequestException as e:
            logger.error(f"企微推送请求失败: {e}")
            return {'success': False, 'msg': f'请求失败: {e}'}
        except Exception as e:
            logger.error(f"企微推送异常: {e}")
            return {'success': False, 'msg': f'推送异常: {e}'}

    @staticmethod
    def push_approval_result(app_info, result, approver_name=''):
        """
        推送审批结果通知

        Args:
            app_info: 申请信息
            result: 审批结果 ('approved' / 'rejected')
            approver_name: 审批人姓名

        Returns:
            dict: 推送结果
        """
        app_no = app_info.get('app_no', '')
        app_type = app_info.get('app_type_name', app_info.get('app_type', ''))
        user_name = app_info.get('user_name', '')
        user_id = app_info.get('user_id', '')

        # 审批结果文本
        result_text = '已通过' if result == 'approved' else '已拒绝'
        result_emoji = '✅' if result == 'approved' else '❌'

        title = f'{result_emoji} 申请审批结果通知'
        content = f'''
**申请类型**: {app_type}
**申请单号**: {app_no}
**申请人**: {user_name}
**审批结果**: {result_text}
**审批人**: {approver_name}
**审批时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
'''

        if result == 'approved':
            content += '\n> 您的申请已通过审批，请按相关要求执行。'
        else:
            reject_reason = app_info.get('reject_reason', '无')
            content += f'\n> 拒绝原因: {reject_reason}'

        return WeComPushService.send_message(
            [str(user_id)],
            title,
            content,
            msg_type='markdown'
        )

    @staticmethod
    def push_application_remind(app_info, remind_type='pending'):
        """
        推送申请提醒

        Args:
            app_info: 申请信息
            remind_type: 提醒类型 (pending/expired/approaching)

        Returns:
            dict: 推送结果
        """
        app_no = app_info.get('app_no', '')
        app_type = app_info.get('app_type_name', app_info.get('app_type', ''))
        user_name = app_info.get('user_name', '')

        remind_texts = {
            'pending': '⏰ 您有申请待审批',
            'expired': '⚠️ 申请即将到期',
            'approaching': '📅 申请即将开始',
        }

        title = remind_texts.get(remind_type, '申请提醒')
        content = f'''
**申请类型**: {app_type}
**申请单号**: {app_no}
**申请人**: {user_name}
**提醒时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
'''

        return WeComPushService.send_message(
            [str(app_info.get('user_id', ''))],
            title,
            content,
            msg_type='markdown'
        )

    @staticmethod
    def push_expire_remind(app_info):
        """
        推送到期提醒（候餐椅、货梯等）

        Args:
            app_info: 申请信息

        Returns:
            dict: 推送结果
        """
        app_no = app_info.get('app_no', '')
        app_type = app_info.get('app_type_name', app_info.get('app_type', ''))
        end_time = app_info.get('form_data', {}).get('end_time', '')

        title = '⏰ 申请即将到期提醒'
        content = f'''
**申请类型**: {app_type}
**申请单号**: {app_no}
**到期时间**: {end_time}
**提醒时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

> 您的申请即将到期，请及时处理撤场事宜。
'''

        return WeComPushService.send_message(
            [str(app_info.get('user_id', ''))],
            title,
            content,
            msg_type='markdown'
        )

    @staticmethod
    def push_to_approvers(app_info, approver_ids):
        """
        推送待审批通知给审批人

        Args:
            app_info: 申请信息
            approver_ids: 审批人ID列表

        Returns:
            dict: 推送结果
        """
        app_no = app_info.get('app_no', '')
        app_type = app_info.get('app_type_name', app_info.get('app_type', ''))
        user_name = app_info.get('user_name', '')

        title = '📋 新申请待审批'
        content = f'''
**申请类型**: {app_type}
**申请单号**: {app_no}
**申请人**: {user_name}
**申请时间**: {app_info.get('created_at', '')}

> 请及时登录系统进行审批处理。
'''

        return WeComPushService.send_message(
            approver_ids,
            title,
            content,
            msg_type='markdown'
        )


# 便捷实例
wecom_push = WeComPushService()
