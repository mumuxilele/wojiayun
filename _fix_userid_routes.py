content = open('/www/wwwroot/wojiayun/business-admin/app.py', encoding='utf-8').read()

# Find all int:user_id patterns
import re
matches = re.findall(r"'/api/admin/users/<int:user_id>[^']*'", content)
print('Found <int:user_id> routes:')
for m in matches:
    print(' ', m)

# Fix: <int:user_id> -> <user_id>
count = content.count("'/api/admin/users/<int:user_id>")
content = content.replace("'/api/admin/users/<int:user_id>", "'/api/admin/users/<user_id>")
print(f'Fixed {count} occurrences')

open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8').write(content)
print('Done.')
