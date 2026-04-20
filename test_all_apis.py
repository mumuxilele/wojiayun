#!/usr/bin/env python3
"""
API 接口批量测试脚本
测试 web 端(管理后台)、员工端 H5、用户端 H5 的所有接口
"""
import requests
import json
from urllib.parse import urljoin

# 配置
BASE_URLS = {
    'admin': 'http://47.98.238.209:22313',      # 管理后台
    'staff': 'http://47.98.238.209:22312',      # 员工端 H5
    'user': 'http://47.98.238.209:22311',       # 用户端 H5
}

TOKENS = {
    'admin_staff': '91be24cf4e3ed8b0c64338a5afb8dff16ee058c897c1cd6e95342e1264ba2cb6',
    'user': '37e6d1986107360c5422762c89cdda9f07eb226db3bc78debd3766798bf27f74'
}

# 接口列表
APIS = {
    'admin': [
        # GET 接口
        {'method': 'GET', 'path': '/api/admin/userinfo', 'name': '获取管理员信息'},
        {'method': 'GET', 'path': '/api/admin/statistics', 'name': '统计数据'},
        {'method': 'GET', 'path': '/api/admin/statistics/overview', 'name': '统计概览'},
        {'method': 'GET', 'path': '/api/admin/statistics/trend', 'name': '趋势统计'},
        {'method': 'GET', 'path': '/api/admin/products/top', 'name': '热销商品'},
        {'method': 'GET', 'path': '/api/admin/statistics/refund-analysis', 'name': '退款分析'},
        {'method': 'GET', 'path': '/api/admin/statistics/member-growth', 'name': '会员增长'},
        {'method': 'GET', 'path': '/api/admin/statistics/inventory-warning', 'name': '库存预警'},
        {'method': 'GET', 'path': '/api/admin/applications', 'name': '申请列表'},
        {'method': 'GET', 'path': '/api/admin/orders', 'name': '订单列表'},
        {'method': 'GET', 'path': '/api/admin/shops', 'name': '店铺列表'},
        {'method': 'GET', 'path': '/api/admin/products', 'name': '商品列表'},
        {'method': 'GET', 'path': '/api/admin/users', 'name': '用户列表'},
        {'method': 'GET', 'path': '/api/admin/venues', 'name': '场馆列表'},
        {'method': 'GET', 'path': '/api/admin/members', 'name': '会员列表'},
        {'method': 'GET', 'path': '/api/admin/points/stats', 'name': '积分统计'},
        {'method': 'GET', 'path': '/api/admin/visits', 'name': '走访记录'},
        {'method': 'GET', 'path': '/api/admin/promotions', 'name': '促销活动'},
        {'method': 'GET', 'path': '/api/admin/refund-orders', 'name': '退款订单'},
    ],
    'staff': [
        {'method': 'GET', 'path': '/api/staff/userinfo', 'name': '员工信息'},
        {'method': 'GET', 'path': '/api/staff/orders', 'name': '员工端订单'},
        {'method': 'GET', 'path': '/api/staff/applications', 'name': '申请审批列表'},
        {'method': 'GET', 'path': '/api/staff/visits', 'name': '走访列表'},
        {'method': 'GET', 'path': '/api/staff/customers/search', 'name': '客户搜索'},
        {'method': 'GET', 'path': '/api/staff/dashboard', 'name': '员工仪表盘'},
    ],
    'user': [
        {'method': 'GET', 'path': '/api/user/userinfo', 'name': '用户信息'},
        {'method': 'GET', 'path': '/api/user/stats', 'name': '用户统计'},
        {'method': 'GET', 'path': '/api/user/products', 'name': '商品列表'},
        {'method': 'GET', 'path': '/api/user/orders', 'name': '订单列表'},
        {'method': 'GET', 'path': '/api/user/cart', 'name': '购物车'},
        {'method': 'GET', 'path': '/api/user/favorites', 'name': '收藏列表'},
        {'method': 'GET', 'path': '/api/user/coupons', 'name': '优惠券'},
        {'method': 'GET', 'path': '/api/user/points', 'name': '积分'},
        {'method': 'GET', 'path': '/api/user/venues', 'name': '场馆列表'},
        {'method': 'GET', 'path': '/api/user/application/types', 'name': '申请类型'},
        {'method': 'GET', 'path': '/api/user/applications/v2', 'name': '我的申请列表'},
        {'method': 'GET', 'path': '/api/user/applications/v2/favorites', 'name': '常用申请'},
        {'method': 'GET', 'path': '/api/v2/rooms', 'name': '房间列表'},
    ]
}

def test_api(base_url, path, method, token, name):
    """测试单个接口"""
    url = f"{base_url}{path}?access_token={token}"
    try:
        if method == 'GET':
            resp = requests.get(url, timeout=10)
        else:
            resp = requests.post(url, timeout=10)
        
        status = resp.status_code
        try:
            data = resp.json()
            if data.get('success') or status == 200:
                return {'status': 'OK', 'code': status, 'msg': '正常'}
            else:
                return {'status': 'WARN', 'code': status, 'msg': data.get('msg', '业务错误')}
        except:
            if status == 200:
                return {'status': 'OK', 'code': status, 'msg': '正常'}
            else:
                return {'status': 'ERROR', 'code': status, 'msg': '请求失败'}
    except requests.exceptions.Timeout:
        return {'status': 'ERROR', 'code': 0, 'msg': '超时'}
    except Exception as e:
        return {'status': 'ERROR', 'code': 0, 'msg': str(e)[:50]}

def run_tests():
    """运行所有测试"""
    results = {
        'admin': [],
        'staff': [],
        'user': []
    }
    
    print("=" * 70)
    print("API 接口批量测试")
    print("=" * 70)
    
    # 测试管理后台 (admin)
    print("\n【管理后台 - 端口 22313】")
    token = TOKENS['admin_staff']
    for api in APIS['admin']:
        result = test_api(BASE_URLS['admin'], api['path'], api['method'], token, api['name'])
        results['admin'].append({**api, **result})
        status_icon = "✅" if result['status'] == 'OK' else "⚠️" if result['status'] == 'WARN' else "❌"
        print(f"  {status_icon} {api['name']}: {result['code']} - {result['msg']}")
    
    # 测试员工端 (staff)
    print("\n【员工端 H5 - 端口 22312】")
    for api in APIS['staff']:
        result = test_api(BASE_URLS['staff'], api['path'], api['method'], token, api['name'])
        results['staff'].append({**api, **result})
        status_icon = "✅" if result['status'] == 'OK' else "⚠️" if result['status'] == 'WARN' else "❌"
        print(f"  {status_icon} {api['name']}: {result['code']} - {result['msg']}")
    
    # 测试用户端 (user)
    print("\n【用户端 H5 - 端口 22311】")
    token = TOKENS['user']
    for api in APIS['user']:
        result = test_api(BASE_URLS['user'], api['path'], api['method'], token, api['name'])
        results['user'].append({**api, **result})
        status_icon = "✅" if result['status'] == 'OK' else "⚠️" if result['status'] == 'WARN' else "❌"
        print(f"  {status_icon} {api['name']}: {result['code']} - {result['msg']}")
    
    # 汇总
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    for service in ['admin', 'staff', 'user']:
        total = len(results[service])
        ok = sum(1 for r in results[service] if r['status'] == 'OK')
        warn = sum(1 for r in results[service] if r['status'] == 'WARN')
        error = sum(1 for r in results[service] if r['status'] == 'ERROR')
        print(f"\n{service.upper()} 端: 总计 {total} | ✅ 正常 {ok} | ⚠️ 警告 {warn} | ❌ 错误 {error}")
        
        # 显示失败的接口
        failed = [r for r in results[service] if r['status'] != 'OK']
        if failed:
            print("  异常接口:")
            for f in failed:
                print(f"    - {f['name']}: {f['msg']}")
    
    return results

if __name__ == '__main__':
    run_tests()
