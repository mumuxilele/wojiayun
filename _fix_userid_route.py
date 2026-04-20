content = open('/www/wwwroot/wojiayun/business-admin/app.py', encoding='utf-8').read()

# Fix 1: <int:user_id>/profile -> <user_id>/profile (UUID not int)
count1 = content.count("'/api/admin/users/<int:user_id>/profile'")
content = content.replace("'/api/admin/users/<int:user_id>/profile'", "'/api/admin/users/<user_id>/profile'")
print(f'Fixed {count1} occurrences of int:user_id -> user_id in profile route')

open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8').write(content)
print('Done.')
