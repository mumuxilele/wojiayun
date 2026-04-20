# -*- coding: utf-8 -*-
import urllib.request
import json

TOKEN = "37e6d1986107360c5422762c89cdda9f07eb226db3bc78debd3766798bf27f74"
BASE = "http://127.0.0.1:22311"

apis = [
    "stats",
    "info",
    "member",
    "applications/v2",
    "application-types",
    "venues",
    "orders",
    "coupons",
    "points",
    "points-goods",
    "notifications",
    "feedback",
    "cart",
    "addresses",
    "products",
    "group-buy",
    "seckill",
    "reviews",
    "favorites",
    "messages",
]

print("=" * 55)
print("用户端H5接口测试 (端口22311)")
print("=" * 55)

for api in apis:
    url = f"{BASE}/api/user/{api}?access_token={TOKEN}"
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('success'):
            print(f"✓ /api/user/{api}: OK")
        else:
            msg = data.get('msg', '')[:35]
            print(f"✗ /api/user/{api}: {msg}")
    except urllib.error.HTTPError as e:
        print(f"✗ /api/user/{api}: HTTP {e.code}")
    except Exception as e:
        print(f"✗ /api/user/{api}: {str(e)[:30]}")

print("=" * 55)
print("测试完成")
