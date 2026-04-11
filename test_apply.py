#!/usr/bin/env python3
"""测试申请提交"""
import requests
import json

url = 'http://47.98.238.209:22311/api/user/applications/v2'
params = {'access_token': 'cb0cf8ade6a3361e0c2eb4a69a16024d9aba0c726ccaab84163c3d96153475bc'}
data = {
    "type_code": "overtime",
    "title": "测试加班申请",
    "form_data": {
        "overtime_date": "2026-04-11",
        "start_time": "18:00",
        "end_time": "20:00",
        "area": "A座办公区",
        "people_count": 5,
        "reason": "项目紧急需要加班"
    },
    "remark": "测试备注"
}

try:
    resp = requests.post(url, params=params, json=data, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
