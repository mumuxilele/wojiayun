#!/usr/bin/env python3
import os

# Read the current app.py
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add static file route for business-common before if __name__ block
static_route = '''
from flask import send_from_directory
import os

@app.route('/business-common/<path:filename>')
def serve_business_common(filename):
    """提供 business-common 目录的静态文件"""
    common_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'business-common')
    return send_from_directory(common_dir, filename)

'''

# Find if route already exists
if 'business-common' in content:
    print("Route already exists")
else:
    # Insert before if __name__
    if '__name__' in content:
        idx = content.find('if __name__')
        content = content[:idx] + static_route + content[idx:]
        with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Added business-common static route")
    else:
        print("Could not find if __name__ block")
