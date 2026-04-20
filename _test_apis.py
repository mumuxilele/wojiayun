#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.request
import urllib.error
import json

TOKEN = "91be24cf4e3ed8b0c64338a5afb8dff16ee058c897c1cd6e95342e1264ba2cb6"
BASE_ADMIN = "http://127.0.0.1:22313"
BASE_STAFF = "http://127.0.0.1:22312"
BASE_USER = "http://127.0.0.1:22311"

def test_api(base, path, desc):
    url = f"{base}{path}?access_token={TOKEN}"
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        data = resp.read().decode('utf-8')
        try:
            j = json.loads(data)
            success = j.get('success', False)
            msg = j.get('msg', '')[:50] if j.get('msg') else ''
            if success:
                return f"✓ {desc}: OK"
            else:
                return f"✗ {desc}: {msg}"
        except:
            return f"? {desc}: {data[:60]}"
    except urllib.error.HTTPError as e:
        return f"✗ {desc}: HTTP {e.code}"
    except Exception as e:
        return f"✗ {desc}: {str(e)[:40]}"

# Admin APIs (22313)
admin_apis = [
    ("/api/admin/stats", "仪表盘统计"),
    ("/api/admin/applications", "申请单列表"),
    ("/api/admin/users", "用户列表"),
    ("/api/admin/products", "商品列表"),
    ("/api/admin/orders", "订单列表"),
    ("/api/admin/coupons", "优惠券列表"),
    ("/api/admin/venues", "场地列表"),
    ("/api/admin/promotions", "促销活动"),
    ("/api/admin/notices", "公告列表"),
    ("/api/admin/feedback", "反馈列表"),
    ("/api/admin/member-levels", "会员等级"),
    ("/api/admin/points-goods", "积分商品"),
]

# Staff APIs (22312)
staff_apis = [
    ("/api/staff/stats", "员工端统计"),
    ("/api/staff/applications", "员工申请单"),
    ("/api/staff/tasks", "员工任务"),
    ("/api/staff/orders", "员工订单"),
    ("/api/staff/venues", "员工场地"),
    ("/api/staff/venue-bookings", "场地预约"),
    ("/api/staff/coupons", "员工优惠券"),
    ("/api/staff/feedback", "员工反馈"),
]

# User APIs (22311) - 用户端H5
user_apis = [
    ("/api/user/stats", "用户统计"),
    ("/api/user/applications/v2", "用户申请单v2"),
    ("/api/user/orders", "用户订单"),
    ("/api/user/venues", "用户场地"),
    ("/api/user/coupons", "用户优惠券"),
    ("/api/user/member", "用户会员信息"),
    ("/api/user/points", "用户积分"),
    ("/api/user/notifications", "用户通知"),
]

print("=" * 60)
print("【Web管理端接口测试】端口 22313")
print("=" * 60)
for path, desc in admin_apis:
    print(test_api(BASE_ADMIN, path, desc))

print("\n" + "=" * 60)
print("【员工端H5接口测试】端口 22312")
print("=" * 60)
for path, desc in staff_apis:
    print(test_api(BASE_STAFF, path, desc))

print("\n" + "=" * 60)
print("【用户端H5接口测试】端口 22311")
print("=" * 60)
for path, desc in user_apis:
    print(test_api(BASE_USER, path, desc))
