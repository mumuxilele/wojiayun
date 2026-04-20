#!/usr/bin/env python3
"""修复服务器上的语法错误"""

import re

filepath = '/www/wwwroot/wojiayun/business-admin/app.py'

with open(filepath, 'r') as f:
    content = f.read()

# Fix line 539: missing closing braces
content = content.replace("'overview': {}})", "'overview': {}}}})")

# Write back
with open(filepath, 'w') as f:
    f.write(content)

print('Syntax fixed!')