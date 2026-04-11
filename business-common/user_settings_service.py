"""
用户设置服务 V36.0
功能:
  - 用户通知偏好持久化
  - 推送渠道开关管理
  - 推送前置过滤
"""
import logging
from typing import Any, Dict, List, Optional

from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)


class UserSettingsService(BaseService):
    """用户设置服务"""

    SERVICE_NAME = 'UserSettingsService'

    DEFAULT_SETTINGS = {
        'notif_order': True,
        'notif_coupon': True,
        'notif_system': True,
        'channel_in_app': True,
        'channel_wechat': False,
        'channel_sms': False,
        'channel_email': False,
        'wechat_openid': '',
        'email': ''
    }

    MSG_TYPE_PREF_MAP = {
        'order': 'notif_order',
        'payment': 'notif_order',
        'refund': 'notif_order',
        'delivery': 'notif_order',
        'marketing': 'notif_coupon',
        'activity': 'notif_coupon',
        'system': 'notif_system'
    }

    CHANNEL_PREF_MAP = {
        'in_app': 'channel_in_app',
        'wechat': 'channel_wechat',
        'sms': 'channel_sms',
        'email': 'channel_email'
    }

    @staticmethod
    def _normalize_scope(ec_id: Any = None, project_id: Any = None) -> tuple:
        return str(ec_id or ''), str(project_id or '')

    @staticmethod
    def _to_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in ('1', 'true', 'yes', 'y', 'on')

    def _default_payload(self, user_id: Any, ec_id: Any = None, project_id: Any = None) -> Dict[str, Any]:
        scope_ec_id, scope_project_id = self._normalize_scope(ec_id, project_id)
        result = {'user_id': str(user_id), 'ec_id': scope_ec_id, 'project_id': scope_project_id}
        result.update(self.DEFAULT_SETTINGS)
        return result

    def _serialize_row(self, row: Optional[Dict[str, Any]], user_id: Any, ec_id: Any = None, project_id: Any = None) -> Dict[str, Any]:
        payload = self._default_payload(user_id, ec_id, project_id)
        if row:
            payload.update({
                'notif_order': self._to_bool(row.get('notif_order'), True),
                'notif_coupon': self._to_bool(row.get('notif_coupon'), True),
                'notif_system': self._to_bool(row.get('notif_system'), True),
                'channel_in_app': self._to_bool(row.get('channel_in_app'), True),
                'channel_wechat': self._to_bool(row.get('channel_wechat'), False),
                'channel_sms': self._to_bool(row.get('channel_sms'), False),
                'channel_email': self._to_bool(row.get('channel_email'), False),
                'wechat_openid': row.get('wechat_openid') or '',
                'email': row.get('email') or ''
            })
        payload['delivery_channels'] = {
            'in_app': payload['channel_in_app'],
            'wechat': payload['channel_wechat'],
            'sms': payload['channel_sms'],
            'email': payload['channel_email']
        }
        return payload

    def ensure_user_settings(self, user_id: Any, ec_id: Any = None, project_id: Any = None) -> Dict[str, Any]:
        """确保用户设置存在"""
        scope_ec_id, scope_project_id = self._normalize_scope(ec_id, project_id)
        user_id = str(user_id)
        try:
            row = db.get_one(
                """
                SELECT * FROM business_user_settings
                WHERE user_id=%s AND ec_id=%s AND project_id=%s AND deleted=0
                LIMIT 1
                """,
                [user_id, scope_ec_id, scope_project_id]
            )
            if row:
                return self._serialize_row(row, user_id, scope_ec_id, scope_project_id)
        except Exception as e:
            logger.warning(f"查询用户设置失败，回退默认值: user_id={user_id}, error={e}")
            return self._default_payload(user_id, scope_ec_id, scope_project_id)

        try:
            db.execute(
                """
                INSERT INTO business_user_settings (
                    user_id, ec_id, project_id,
                    notif_order, notif_coupon, notif_system,
                    channel_in_app, channel_wechat, channel_sms, channel_email,
                    wechat_openid, email
                ) VALUES (%s, %s, %s, 1, 1, 1, 1, 0, 0, 0, '', '')
                """,
                [user_id, scope_ec_id, scope_project_id]
            )
        except Exception as e:
            logger.warning(f"初始化用户设置失败，继续返回默认值: user_id={user_id}, error={e}")

        return self._default_payload(user_id, scope_ec_id, scope_project_id)


    def get_notification_preferences(self, user_id: Any, ec_id: Any = None, project_id: Any = None) -> Dict[str, Any]:
        """获取通知偏好"""
        scope_ec_id, scope_project_id = self._normalize_scope(ec_id, project_id)
        user_id = str(user_id)
        try:
            row = db.get_one(
                """
                SELECT * FROM business_user_settings
                WHERE user_id=%s AND ec_id=%s AND project_id=%s AND deleted=0
                LIMIT 1
                """,
                [user_id, scope_ec_id, scope_project_id]
            )
            if not row:
                return self.ensure_user_settings(user_id, scope_ec_id, scope_project_id)
            return self._serialize_row(row, user_id, scope_ec_id, scope_project_id)
        except Exception as e:
            logger.error(f"获取用户通知偏好失败: user_id={user_id}, error={e}")
            return self._default_payload(user_id, scope_ec_id, scope_project_id)

    def update_notification_preferences(self, user_id: Any, data: Dict[str, Any], ec_id: Any = None, project_id: Any = None) -> Dict[str, Any]:
        """更新通知偏好"""
        scope_ec_id, scope_project_id = self._normalize_scope(ec_id, project_id)
        user_id = str(user_id)
        self.ensure_user_settings(user_id, scope_ec_id, scope_project_id)

        allowed_bool_fields = [
            'notif_order', 'notif_coupon', 'notif_system',
            'channel_in_app', 'channel_wechat', 'channel_sms', 'channel_email'
        ]
        allowed_text_fields = ['wechat_openid', 'email']

        updates = []
        params: List[Any] = []

        for field in allowed_bool_fields:
            if field in data:
                updates.append(f"{field}=%s")
                params.append(1 if self._to_bool(data.get(field)) else 0)

        for field in allowed_text_fields:
            if field in data:
                updates.append(f"{field}=%s")
                params.append(str(data.get(field) or '').strip())

        if updates:
            updates.append("updated_at=NOW()")
            params.extend([user_id, scope_ec_id, scope_project_id])
            db.execute(
                f"""
                UPDATE business_user_settings
                SET {', '.join(updates)}
                WHERE user_id=%s AND ec_id=%s AND project_id=%s AND deleted=0
                """,
                params
            )

        latest = self.get_notification_preferences(user_id, scope_ec_id, scope_project_id)
        return {'success': True, 'msg': '通知偏好已更新', 'data': latest}

    def filter_channels(self, user_id: Any, msg_type: str, channels: Optional[List[str]], ec_id: Any = None, project_id: Any = None) -> List[str]:
        """根据用户偏好过滤推送渠道"""
        prefs = self.get_notification_preferences(user_id, ec_id, project_id)
        pref_key = self.MSG_TYPE_PREF_MAP.get(msg_type, 'notif_system')
        if not prefs.get(pref_key, True):
            return []

        normalized_channels = channels or ['in_app']
        result = []
        for channel in normalized_channels:
            pref_field = self.CHANNEL_PREF_MAP.get(channel)
            if pref_field is None:
                continue
            if prefs.get(pref_field, False):
                result.append(channel)
        return result

    def get_contact_info(self, user_id: Any, ec_id: Any = None, project_id: Any = None) -> Dict[str, str]:
        """获取推送联系信息"""
        prefs = self.get_notification_preferences(user_id, ec_id, project_id)
        member = None
        try:
            member = db.get_one(
                "SELECT phone, user_name FROM business_members WHERE user_id=%s LIMIT 1",
                [str(user_id)]
            ) or {}
        except Exception as e:
            logger.warning(f"查询用户联系信息失败: user_id={user_id}, error={e}")
            member = {}

        return {
            'phone': member.get('phone') or '',
            'user_name': member.get('user_name') or '',
            'wechat_openid': prefs.get('wechat_openid', ''),
            'email': prefs.get('email', '')
        }


user_settings_service = UserSettingsService()
