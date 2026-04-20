#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

app_file = '/www/wwwroot/wojiayun/business-admin/app.py'

# Read file with proper encoding
with open(app_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if overdue endpoint already exists
if '/api/admin/applications/overdue' in content:
    print("Overdue endpoint already exists")
    sys.exit(0)

# Find the __name__ line
lines = content.split('\n')
main_line = -1
for i, line in enumerate(lines):
    if "__name__" in line and "__main__" in line:
        main_line = i
        break

if main_line == -1:
    print("ERROR: Could not find __name__ line")
    sys.exit(1)

# New endpoint code
new_code = '''

# ============ 超时申请统计 V44.0新增 ============
@app.route('/api/admin/applications/overdue', methods=['GET'])
def admin_overdue_applications():
    """V44.0: 获取超时申请单统计（管理员视角）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    from business_common.application_monitor import get_overdue_statistics
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    stats = get_overdue_statistics(ec_id=ec_id, project_id=project_id)
    return jsonify({'success': True, 'data': stats})

'''

# Insert before the __name__ line
lines.insert(main_line, new_code)

# Write back with UTF-8
with open(app_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('Done - overdue endpoint added')
