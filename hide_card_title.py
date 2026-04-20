#!/usr/bin/env python3
file_path = '/www/wwwroot/wojiayun/business-userH5/application_form_v2.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
old = '''                    <div class="card-title">
                        <span>${appType.icon || '📋'}</span>
                        <span>${appType.type_name}</span>
                    </div>'''
new = '''                    <div class="card-title" style="display:none">
                        <span>${appType.icon || '📋'}</span>
                        <span>${appType.type_name}</span>
                    </div>'''
if old in content:
    content = content.replace(old, new, 1)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done - hid first card-title')
else:
    print('ERROR - pattern not found')
