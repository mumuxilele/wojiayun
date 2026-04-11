"""
V36.0 体验闭环增强测试用例

说明:
- 当前项目公共模块目录名为 business-common，运行环境对导入路径有定制处理。
- 为保证测试在通用 Python 解释器下也能稳定执行，本文件以“结构契约测试”为主，
  重点校验 V36.0 关键能力是否已经落盘到代码与页面层。

测试覆盖:
1. 用户通知偏好云端持久化链路
2. 订单超时倒计时字段透传
3. 会员权益展示与升级指引页面
4. PushService 偏好过滤与外部渠道适配代码
5. V36.0 数据库迁移脚本

Author: AI产品经理
Date: 2026-04-05
"""

import os
import unittest


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_project_file(relative_path):
    file_path = os.path.join(BASE_DIR, relative_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


class TestV36Contracts(unittest.TestCase):
    """V36.0 结构契约测试"""

    def test_v36_core_files_exist(self):
        required_files = [
            'business-common/user_settings_service.py',
            'business-common/migrate_v36.py',
            'business-common/push_service.py',
            'business-userH5/app.py',
            'business-userH5/member.html',
            'business-userH5/settings.html',
            'business-userH5/orders.html',
            'tests/test_v36.py'
        ]
        missing = [path for path in required_files if not os.path.exists(os.path.join(BASE_DIR, path))]
        self.assertFalse(missing, f'缺少 V36.0 核心文件: {missing}')

    def test_user_app_exposes_notification_preferences_api(self):
        content = read_project_file('business-userH5/app.py')
        self.assertIn("@app.route('/api/user/notification-preferences', methods=['GET'])", content)
        self.assertIn("@app.route('/api/user/notification-preferences', methods=['PUT'])", content)
        self.assertIn('user_settings_service.get_notification_preferences', content)
        self.assertIn('user_settings_service.update_notification_preferences', content)

    def test_user_app_returns_expire_time_for_order_flow(self):
        content = read_project_file('business-userH5/app.py')
        self.assertIn('COALESCE(expire_time, DATE_ADD(created_at, INTERVAL', content)
        self.assertIn("'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S')", content)
        self.assertIn('ORDER_EXPIRE_MINUTES = OrderService.ORDER_EXPIRE_MINUTES', content)
        self.assertIn("template_code='order_created'", content)

    def test_user_member_api_contains_display_level_fields(self):
        content = read_project_file('business-userH5/app.py')
        self.assertIn('display_level_name', content)
        self.assertIn('discount_rate', content)
        self.assertIn('points_rate', content)
        self.assertIn('business_member_levels', content)

    def test_member_page_uses_benefits_api_and_shows_value(self):
        content = read_project_file('business-userH5/member.html')
        self.assertIn("/api/user/member/benefits", content)
        self.assertIn('当前会员权益', content)
        self.assertIn('升级任务指引', content)
        self.assertIn('等级权益对比', content)
        self.assertIn('renderPrivilegeList', content)
        self.assertIn('renderUpgradeTasks', content)
        self.assertIn('renderLevelList', content)

    def test_settings_page_supports_cloud_sync_and_channel_switches(self):
        content = read_project_file('business-userH5/settings.html')
        self.assertIn('这些偏好会同步到服务器', content)
        self.assertIn("fetch(api('/api/user/notification-preferences'))", content)
        self.assertIn('channelWechat', content)
        self.assertIn('channelSms', content)
        self.assertIn('channelEmail', content)
        self.assertIn('settings_pref_cache', content)
        self.assertIn('V36.0', content)

    def test_orders_page_has_countdown_experience(self):
        content = read_project_file('business-userH5/orders.html')
        self.assertIn('countdown-bar', content)
        self.assertIn('renderCountdown', content)
        self.assertIn('refreshCountdowns', content)
        self.assertIn('还剩', content)
        self.assertIn('支付已超时', content)

    def test_user_settings_service_contains_default_preferences_and_filtering(self):
        content = read_project_file('business-common/user_settings_service.py')
        self.assertIn('DEFAULT_SETTINGS', content)
        self.assertIn("'notif_order': True", content)
        self.assertIn("'channel_in_app': True", content)
        self.assertIn('filter_channels', content)
        self.assertIn('get_contact_info', content)
        self.assertIn('business_user_settings', content)

    def test_push_service_integrates_user_preferences_and_webhook_channels(self):
        content = read_project_file('business-common/push_service.py')
        self.assertIn('from .user_settings_service import user_settings_service', content)
        self.assertIn('_filter_channels_by_preference', content)
        self.assertIn('_send_wechat', content)
        self.assertIn('_send_sms', content)
        self.assertIn('_send_email', content)
        self.assertIn('PUSH_WECHAT_WEBHOOK_URL', content)
        self.assertIn('PUSH_SMS_WEBHOOK_URL', content)
        self.assertIn('PUSH_EMAIL_WEBHOOK_URL', content)

    def test_migrate_v36_creates_user_settings_and_expire_time(self):
        content = read_project_file('business-common/migrate_v36.py')
        self.assertIn('CREATE TABLE IF NOT EXISTS business_user_settings', content)
        self.assertIn('notif_order', content)
        self.assertIn('channel_wechat', content)
        self.assertIn('ALTER TABLE business_orders', content)
        self.assertIn('ADD COLUMN expire_time', content)
        self.assertIn('MIGRATION_NAME =', content)

    def test_common_exports_include_push_and_user_settings(self):
        content = read_project_file('business-common/__init__.py')
        self.assertIn('from .user_settings_service import UserSettingsService, user_settings_service', content)
        self.assertIn('from .push_service import PushService, push_service', content)
        self.assertIn("'UserSettingsService'", content)
        self.assertIn("'PushService'", content)


if __name__ == '__main__':
    unittest.main()
