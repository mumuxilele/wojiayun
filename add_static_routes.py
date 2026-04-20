#!/usr/bin/env python3

with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add static file routes before if __name__
static_routes = '''
from flask import send_from_directory
import os

@app.route('/business-admin/<path:filename>')
def serve_admin_static(filename):
    """提供 admin 目录的静态文件"""
    static_dir = os.path.dirname(__file__)
    return send_from_directory(static_dir, filename)

'''

if 'serve_admin_static' not in content:
    idx = content.find('if __name__')
    if idx > 0:
        content = content[:idx] + static_routes + content[idx:]
        with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Added static routes")
    else:
        print("Could not find if __name__")
else:
    print("Routes already exist")
