#!/usr/bin/env python3
import re, sys

app_py = '/www/wwwroot/wojiayun/business-userH5/app.py'

with open(app_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 return jsonify({'success': False, 'msg': '申请类型不存在'}) 之前添加
old = '''    app_type = ApplicationService.get_application_type(type_code)
    import logging
    logging.info(f"[DEBUG] get_application_type({type_code}) result: {app_type}")
    logging.info(f"[DEBUG] user: {user}")
    if not app_type:
        return jsonify({'success': False, 'msg': '申请类型不存在'})'''

new = '''    app_type = ApplicationService.get_application_type(type_code)
    app.logger.info(f"[DEBUG] get_application_type({type_code}) result: {app_type}")
    app.logger.info(f"[DEBUG] user: {user}")
    app.logger.info(f"[DEBUG] user ecId: {user.get('ecId') if user else None}")
    if not app_type:
        return jsonify({'success': False, 'msg': '申请类型不存在'})'''

if old in content:
    content = content.replace(old, new)
    with open(app_py, 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ 调试日志已更新，使用 app.logger')
else:
    print('❌ 未找到目标代码')
    print('搜索 application_types...')
    idx = content.find('application_types')
    if idx > 0:
        print(f'找到于 {idx}')
        print(content[idx-50:idx+200])
