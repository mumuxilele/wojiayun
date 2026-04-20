#!/usr/bin/env python3

# 清理所有调试代码
for path in [
    '/www/wwwroot/wojiayun/business-userH5/app.py',
    '/www/wwwroot/wojiayun/business-common/application_service.py'
]:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 清理 app.py 中的调试
    content = content.replace(
        '    import logging\n    logging.info(f"[DEBUG] get_application_type({type_code}) result: {app_type}")\n    logging.info(f"[DEBUG] user: {user}")\n    app.logger.info(f"[DEBUG] get_application_type({type_code}) result: {app_type}")\n    app.logger.info(f"[DEBUG] user: {user}")\n    app.logger.info(f"[DEBUG] user ecId: {user.get',
        '    app.logger.info'
    )
    content = content.replace(
        '    app.logger.info(f"[DEBUG] get_application_type({type_code}) result: {app_type}")\n    app.logger.info(f"[DEBUG] user: {user}")\n    app.logger.info(f"[DEBUG] user ecId: {user.get',
        '    app.logger.info'
    )
    
    # 清理 application_service.py 中的调试
    content = content.replace(
        'print(f"[DEBUG] get_application_type called, type_code={type_code}", flush=True)\n        ',
        ''
    )
    content = content.replace(
        'print(f"[DEBUG] get_application_type({type_code}) result={t}", flush=True)\n        ',
        ''
    )
    content = content.replace(
        '        print(f"[DEBUG] get_application_type({type_code}) result={t}", flush=True)',
        ''
    )
    content = content.replace(
        'print(f"[DEBUG] get_application_type({type_code}) result={t}", flush=True)\n',
        ''
    )
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'✅ 清理了 {path}')

print('\n清理完成')
