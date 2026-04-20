#!/usr/bin/env python3

svc_py = '/www/wwwroot/wojiayun/business_common/application_service.py'

with open(svc_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 在文件末尾添加 create_application 方法
method = '''

    @staticmethod
    def create_application(user_id, user_name, user_phone, type_code, title, 
                          form_data=None, ec_id=None, project_id=None, 
                          attachments=None, remark=None):
        """创建申请单"""
        import json
        from datetime import datetime
        from . import db
        
        try:
            # 检查申请类型是否存在
            app_type = ApplicationService.get_application_type(type_code)
            if not app_type:
                return {'success': False, 'msg': '申请类型不存在'}
            
            # 生成申请单号
            app_no = 'APP' + datetime.now().strftime('%Y%m%d%H%M%S') + str(int(datetime.now().timestamp() * 1000))[-4:]
            
            # 序列化表单数据
            form_data_str = json.dumps(form_data, ensure_ascii=False) if form_data else None
            attachments_str = json.dumps(attachments, ensure_ascii=False) if attachments else None
            
            conn = db.get_connection()
            cursor = conn.cursor(db.pymysql.cursors.DictCursor)
            
            sql = """INSERT INTO business_applications 
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
            ))
            conn.commit()
            
            app_id = cursor.lastrowid
            cursor.close()
            conn.close()
            
            return {
                'success': True, 
                'msg': '申请提交成功',
                'data': {
                    'id': app_id,
                    'app_no': app_no,
                    'type_code': type_code,
                    'title': title,
                    'status': 'pending'
                }
            }
        except Exception as e:
            logger.error(f"创建申请单失败: {e}")
            return {'success': False, 'msg': f'提交失败: {str(e)}'}
'''

content = content.rstrip() + method

with open(svc_py, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done - added create_application method')
