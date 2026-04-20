f = '/www/wwwroot/wojiayun/business-admin/index.html'
c = open(f, encoding='utf-8', errors='ignore').read()
old = "<a onclick=\"viewApp(\\' + item.id + \\')\">查看</a></td></tr>"
new = "<button class=\"el-button el-button--small\" onclick=\"viewApp(\\' + item.id + \\')\">查看</button></td></tr>"
if old in c:
    c = c.replace(old, new)
    open(f, 'w', encoding='utf-8').write(c)
    print('FIXED: index.html')
else:
    print('NOT FOUND')
