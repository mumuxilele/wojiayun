#!/usr/bin/env python3
import urllib.request
import json

TOKEN = '9f2e0ad4213dba711f73a17a6e538f5c7eb349613ba56d6e83aa0c7cf05b0556'
BASE = 'http://127.0.0.1:22313'

print("=== 页面加载测试 ===")
pages = [
    'index', 'data-board', 'statistics', 'member-levels', 'members',
    'shops', 'orders', 'products', 'coupons', 'promotions',
    'group-buy', 'applications', 'refunds', 'notices', 'points-mall', 'users'
]
for page in pages:
    url = f"{BASE}/business-admin/{page}.html"
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"✓ {page}.html: {resp.status}")
    except Exception as e:
        print(f"✗ {page}.html: {str(e)[:50]}")

print("\n=== API 测试 ===")
apis = [
    '/api/admin/statistics/overview',
    '/api/admin/statistics/trend',
    '/api/admin/members',
    '/api/admin/member-levels',
    '/api/admin/shops',
    '/api/admin/orders',
    '/api/admin/products',
    '/api/admin/coupons',
    '/api/admin/promotions',
    '/api/admin/group-buys',
    '/api/admin/applications',
    '/api/admin/refunds',
    '/api/admin/notices',
    '/api/admin/users',
    '/api/admin/points-mall/goods',
]
for api in apis:
    url = f"{BASE}{api}?access_token={TOKEN}"
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        data = json.loads(resp.read())
        if data.get('success'):
            print(f"✓ {api}")
        else:
            print(f"✗ {api}: {data.get('msg', 'failed')}")
    except Exception as e:
        print(f"✗ {api}: {str(e)[:50]}")
