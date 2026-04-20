#!/usr/bin/env python3
import re

html_file = '/www/wwwroot/wojiayun/business-userH5/application_form_v2.html'

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 隐藏页面标题
content = content.replace(
    '<div class="page-title" id="pageTitle">填写申请</div>',
    '<div class="page-title" id="pageTitle" style="display:none">填写申请</div>'
)

# 2. 隐藏"申请标题"输入框
content = content.replace(
    '''<div class="form-item">
                        <label class="form-label"><span class="required">*</span>申请标题</label>
                        <input type="text" class="form-input" id="title" placeholder="请输入申请标题" required>
                    </div>''',
    '''<div class="form-item" style="display:none">
                        <label class="form-label"><span class="required">*</span>申请标题</label>
                        <input type="text" class="form-input" id="title" placeholder="请输入申请标题">
                    </div>'''
)

# 3. 修改title验证 - 如果为空自动用类型名填充
content = content.replace(
    "const title = document.getElementById('title').value.trim();",
    "const title = document.getElementById('title').value.trim() || (typeof appType !== 'undefined' && appType ? appType.type_name : '申请');"
)

# 4. 修改提交时的title - 同样自动填充
content = content.replace(
    "title: document.getElementById('title').value,",
    "title: document.getElementById('title').value.trim() || (typeof appType !== 'undefined' && appType ? appType.type_name : '申请'),"
)

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - hid page title and title input, auto-fill title on submit')
