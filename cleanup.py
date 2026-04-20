#!/usr/bin/env python3

app_py = '/www/wwwroot/wojiayun/business-userH5/app.py'

with open(app_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 清理调试代码
debug_lines = [
    '    import logging\n    logging.info(f"[DEBUG] get_application_type({type_code}) result: {app_type}")\n    logging.info(f"[DEBUG] user: {user}")\n',
    '    app.logger.info(f"[DEBUG] get_application_type({type_code}) result: {app_type}")\n    app.logger.info(f"[DEBUG] user: {user}")\n    app.logger.info(f"[DEBUG] user ecId: {user.get(\'ecId\') if user else None}")\n',
]
for dl in debug_lines:
    if dl in content:
        content = content.replace(dl, '')

with open(app_py, 'w', encoding='utf-8') as f:
    f.write(content)
print('Cleaned debug code')
