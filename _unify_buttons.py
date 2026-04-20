# -*- coding: utf-8 -*-
import os

admin_dir = '/www/wwwroot/wojiayun/business-admin/'

fixes = [
    ('applications.html',
     '<a class="link" onclick="viewApp(${item.id})">查看</a>\n                                <a class="link" onclick="openEdit(${item.id}, \'${item.app_no || \'\'}\')">处理</a>\n                                <a class="link danger" onclick="deleteApp(${item.id})">删除</a>',
     '<button class="el-button el-button--small" onclick="viewApp(${item.id})">查看</button>\n                                <button class="el-button el-button--small el-button--primary" onclick="openEdit(${item.id}, \'${item.app_no || \'\'}\')">处理</button>\n                                <button class="el-button el-button--small el-button--danger" onclick="deleteApp(${item.id})">删除</button>'
    ),

    ('users.html',
     '<td class="actions">\n                                <a href="member-profile.html?access_token=${encodeURIComponent(token)}&isdev=${isdev}&user_id=${m.user_id}" target="_blank">画像</a>\n                                <a href="points.html?access_token=${encodeURIComponent(token)}&isdev=${isdev}" target="_blank">积分管理</a>\n                            </td>',
     '<td>\n                                <div class="actions">\n                                    <a href="member-profile.html?access_token=${encodeURIComponent(token)}&isdev=${isdev}&user_id=${m.user_id}" target="_blank"><button class="el-button el-button--small el-button--primary">画像</button></a>\n                                    <a href="points.html?access_token=${encodeURIComponent(token)}&isdev=${isdev}" target="_blank"><button class="el-button el-button--small">积分管理</button></a>\n                                </div>\n                            </td>'
    ),

    ('notices.html',
     '<button class="btn btn-default" onclick="openEdit(${n.id})">编辑</button>\n                    ${n.status === \'draft\' ? `<button class="btn btn-success" style="padding:4px 10px;font-size:12px" onclick="publishNotice(${n.id})">发布</button>` : \'\'}',
     '<button class="el-button el-button--small" onclick="openEdit(${n.id})">编辑</button>\n                    ${n.status === \'draft\' ? `<button class="el-button el-button--small el-button--success" onclick="publishNotice(${n.id})">发布</button>` : `\'}\''
    ),
]

# Process fixes
for filename, old, new in fixes:
    path = admin_dir + filename
    if not os.path.exists(path):
        print(f'NOT FOUND: {filename}')
        continue
    content = open(path, encoding='utf-8', errors='ignore').read()
    if old in content:
        content = content.replace(old, new)
        open(path, 'w', encoding='utf-8').write(content)
        print(f'FIXED: {filename}')
    else:
        print(f'NOT FOUND: {filename}')
        # find context
        for kw in ['viewApp', 'class="actions"', 'openEdit']:
            idx = content.find(kw)
            if idx >= 0:
                print(f'  Context near "{kw}": {repr(content[max(0,idx-80):idx+200])}')
                break

print('Done.')
