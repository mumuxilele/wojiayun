#!/usr/bin/env python3
"""
V20.0 自动化测试 - 安全加固与稳定性增强
覆盖: 密码硬编码移除、认证绕过修复、SQL注入修复、并发安全、XSS防护、通知重试
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestV20ConfigSecurity(unittest.TestCase):
    """P0: 配置安全"""

    def test_config_no_hardcoded_password(self):
        """config.py 不应包含明文密码默认值"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    'business-common', 'config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn('Wojiacloud$2023', content,
                         'config.py 仍包含硬编码密码')

    def test_config_uses_env_vars(self):
        """config.py 应使用环境变量获取密码"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    'business-common', 'config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('DB_PASSWORD', content,
                      'config.py 应包含 DB_PASSWORD 环境变量读取')


class TestV20AuthBypassFix(unittest.TestCase):
    """P0: 认证绕过修复"""

    def test_admin_no_empty_before_request(self):
        """admin/app.py 不应有空的 before_request pass"""
        admin_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'business-admin', 'app.py')
        content = open(admin_path, 'r', encoding='utf-8').read()
        # 不应存在仅包含pass的before_request
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '@app.before_request' in line:
                # 检查接下来的几行是否有 pass
                for j in range(i+1, min(i+5, len(lines))):
                    stripped = lines[j].strip()
                    if stripped.startswith('def '):
                        func_body_start = j + 1
                        for k in range(func_body_start, min(func_body_start + 5, len(lines))):
                            body = lines[k].strip()
                            if body == 'pass':
                                self.fail(f'admin/app.py 第{k+1}行存在空的 before_request pass，'
                                          f'可能导致认证绕过')
                            if body and body != 'pass':
                                break
                        break

    def test_admin_no_debugtest_exposed(self):
        """admin 不应暴露 /debugtest 路径"""
        admin_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'business-admin', 'app.py')
        content = open(admin_path, 'r', encoding='utf-8').read()
        self.assertNotIn('/debugtest', content.split('exempt_paths')[1].split('\n')[0] if 'exempt_paths' in content else '',
                         '/debugtest 仍在认证豁免路径中')


class TestV20SQLInjectionFix(unittest.TestCase):
    """P1: SQL注入修复"""

    def test_staff_no_date_scope_string_concat(self):
        """staffH5 仪表盘不应使用字符串拼接日期范围"""
        staff_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'business-staffH5', 'app.py')
        with open(staff_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 仪表盘 date_scope 应使用参数化查询 %s 而非字符串拼接
        # 检查不应有 f" AND created_at >= '...'" 模式
        import re
        # 查找所有包含 created_at >= 的行
        for line_num, line in enumerate(content.split('\n'), 1):
            if 'created_at >=' in line and "'" in line and '%s' not in line and 'date_scope' not in line.split('#')[0]:
                # 排除注释行和正常参数化查询
                code_part = line.split('#')[0].strip()
                if code_part and 'created_at >=' in code_part:
                    self.fail(f'staffH5 第{line_num}行可能使用字符串拼接日期范围: {line.strip()}')

    def test_staff_refund_filter_parameterized(self):
        """staffH5 退款筛选应使用参数化查询"""
        staff_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'business-staffH5', 'app.py')
        content = open(staff_path, 'r', encoding='utf-8').read()
        # 不应有 f" AND order_status='{status_map[status]}'" 这样的拼接
        self.assertNotIn("order_status='{status_map", content,
                         'staffH5 退款筛选仍使用f-string拼接（SQL注入风险）')


class TestV20ConcurrentSafety(unittest.TestCase):
    """P1: 并发安全"""

    def test_checkin_uses_for_update(self):
        """签到操作应使用 FOR UPDATE 行锁"""
        user_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'business-userH5', 'app.py')
        content = open(user_path, 'r', encoding='utf-8').read()
        # 签到函数中应包含 FOR UPDATE
        checkin_section = content[content.find('def daily_checkin'):content.find('def daily_checkin') + 2000]
        self.assertIn('FOR UPDATE', checkin_section,
                     '签到操作未使用 FOR UPDATE 行锁（并发安全风险）')

    def test_checkin_has_yesterday_before_try(self):
        """签到函数应在 try 块之前定义 yesterday"""
        user_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'business-userH5', 'app.py')
        content = open(user_path, 'r', encoding='utf-8').read()
        func_start = content.find('def daily_checkin')
        try_pos = content.find('try:', func_start)
        yesterday_pos = content.find('yesterday', func_start)
        self.assertLess(yesterday_pos, try_pos,
                        'yesterday 变量应在 try 块之前定义')

    def test_checkin_has_finally_block(self):
        """签到函数应有 finally 块关闭连接"""
        user_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'business-userH5', 'app.py')
        content = open(user_path, 'r', encoding='utf-8').read()
        func_start = content.find('def daily_checkin')
        func_end = content.find('\ndef ', func_start + 10)
        func_body = content[func_start:func_end] if func_end > 0 else content[func_start:]
        self.assertIn('finally:', func_body,
                     '签到操作缺少 finally 块关闭数据库连接')


class TestV20DuplicateRouteFix(unittest.TestCase):
    """P1: 路由重复修复"""

    def test_no_duplicate_refund_routes(self):
        """userH5 不应有重复的退款路由"""
        user_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'business-userH5', 'app.py')
        content = open(user_path, 'r', encoding='utf-8').read()
        refund_count = content.count("'/api/user/orders/")
        refund_count += content.count('/api/user/orders/')
        # 应只有一个 refund 路由定义
        route_defs = []
        for line in content.split('\n'):
            if '@app.route' in line and 'refund' in line:
                route_defs.append(line.strip())
        self.assertEqual(len(route_defs), 1,
                         f'发现 {len(route_defs)} 个退款路由定义，应只有1个: {route_defs}')


class TestV20NotificationFix(unittest.TestCase):
    """P1: 通知参数名修复"""

    def test_monitor_uses_notify_type(self):
        """application_monitor 应使用 notify_type 而非 msg_type"""
        monitor_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                      'business-common', 'application_monitor.py')
        content = open(monitor_path, 'r', encoding='utf-8').read()
        self.assertNotIn('msg_type=', content,
                         'application_monitor 仍使用错误的参数名 msg_type')
        self.assertIn('notify_type=', content,
                      'application_monitor 应使用 notify_type 参数名')


class TestV20NotificationRetry(unittest.TestCase):
    """P1: 通知重试机制"""

    def test_notification_has_retry_config(self):
        """notification.py 应有重试配置"""
        notif_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'business-common', 'notification.py')
        with open(notif_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('MAX_RETRIES', content,
                      'notification 模块缺少 MAX_RETRIES 配置')
        self.assertIn('RETRY_BACKOFF_BASE', content,
                      'notification 模块缺少 RETRY_BACKOFF_BASE 配置')
        # 验证 MAX_RETRIES >= 2
        import re
        m = re.search(r'MAX_RETRIES\s*=\s*(\d+)', content)
        if m:
            self.assertGreaterEqual(int(m.group(1)), 2, 'MAX_RETRIES 应至少为 2')

    def test_notification_retry_backoff(self):
        """notification.py 应有指数退避配置"""
        notif_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'business-common', 'notification.py')
        with open(notif_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('RETRY_BACKOFF_BASE', content,
                      'notification 模块缺少 RETRY_BACKOFF_BASE 配置')
        import re
        m = re.search(r'RETRY_BACKOFF_BASE\s*=\s*([\d.]+)', content)
        if m:
            self.assertGreater(float(m.group(1)), 0, 'RETRY_BACKOFF_BASE 应大于 0')


class TestV20XSSProtection(unittest.TestCase):
    """P2: XSS防护"""

    def test_admin_has_escape_function(self):
        """admin/index.html 应有 XSS 转义函数"""
        admin_html = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    'business-admin', 'index.html')
        content = open(admin_html, 'r', encoding='utf-8').read()
        self.assertIn('escHtml', content,
                      'admin/index.html 缺少 XSS 转义函数 escHtml')

    def test_admin_username_uses_textcontent(self):
        """admin 用户名显示应使用 textContent"""
        admin_html = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    'business-admin', 'index.html')
        content = open(admin_html, 'r', encoding='utf-8').read()
        # 找到 userInfoEl 相关的行
        lines = content.split('\n')
        for line in lines:
            if 'userInfoEl' in line and 'innerHTML' in line and 'user_name' in line.lower():
                self.fail(f'admin 用户名仍使用 innerHTML: {line.strip()}')


class TestV20HardcodedIPRemoval(unittest.TestCase):
    """P2: 硬编码IP移除"""

    def test_business_dir_no_hardcoded_ip(self):
        """business/ 目录下的 HTML 文件不应包含硬编码 IP"""
        business_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'business')
        for filename in os.listdir(business_dir):
            if filename.endswith('.html'):
                filepath = os.path.join(business_dir, filename)
                content = open(filepath, 'r', encoding='utf-8').read()
                self.assertNotIn('47.98.238.209', content,
                                 f'{filename} 仍包含硬编码 IP 地址')

    def test_business_app_no_hardcoded_password(self):
        """business_app.py 不应包含硬编码密码"""
        app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'business_app.py')
        content = open(app_path, 'r', encoding='utf-8').read()
        self.assertNotIn('Wojiacloud$2023', content,
                         'business_app.py 仍包含硬编码密码')
        self.assertNotIn('debug=True', content,
                         'business_app.py 仍启用 debug 模式')


if __name__ == '__main__':
    unittest.main(verbosity=2)
