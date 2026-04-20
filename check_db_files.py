#!/usr/bin/env python3
import os, glob

db_files = glob.glob('/www/wwwroot/wojiayun/**/db.py', recursive=True)
for f in db_files:
    with open(f, 'r', encoding='utf-8') as fp:
        content = fp.read()
    has_conn = 'def get_connection' in content
    size = os.path.getsize(f)
    print(f'{"✅" if has_conn else "❌"} {f} ({size} bytes, has get_connection={"Yes" if has_conn else "No"})')
