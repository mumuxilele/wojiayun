#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business-common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换logging为print
content = content.replace(
    'import logging\n        logging.info(f"[DEBUG application_service] get_application_type called with type_code={type_code}")',
    'print(f"[DEBUG] get_application_type called, type_code={type_code}", flush=True)'
)
content = content.replace(
    'logging.info(f"[DEBUG application_service] get_application_type({type_code}) result: {t}")',
    'print(f"[DEBUG] get_application_type({type_code}) result={t}", flush=True)'
)

with open(svc_py, 'w', encoding='utf-8') as f:
    f.write(content)
print('✅ 已替换为 print()')
