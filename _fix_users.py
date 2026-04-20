# Fix users.html: filter1 -> levelFilter (id mismatch)
content = open('/www/wwwroot/wojiayun/business-admin/users.html', encoding='utf-8').read()

# Fix 1: select id="filter1" -> id="levelFilter"
content = content.replace('id="filter1"', 'id="levelFilter"')

# Fix 2: getElementById('levelFilter') - already correct, but also check for filter1
content = content.replace("getElementById('filter1')", "getElementById('levelFilter')")

open('/www/wwwroot/wojiayun/business-admin/users.html', 'w', encoding='utf-8').write(content)
print('Fixed: filter1 -> levelFilter in users.html')
print('Occurrences of levelFilter:', content.count('levelFilter'))
