#!/usr/bin/env python3
import re

with open('/www/wwwroot/wojiayun/business-userH5/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在 get_application_type 调用后添加调试
old_code = '''    app_type = ApplicationService.get_application_type(type_code)
    if not app_type:
        return jsonify({'success': False, 'msg': '申请类型不存在'})'''

new_code = '''    app_type = ApplicationService.get_application_type(type_code)
    import logging
    logging.info(f"[DEBUG] get_application_type({type_code}) result: {app_type}")
    logging.info(f"[DEBUG] user: {user}")
    if not app_type:
        return jsonify({'success': False, 'msg': '申请类型不存在'})'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/www/wwwroot/wojiayun/business-userH5/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ 调试日志已添加')
else:
    print('❌ 未找到目标代码')
