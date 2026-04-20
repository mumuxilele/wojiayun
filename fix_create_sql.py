#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 SQL - 使用正确的列名
old_sql = '''sql = """INSERT INTO business_applications 
                (app_no, user_id, user_name, user_phone, type_code, type_name, 
                 title, content, form_data, attachments, remark, status,
                 ec_id, project_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(sql, (
                app_no, user_id, user_name, user_phone, type_code, 
                app_type.get('type_name', ''),
                title, remark or '', form_data_str, attachments_str, remark or '',
                'pending', ec_id, project_id, now, now
            ))'''

new_sql = '''sql = """INSERT INTO business_applications 
                (app_no, user_id, user_name, user_phone, app_type, 
                 title, content, form_data, attachments, remark, status,
                 ec_id, project_id, created_at, updated_at, deleted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(sql, (
                app_no, user_id, user_name, user_phone, type_code, 
                title, remark or '', form_data_str, attachments_str, remark or '',
                'pending', ec_id, project_id, now, now, 0
            ))'''

if old_sql in content:
    content = content.replace(old_sql, new_sql)
    with open(svc_py, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done - fixed SQL column names')
else:
    print('ERROR - old SQL not found')
