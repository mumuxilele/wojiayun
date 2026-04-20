content = open('/www/wwwroot/wojiayun/business-admin/notices.html', encoding='utf-8').read()
content = content.replace("getElementById('noticeTableBody')", "getElementById('listBody')")
open('/www/wwwroot/wojiayun/business-admin/notices.html', 'w', encoding='utf-8').write(content)
print('fixed: noticeTableBody -> listBody')
