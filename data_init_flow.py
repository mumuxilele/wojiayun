#!/usr/bin/env python3
"""
我家云开放平台 - 数据初始化完整流程
=============================================
流程步骤：
1. 获取授权Token
2. 创建项目（小区）
3. 创建楼栋
4. 创建单元
5. 创建房间
6. 创建客户/业主
7. 房间关联业主
=============================================
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

# 输出文件
OUTPUT_FILE = "/workspace/init_result.json"

# ============ 签名算法 ============
def calculate_signature(app_key, app_secret, client_time, version="V1.0"):
    """计算签名"""
    param_string = f"appKey={app_key}&clientTime={client_time}&version={version}&{app_secret}"
    md5_hash = hashlib.md5(param_string.encode('utf-8')).hexdigest()
    sha1_hash = hashlib.sha1(md5_hash.encode('utf-8')).hexdigest()
    return sha1_hash

# ============ 获取 Token ============
def get_token():
    """获取Token"""
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
        return result["data"]["access_token"]

# ============ API调用 ============
def call_api(access_token, api_path, data, method="POST"):
    """通用API调用"""
    url = f"{API_HOST}{api_path}"
    data["access_token"] = access_token
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except urllib.error.HTTPError as e:
        return {"success": False, "msg": f"HTTP {e.code}: {e.reason}"}

# ============ 步骤1: 创建项目 ============
def create_project(access_token, project_data):
    """创建项目/小区"""
    print("\n【步骤1】创建项目...")
    result = call_api(access_token, "/api/projects/sync_project", {
        "list": [project_data]
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

# ============ 步骤2: 创建楼栋 ============
def create_buildings(access_token, project_id, buildings):
    """批量创建楼栋"""
    print("\n【步骤2】创建楼栋...")
    result = call_api(access_token, "/api/buildings/sSave", {
        "projectID": project_id,
        "list": buildings
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

# ============ 步骤3: 创建单元 ============
def create_units(access_token, project_id, units):
    """批量创建单元"""
    print("\n【步骤3】创建单元...")
    # 接口地址待确认: /api/units/sSave
    result = call_api(access_token, "/api/units/sSave", {
        "projectID": project_id,
        "list": units
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

# ============ 步骤4: 创建房间 ============
def create_rooms(access_token, project_id, rooms):
    """批量创建房间"""
    print("\n【步骤4】创建房间...")
    # 接口地址待确认: /api/rooms/sSave
    result = call_api(access_token, "/api/rooms/sSave", {
        "projectID": project_id,
        "list": rooms
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

# ============ 步骤5: 创建客户/业主 ============
def create_customers(access_token, customers):
    """批量创建客户/业主"""
    print("\n【步骤5】创建客户/业主...")
    # 接口地址待确认: /api/owners/save 或 /api/customers/save
    result = call_api(access_token, "/api/owners/save", {
        "list": customers
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

# ============ 步骤6: 房间关联业主 ============
def bind_owner_room(access_token, room_id, owner_id):
    """房间关联业主"""
    print("\n【步骤6】房间关联业主...")
    # 接口地址待确认
    result = call_api(access_token, "/api/roomOwner/bind", {
        "roomID": room_id,
        "ownerID": owner_id
    })
    print(f"  结果: {result.get('msg', result)}")
    return result

# ============ 名称转拼音 ============
def to_pinyin(name):
    """简单中文转拼音"""
    mapping = {
        '泰': 'tai', '华': 'hua', '大': 'da', '厦': 'xia',
        '栋': 'dong', '号': 'hao', '楼': 'lou', '区': 'qu',
        '园': 'yuan', '路': 'lu', '街': 'jie', '道': 'dao',
        '座': 'zuo', '期': 'qi', '栋': 'dong', '单元': 'danyuan'
    }
    result = ''
    for char in name:
        result += mapping.get(char, char)
    return result

# ============ 示例数据 ============
def generate_demo_data():
    """生成示例初始化数据"""
    data = {
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
            # 每个楼栋2个单元
            {"buildingName": "泰华大厦1栋", "name": "1单元", "number": "1dong1dy"},
            {"buildingName": "泰华大厦1栋", "name": "2单元", "number": "1dong2dy"},
            {"buildingName": "泰华大厦2栋", "name": "1单元", "number": "2dong1dy"},
            {"buildingName": "泰华大厦2栋", "name": "2单元", "number": "2dong2dy"},
            {"buildingName": "泰华大厦3栋", "name": "1单元", "number": "3dong1dy"},
            {"buildingName": "泰华大厦3栋", "name": "2单元", "number": "3dong2dy"},
        ],
        "rooms": [
            # 每个单元5层，每层4户
            {"buildingName": "泰华大厦1栋", "unitName": "1单元", "floor": 1, "roomNo": "01", "area": 89.5},
            {"buildingName": "泰华大厦1栋", "unitName": "1单元", "floor": 1, "roomNo": "02", "area": 92.3},
            {"buildingName": "泰华大厦1栋", "unitName": "1单元", "floor": 1, "roomNo": "03", "area": 85.0},
            {"buildingName": "泰华大厦1栋", "unitName": "1单元", "floor": 1, "roomNo": "04", "area": 120.5},
        ],
        "customers": [
            {
                "name": "张三",
                "phone": "13800138001",
                "idCard": "440300199001011234",
                "roomInfo": "泰华大厦1栋1单元101"
            },
            {
                "name": "李四",
                "phone": "13800138002",
                "idCard": "440300199002022345",
                "roomInfo": "泰华大厦1栋1单元102"
            },
        ]
    }
    return data

# ============ 主流程 ============
def main():
    print("=" * 60)
    print("我家云开放平台 - 数据初始化流程")
    print("=" * 60)
    
    # 获取Token
    print("\n【获取授权Token】")
    try:
        access_token = get_token()
        print(f"  ✓ Token获取成功")
    except Exception as e:
        print(f"  ✗ 获取Token失败: {e}")
        return
    
    # 生成示例数据
    demo_data = generate_demo_data()
    
    results = {
        "project": None,
        "buildings": None,
        "units": None,
        "rooms": None,
        "customers": None,
        "bindings": []
    }
    
    # 步骤1: 创建项目
    print("\n" + "=" * 40)
    project_result = create_project(access_token, demo_data["project"])
    results["project"] = project_result
    
    # 步骤2: 创建楼栋
    buildings = []
    for b in demo_data["buildings"]:
        buildings.append({
            "name": b["name"],
            "number": to_pinyin(b["name"]),
            "overCount": b["overCount"],
            "underCount": b.get("underCount", 0)
        })
    building_result = create_buildings(access_token, PID, buildings)
    results["buildings"] = building_result
    
    # 步骤3: 创建单元 (待确认接口)
    # units = []
    # for u in demo_data["units"]:
    #     units.append({
    #         "name": u["name"],
    #         "number": u["number"],
    #         "buildingName": u["buildingName"]
    #     })
    # unit_result = create_units(access_token, PID, units)
    # results["units"] = unit_result
    
    # 步骤4: 创建房间 (待确认接口)
    # rooms = []
    # for r in demo_data["rooms"]:
    #     rooms.append({
    #         "name": f"{r['floor']}{r['roomNo']}",
    #         "number": to_pinyin(f"{r['buildingName']}{r['unitName']}{r['floor']}{r['roomNo']}"),
    #         "buildingName": r["buildingName"],
    #         "unitName": r["unitName"],
    #         "floor": r["floor"],
    #         "roomNo": r["roomNo"],
    #         "area": r["area"]
    #     })
    # room_result = create_rooms(access_token, PID, rooms)
    # results["rooms"] = room_result
    
    # 步骤5: 创建客户 (待确认接口)
    # customers = []
    # for c in demo_data["customers"]:
    #     customers.append({
    #         "name": c["name"],
    #         "phone": c["phone"],
    #         "idCard": c["idCard"]
    #     })
    # customer_result = create_customers(access_token, customers)
    # results["customers"] = customer_result
    
    # 保存结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("初始化流程完成!")
    print(f"结果已保存到: {OUTPUT_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
