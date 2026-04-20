#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 直接替换所有 status = 1 → is_active = 1 (在引号内的SQL中)
import re
# 替换 SQL 字符串中的 status = 1
content = re.sub(r"['\"]status\s*=\s*1", r"is_active = 1", content)

# 也替换 approval_config
content = content.replace('approval_config', 'approve_flow')

with open(svc_py, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ 已用正则替换所有 remaining status=1')
