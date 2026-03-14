#!/usr/bin/env python3
"""
我家云开放平台 - 完整数据初始化流程
支持: 项目 -> 楼栋 -> 单元 -> 房间 -> 客户关系
"""

import json
import time
import hashlib
import urllib.request
import urllib.parse
import ssl
import os

# ============ 配置参数 ============
APP_KEY = "6w6caainm1he2hhg"
APP_SECRET = "gbxvr8hyti3vt29194e9zif6xu5164sg"
PID = "319c23c4c60e4def9959c776c32ca7f9"
NUMBER = "18820487064"
API_HOST = "https://api.wojiacloud.cn"

# Token 缓存
TOKEN_CACHE_FILE = "/workspace/token_cache.json"
TOKEN_EXPIRE_SECONDS = 24 * 60 * 60

# ============ 工具函数 ============
def calculate_signature(app_key, app_secret, client_time, version="V1.0"):
    param_string = f"appKey={app_key}&clientTime={client_time}&version={version}&{app_secret}"
    md5_hash = hashlib.md5(param_string.encode('utf-8')).hexdigest()
    return hashlib.sha1(md5_hash.encode('utf-8')).hexdigest()

def load_token():
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE, 'r') as f:
                cache = json.load(f)
            if time.time() - cache.get('timestamp', 0) < TOKEN_EXPIRE_SECONDS:
                print(f"✓ 使用缓存 Token")
                return cache.get('token')
        except:
            pass
    return None

def save_token(token):
    with open(TOKEN_CACHE_FILE, 'w') as f:
        json.dump({'token': token, 'timestamp': time.time()}, f)
    print(f"✓ Token 已缓存")

def get_token():
    cached = load_token()
    if cached:
        return cached
    
    client_time = int(time.time() * 1000)
    signature = calculate_signature(APP_KEY, APP_SECRET, client_time)
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # 获取 Ticket
    url = f"{API_HOST}/api/users/ticket?appKey={APP_KEY}&clientTime={client_time}&version=V1.0&signature={signature}"
    ticket = json.loads(urllib.request.urlopen(url, context=ctx).read())['data']['ticket']
    
    # 获取 Access Token
    data = urllib.parse.urlencode({
        "ticket": ticket, "username": NUMBER, "pid": PID, "type": "2", "source": "OpenClaw"
    }).encode()
    req = urllib.request.Request(f"{API_HOST}/api/users/access_token", data=data, 
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'})
    token = json.loads(urllib.request.urlopen(req, context=ctx).read())['data']['access_token']
    
    save_token(token)
    return token

def call_api(access_token, api_path, params):
    """Form 方式提交"""
    url = f"{API_HOST}{api_path}?access_token={access_token}"
    
    form_data = {}
    for key, value in params.items():
        form_data[key] = json.dumps(value) if isinstance(value, (list, dict)) else value
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, data=urllib.parse.urlencode(form_data).encode(),
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'})
    return json.loads(urllib.request.urlopen(req, context=ctx).read())

def call_api_with_pid(access_token, api_path, params):
    """带 pid 参数的 Form 提交"""
    url = f"{API_HOST}{api_path}?access_token={access_token}"
    
    form_data = {"pid": PID}
    for key, value in params.items():
        form_data[key] = json.dumps(value) if isinstance(value, (list, dict)) else value
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, data=urllib.parse.urlencode(form_data).encode(),
                                  headers={'Content-Type': 'application/x-www-form-urlencoded'})
    return json.loads(urllib.request.urlopen(req, context=ctx).read())

# ============ 数据初始化 ============

def create_project(access_token, project):
    """创建项目"""
    print("\n【1. 创建项目】")
    result = call_api(access_token, "/api/projects/sync_project", {"list": [project]})
    print(f"  结果: {result.get('msg', result)}")
    return result

def create_buildings(access_token, buildings):
    """创建楼栋"""
    print("\n【2. 创建楼栋】")
    result = call_api(access_token, "/api/buildings/sSave", {
        "projectID": PID,
        "list": buildings
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

def create_units(access_token, units):
    """创建单元"""
    print("\n【3. 创建单元】")
    # 接口: /api/buildUnit/sSave
    # 必填: projectID, list[name, buildNumber]
    result = call_api(access_token, "/api/buildUnit/sSave", {
        "projectID": PID,
        "list": units
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

def create_rooms(access_token, rooms):
    """创建房间"""
    print("\n【4. 创建房间】")
    # 接口: /api/rooms/sSave
    # 必填: projectID, list[buildingName, floor, roomName, roomNumber, property, buildingArea, roomArea, chargeArea, productName]
    result = call_api(access_token, "/api/rooms/sSave", {
        "projectID": PID,
        "list": rooms
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

def bind_room_customer(access_token, room_customers):
    """房间客户关系同步"""
    print("\n【5. 绑定房间客户关系】")
    # 接口: /api/rooms/addroomcus
    # 必填: rooms[buildingName, roomName, roomNumber, property, customerType, joinDate, type, customerName, phone]
    result = call_api_with_pid(access_token, "/api/rooms/addroomcus", {
        "rooms": room_customers
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

def to_pinyin(name):
    mapping = {'泰': 'tai', '华': 'hua', '大': 'da', '厦': 'xia', '栋': 'dong', 
               '号': 'hao', '楼': 'lou', '区': 'qu', '园': 'yuan', '路': 'lu',
               '街': 'jie', '道': 'dao', '座': 'zuo', '期': 'qi', '单元': 'danyuan'}
    return ''.join(mapping.get(c, c) for c in name)

# ============ 主流程 ============
def main():
    print("=" * 60)
    print("我家云开放平台 - 完整数据初始化流程")
    print("=" * 60)
    
    # 获取 Token
    try:
        token = get_token()
    except Exception as e:
        print(f"✗ 获取Token失败: {e}")
        return
    
    # ===== 示例数据 =====
    # 项目
    project = {
        "name": "泰华小区",
        "number": "THXQ001",
        "province": "广东省",
        "city": "深圳市",
        "area": "南山区",
        "address": "科技园南路88号"
    }
    
    # 楼栋
    buildings = [
        {"name": "泰华大厦1栋", "number": "taihuadasha1dong", "overCount": 25, "underCount": 4},
        {"name": "泰华大厦2栋", "number": "taihuadasha2dong", "overCount": 30, "underCount": 3},
    ]
    
    # 单元 (楼栋名称 + 楼栋名称)
    units = [
        {"name": "1单元", "buildNumber": "泰华大厦1栋"},  # 用楼栋名称
        {"name": "2单元", "buildNumber": "泰华大厦1栋"},
        {"name": "1单元", "buildNumber": "泰华大厦2栋"},
    ]
    
    # 房间 (楼栋名称 + 单元名称 + 楼层 + 房间名 + 编码 + 业务属性 + 面积 + 产品类型)
    # property: 0=住宅, 1=商业, 2=工业, 3=车位
    rooms = [
        {
            "buildingName": "泰华大厦1栋",
            "buildUnitName": "1单元",
            "floor": 1,
            "roomName": "101",
            "roomNumber": "taihuadasha1dong1dy101",
            "property": 0,
            "buildingArea": 89.5,
            "roomArea": 75.0,
            "chargeArea": 75.0,
            "productName": "住宅"
        },
        {
            "buildingName": "泰华大厦1栋",
            "buildUnitName": "1单元",
            "floor": 1,
            "roomName": "102",
            "roomNumber": "taihuadasha1dong1dy102",
            "property": 0,
            "buildingArea": 92.3,
            "roomArea": 80.0,
            "chargeArea": 80.0,
            "productName": "住宅"
        },
    ]
    
    # 房间客户关系 (楼栋名称 + 房间名称 + 房间编码 + 业务属性 + 客户类型 + 迁入日期 + 客户类型 + 客户名称 + 手机)
    # customerType: 0=业主, 2=租户
    # type: P=个人, E=企业, S=个体户, G=政府机构, O=其他
    room_customers = [
        {
            "buildingName": "泰华大厦1栋",
            "roomName": "101",
            "roomNumber": "taihuadasha1dong1dy101",
            "property": "0",
            "customerType": "0",  # 业主
            "joinDate": "2024-01-01",
            "type": "P",  # 个人
            "customerName": "张三",
            "phone": "13800138001"
        },
        {
            "buildingName": "泰华大厦1栋",
            "roomName": "102",
            "roomNumber": "taihuadasha1dong1dy102",
            "property": "0",
            "customerType": "0",  # 业主
            "joinDate": "2024-01-01",
            "type": "P",
            "customerName": "李四",
            "phone": "13800138002"
        },
    ]
    
    # ===== 执行流程 =====
    create_project(token, project)
    create_buildings(token, buildings)
    create_units(token, units)
    create_rooms(token, rooms)
    bind_room_customer(token, room_customers)
    
    print("\n" + "=" * 60)
    print("初始化完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
