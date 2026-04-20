# -*- coding: utf-8 -*-
import os, re

d = '/www/wwwroot/wojiayun/business-admin/'

fixes = [
    ('feedback.html',
     '<a onclick="showDetail(${fb.id})">\u8be6\u60c5</a>\n                    <a onclick="showReply(${fb.id})">\u56de\u590d</a>',
     '<button class="el-button el-button--small" onclick="showDetail(${fb.id})">\u8be6\u60c5</button>\n                    <button class="el-button el-button--small el-button--primary" onclick="showReply(${fb.id})">\u56de\u590d</button>'
    ),
    ('shops.html',
     '<a onclick="viewShop(${item.id})">\u67e5\u770b</a>\n                                <a onclick="editShop(${item.id})">\u7f16\u8f91</a>\n                                <a class="danger" onclick="deleteShop(${item.id}, \'${(item.shop_name||\'\').replace(/\'/g, \'\')}\')">\u5220\u9664</a>',
     '<button class="el-button el-button--small" onclick="viewShop(${item.id})">\u67e5\u770b</button>\n                                <button class="el-button el-button--small el-button--primary" onclick="editShop(${item.id})">\u7f16\u8f91</button>\n                                <button class="el-button el-button--small el-button--danger" onclick="deleteShop(${item.id}, \'${(item.shop_name||\'\').replace(/\'/g, \'\')}\')">\u5220\u9664</button>'
    ),
    ('points.html',
     '<a onclick="openAdjustModal(${m.user_id},\'${m.user_name||\'\'}\',${m.points||0})">\u8c03\u6574\u79ef\u5206</a><a onclick="viewMemberLogs(${m.user_id})">\u67e5\u770b\u8bb0\u5f55</a>',
     '<button class="el-button el-button--small el-button--primary" onclick="openAdjustModal(${m.user_id},\'${m.user_name||\'\'}\',${m.points||0})">\u8c03\u6574\u79ef\u5206</button><button class="el-button el-button--small" onclick="viewMemberLogs(${m.user_id})">\u67e5\u770b\u8bb0\u5f55</button>'
    ),
    ('index.html',
     '<a class="link" onclick="viewApp(\' + item.id + \')">\u67e5\u770b</a>',
     '<button class="el-button el-button--small" onclick="viewApp(\' + item.id + \')">\u67e5\u770b</button>'
    ),
]

for fname, old, new in fixes:
    path = d + fname
    if not os.path.exists(path):
        print(f'NOT FOUND: {fname}')
        continue
    c = open(path, encoding='utf-8', errors='ignore').read()
    if old in c:
        c = c.replace(old, new)
        open(path, 'w', encoding='utf-8').write(c)
        print(f'FIXED: {fname}')
    else:
        print(f'NOT FOUND: {fname}')
        idx = c.find('onclick="viewApp')
        if idx >= 0:
            print(f'  Context: {repr(c[max(0,idx-50):idx+200])}')

# Fix group-buy.html - btn-sm to el-button--small
f = d + 'group-buy.html'
c = open(f, encoding='utf-8', errors='ignore').read()
# Use regex for dynamic content
p1 = re.compile(r'<button class="btn btn-sm" onclick="viewOrders\(\'\$\{item\.activity_no\}\'\)">([^<]+)</button>')
c = p1.sub(r'<button class="el-button el-button--small" onclick="viewOrders(\'${item.activity_no}\')">\1</button>', c)
p2 = re.compile(r'<button class="btn btn-sm \$\{item\.status === \'ongoing\' \? \'btn-warning\' : \'btn-success\'\}" onclick="toggleStatus\(\$\{item\.id\}, \'\$\{item\.status\}\'\)">\$\{item\.status === \'ongoing\' \? \'([^\']+)\' : \'([^\']+)\'\}</button>')
c = p2.sub(r'<button class="el-button el-button--small ${item.status === \'ongoing\' ? \'el-button--warning\' : \'el-button--success\'}" onclick="toggleStatus(${item.id}, \'${item.status}\')">${item.status === \'ongoing\' ? \'\1\' : \'\2\'}</button>', c)
open(f, 'w', encoding='utf-8').write(c)
print(f'Fixed group-buy.html')

# Fix promotions.html
f = d + 'promotions.html'
c = open(f, encoding='utf-8', errors='ignore').read()
p1 = re.compile(r'<button class="btn btn-default btn-sm" onclick="viewStats\(\' \+ p\.id \+ \'\)">([^<]+)</button>')
c = p1.sub(r'<button class="el-button el-button--small" onclick="viewStats(\' + p.id + \')">\1</button>', c)
p2 = re.compile(r'<button class="btn btn-primary btn-sm" onclick="openEdit\(\' \+ JSON\.stringify\(p\)\.replace\(/g,\'&quot;\'\) \+ \'\)">([^<]+)</button>')
c = p2.sub(r'<button class="el-button el-button--small el-button--primary" onclick="openEdit(\' + JSON.stringify(p).replace(/"/g,\'&quot;\') + \')">\1</button>', c)
open(f, 'w', encoding='utf-8').write(c)
print(f'Fixed promotions.html')

# Fix points-mall.html
f = d + 'points-mall.html'
c = open(f, encoding='utf-8', errors='ignore').read()
p1 = re.compile(r'<button class="btn btn-sm" onclick="editGoods\(\$\{item\.id\}\)">([^<]+)</button>')
c = p1.sub(r'<button class="el-button el-button--small el-button--primary" onclick="editGoods(${item.id})">\1</button>', c)
p2 = re.compile(r'<button class="btn btn-sm \$\{item\.status === \'active\' \? \'btn-warning\' : \'btn-success\'\}" onclick="toggleStatus\(\$\{item\.id\}, \'\$\{item\.status\}\'\)">')
c = p2.sub(r'<button class="el-button el-button--small ${item.status === \'active\' ? \'el-button--warning\' : \'el-button--success\'}" onclick="toggleStatus(${item.id}, \'${item.status}\')">', c)
open(f, 'w', encoding='utf-8').write(c)
print(f'Fixed points-mall.html')

print('Done.')
