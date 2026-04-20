# 统一管理后台操作列按钮样式
# 将纯文字链接 <a class="link"> 改为 el-button el-button--small 统一按钮

import re

admin_dir = '/www/wwwroot/wojiayun/business-admin/'

# 需要统一操作列按钮的文件
files = {
    'users.html': {
        # 操作列替换
        'find': '<td class="actions">\n                                <a href="member-profile.html?access_token=${encodeURIComponent(token)}&isdev=${isdev}&user_id=${m.user_id}" target="_blank">画像</a>\n                                <a href="points.html?access_token=${encodeURIComponent(token)}&isdev=${isdev}" target="_blank">积分管理</a>\n                            </td>',
        'replace': '''<td>
                                <div class="actions">
                                    <a href="member-profile.html?access_token=${encodeURIComponent(token)}&isdev=${isdev}&user_id=${m.user_id}" target="_blank"><button class="el-button el-button--small el-button--primary">画像</button></a>
                                    <a href="points.html?access_token=${encodeURIComponent(token)}&isdev=${isdev}" target="_blank"><button class="el-button el-button--small">积分管理</button></a>
                                </div>
                            </td>''',
    },
}

for filename, changes in files.items():
    path = admin_dir + filename
    content = open(path, encoding='utf-8').read()
    if changes['find'] in content:
        content = content.replace(changes['find'], changes['replace'])
        open(path, 'w', encoding='utf-8').write(content)
        print(f'Fixed: {filename}')
    else:
        print(f'NOT FOUND in {filename}:')
        # Show around the actions area
        idx = content.find('class="actions"')
        if idx >= 0:
            print(repr(content[max(0,idx-100):idx+300]))
        else:
            print('No "class=actions" found')

print('Done.')
