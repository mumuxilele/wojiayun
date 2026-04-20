#!/usr/bin/env python3
import json
result = {"data":{"type_code":"overtime","form_schema":{"fields":[{"name":"overtime_date","type":"date","label":"加班日期"}]}}}
# Just test API directly
import urllib.request
url = 'http://localhost:22311/api/user/application/types/overtime?access_token=571f60c957698b821e7a4fd53f48cf98dffe7bd09c0af3f5086e0e01a2b2f9d4'
try:
    resp = urllib.request.urlopen(url)
    data = json.loads(resp.read())
    fs = data.get('data', {}).get('form_schema', {})
    fields = fs.get('fields', [])
    print(f'success={data.get("success")}')
    print(f'form_schema fields count: {len(fields)}')
    for f in fields:
        print(f'  - {f["name"]}: {f["label"]} ({f["type"]})')
except Exception as e:
    print(f'Error: {e}')
