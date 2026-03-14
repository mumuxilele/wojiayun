#!/usr/bin/env python3
"""
我家云开放平台 - 数据初始化完整流程
支持 Token 缓存（24小时有效）
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

# Token 缓存文件
TOKEN_CACHE_FILE = "/workspace/token_cache.json"
TOKEN_EXPIRE_SECONDS = 24 * 60 * 60  # 24小时

# ============ 签名算法 ============
def calculate_signature(app_key, app_secret, client_time, version="V1.0"):
    param_string = f"appKey={app_key}&clientTime={client_time}&version={version}&{app_secret}"
    md5_hash = hashlib.md5(param_string.encode('utf-8')).hexdigest()
    sha1_hash = hashlib.sha1(md5_hash.encode('utf-8')).hexdigest()
    return sha1_hash

# ============ Token 缓存 ============
def load_token_from_cache():
    """从缓存加载 token"""
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE, 'r') as f:
                cache = json.load(f)
            # 检查是否过期
            if time.time() - cache.get('timestamp', 0) < TOKEN_EXPIRE_SECONDS:
                print(f"✓ 使用缓存的 Token (缓存时间: {cache.get('timestamp', 0)})")
                return cache.get('token')
            else:
                print("Token 已过期，需要重新获取")
        except:
            pass
    return None

def save_token_to_cache(token):
    """保存 token 到缓存"""
    cache = {
        'token': token,
        'timestamp': time.time()
    }
    with open(TOKEN_CACHE_FILE, 'w') as f:
        json.dump(cache, f)
    print(f"✓ Token 已缓存")

# ============ 获取 Token ============
def get_token():
    """获取 Token（优先使用缓存）"""
    # 尝试从缓存加载
    cached_token = load_token_from_cache()
    if cached_token:
        return cached_token
    
    # 重新获取
    print("重新获取 Token...")
    client_time = int(time.time() * 1000)
    signature = calculate_signature(APP_KEY, APP_SECRET, client_time)
    
    # 获取 Ticket
    params = {
        "appKey": APP_KEY,
        "clientTime": client_time,
        "version": "V1.0",
        "signature": signature
    }
    url = f"{API_HOST}/api/users/ticket?{urllib.parse.urlencode(params)}"
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
        if not result.get("success"):
            raise Exception(f"获取Ticket失败: {result.get('msg')}")
        ticket = result["data"]["ticket"]
    
    # 获取 Access Token
    data = urllib.parse.urlencode({
        "ticket": ticket,
        "username": NUMBER,
        "pid": PID,
        "type": "2",
        "source": "OpenClaw"
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{API_HOST}/api/users/access_token",
        data=data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
        if not result.get("success"):
            raise Exception(f"获取Access Token失败: {result.get('msg')}")
        token = result["data"]["access_token"]
    
    # 缓存 token
    save_token_to_cache(token)
    return token

# ============ API 调用 ============
def call_api(access_token, api_path, params, method="POST"):
    """通用 API 调用（Form 提交方式）"""
    url = f"{API_HOST}{api_path}?access_token={access_token}"
    
    # 构建 Form 数据
    form_data = {}
    for key, value in params.items():
        if isinstance(value, (list, dict)):
            form_data[key] = json.dumps(value)
        else:
            form_data[key] = value
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(form_data).encode('utf-8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except Exception as e:
        return {"success": False, "msg": str(e)}

# ============ 数据初始化函数 ============

def create_project(access_token, project_data):
    """创建项目"""
    print("\n【创建项目】")
    result = call_api(access_token, "/api/projects/sync_project", {
        "list": [project_data]
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

def create_buildings(access_token, buildings):
    """批量创建楼栋"""
    print("\n【创建楼栋】")
    result = call_api(access_token, "/api/buildings/sSave", {
        "projectID": PID,
        "list": buildings
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

def create_units(access_token, units):
    """批量创建单元"""
    print("\n【创建单元】")
    # 接口地址待确认
    result = call_api(access_token, "/api/units/sSave", {
        "projectID": PID,
        "list": units
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

def create_rooms(access_token, rooms):
    """批量创建房间"""
    print("\n【创建房间】")
    # 接口地址待确认
    result = call_api(access_token, "/api/rooms/sSave", {
        "projectID": PID,
        "list": rooms
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

def create_customers(access_token, customers):
    """批量创建客户/业主"""
    print("\n【创建业主】")
    # 接口地址待确认
    result = call_api(access_token, "/api/owners/save", {
        "list": customers
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

# ============ 名称转拼音 ============
def to_pinyin(name):
    mapping = {
        '泰': 'tai', '华': 'hua', '大': 'da', '厦': 'xia',
        '栋': 'dong', '号': 'hao', '楼': 'lou', '区': 'qu',
        '园': 'yuan', '路': 'lu', '街': 'jie', '道': 'dao',
        '座': 'zuo', '期': 'qi', '单元': 'danyuan'
    }
    result = ''
    for char in name:
        result += mapping.get(char, char)
    return result

# ============ 示例数据 ============
def generate_demo_data():
    """生成示例初始化数据"""
    return {
        "project": {
            "name": "泰华小区",
            "number": "THXQ001",
            "province": "广东省",
            "city": "深圳市",
            "area": "南山区",
            "address": "科技园南路88号"
        },
        "buildings": [
            {"name": "泰华大厦1栋", "overCount": 25, "underCount": 4},
            {"name": "泰华大厦2栋", "overCount": 30, "underCount": 3},
            {"name": "泰华大厦3栋", "overCount": 20, "underCount": 2},
        ],
        "units": [
            {"name": "1单元", "buildingName": "泰华大厦1栋"},
            {"name": "2单元", "buildingName": "泰华大厦1栋"},
        ],
        "rooms": [
            {"floor": 1, "roomNo": "101", "area": 89.5},
            {"floor": 1, "roomNo": "102", "area": 92.3},
        ],
        "customers": [
            {"name": "张三", "phone": "13800138001", "idCard": "440300199001011234"},
            {"name": "李四", "phone": "13800138002", "idCard": "440300199002022345"},
        ]
    }

# ============ 主流程 ============
def main():
    print("=" * 60)
    print("我家云开放平台 - 数据初始化流程")
    print("=" * 60)
    
    # 获取 Token（自动缓存）
    try:
        access_token = get_token()
        print(f"✓ Token 准备就绪\n")
    except Exception as e:
        print(f"✗ 获取 Token 失败: {e}")
        return
    
    # 生成数据
    data = generate_demo_data()
    
    # 1. 创建项目
    create_project(access_token, data["project"])
    
    # 2. 创建楼栋
    buildings = []
    for b in data["buildings"]:
        buildings.append({
            "name": b["name"],
            "number": to_pinyin(b["name"]),
            "overCount": b["overCount"],
            "underCount": b.get("underCount", 0)
        })
    create_buildings(access_token, buildings)
    
    # 3. 创建单元（待确认接口）
    # units = [{"name": u["name"], "buildingName": u["buildingName"]} for u in data["units"]]
    # create_units(access_token, units)
    
    # 4. 创建房间（待确认接口）
    # rooms = [{"floor": r["floor"], "roomNo": r["roomNo"], "area": r["area"]} for r in data["rooms"]]
    # create_rooms(access_token, rooms)
    
    # 5. 创建业主（待确认接口）
    # create_customers(access_token, data["customers"])
    
    print("\n" + "=" * 60)
    print("初始化流程完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
