#!/usr/bin/env python3
"""
我家云开放平台 - 批量创建楼栋
"""

import json
import time
import hashlib
import urllib.request
import urllib.parse
import ssl

# ============ 配置参数 ============
APP_KEY = "6w6caainm1he2hhg"
APP_SECRET = "gbxvr8hyti3vt29194e9zif6xu5164sg"
PID = "319c23c4c60e4def9959c776c32ca7f9"
NUMBER = "18820487064"
API_HOST = "https://api.wojiacloud.cn"

# 楼栋配置
BUILDING_COUNT = 10  # 创建数量
OVER_COUNT = 25     # 楼上层数
UNDER_COUNT = 4    # 楼下层数
INTERVAL_MINUTES = 0  # 每个楼栋间隔时间（分钟），设为0则立即执行

# ============ 签名算法 ============
def calculate_signature(app_key, app_secret, client_time, version="V1.0"):
    """计算签名：MD5(appKey=xxx&clientTime=xxx&version=V1.0&appSecret) + SHA1"""
    # 按字母顺序排序拼接
    param_string = f"appKey={app_key}&clientTime={client_time}&version={version}&{app_secret}"
    print(f"签名前字符串: {param_string}")
    
    # MD5 加密
    md5_hash = hashlib.md5(param_string.encode('utf-8')).hexdigest()
    print(f"MD5结果: {md5_hash}")
    
    # SHA1 加密 MD5 结果
    sha1_hash = hashlib.sha1(md5_hash.encode('utf-8')).hexdigest()
    print(f"SHA1签名: {sha1_hash}")
    
    return sha1_hash

# ============ 获取 Ticket ============
def get_ticket():
    """获取Ticket令牌"""
    client_time = int(time.time() * 1000)  # 13位时间戳
    signature = calculate_signature(APP_KEY, APP_SECRET, client_time)
    
    params = {
        "appKey": APP_KEY,
        "clientTime": client_time,
        "version": "V1.0",
        "signature": signature
    }
    
    url = f"{API_HOST}/api/users/ticket?{urllib.parse.urlencode(params)}"
    print(f"\n获取Ticket请求URL: {url}")
    
    try:
        # 跳过SSL验证
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"获取Ticket响应: {result}")
            
            if result.get("success") and result.get("data", {}).get("ticket"):
                return result["data"]["ticket"]
            else:
                raise Exception(f"获取Ticket失败: {result.get('msg', '未知错误')}")
    except Exception as e:
        raise Exception(f"获取Ticket请求失败: {str(e)}")

# ============ 获取 Access Token ============
def get_access_token(ticket):
    """获取访问令牌"""
    # 使用 form 提交格式
    data = urllib.parse.urlencode({
        "ticket": ticket,
        "username": NUMBER,
        "pid": PID,
        "type": "2",  # 物业WEB
        "source": "OpenClaw"
    }).encode('utf-8')
    
    url = f"{API_HOST}/api/users/access_token"
    print(f"\n获取Access Token请求: {url}")
    print(f"请求数据: {data.decode('utf-8')}")
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            url, 
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"获取Access Token响应: {result}")
            
            if result.get("success") and result.get("data", {}).get("access_token"):
                return result["data"]["access_token"]
            else:
                raise Exception(f"获取Access Token失败: {result.get('msg', '未知错误')}")
    except Exception as e:
        raise Exception(f"获取Access Token请求失败: {str(e)}")

# ============ 创建楼栋 ============
def create_building(access_token, name, number):
    """创建单个楼栋"""
    # 构建请求数据
    building_data = {
        "name": name,
        "number": number,
        "overCount": OVER_COUNT,
        "underCount": UNDER_COUNT
    }
    
    # 请求体
    req_body = {
        "projectID": PID,
        "list": [building_data]
    }
    
    url = f"{API_HOST}/api/buildings/sSave?access_token={access_token}"
    print(f"\n创建楼栋: {name}")
    print(f"URL: {url}")
    print(f"请求体: {json.dumps(req_body, ensure_ascii=False)}")
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            url,
            data=json.dumps(req_body).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"响应: {json.dumps(result, ensure_ascii=False)}")
            return result
    except Exception as e:
        print(f"创建楼栋失败: {str(e)}")
        return {"success": False, "msg": str(e)}

# ============ 名称转拼音 ============
def to_pinyin(name):
    """简单中文转拼音（只处理汉字）"""
    # 简单实现：替换常用汉字为拼音
    mapping = {
        '泰': 'tai', '华': 'hua', '大': 'da', '厦': 'xia', 
        '栋': 'dong', '号': 'hao', '楼': 'lou', '区': 'qu',
        '园': 'yuan', '路': 'lu', '街': 'jie', '道': 'dao'
    }
    result = ''
    for char in name:
        result += mapping.get(char, char)
    return result

# ============ 主程序 ============
def main():
    print("=" * 50)
    print("我家云开放平台 - 批量创建楼栋")
    print("=" * 50)
    
    # 第一步：获取 Ticket
    print("\n【步骤1】获取Ticket...")
    try:
        ticket = get_ticket()
        print(f"✓ Ticket获取成功: {ticket}")
    except Exception as e:
        print(f"✗ 获取Ticket失败: {e}")
        return
    
    # 第二步：获取 Access Token
    print("\n【步骤2】获取Access Token...")
    try:
        access_token = get_access_token(ticket)
        print(f"✓ Access Token获取成功: {access_token[:20]}...")
    except Exception as e:
        print(f"✗ 获取Access Token失败: {e}")
        return
    
    # 第三步：创建楼栋
    print(f"\n【步骤3】创建{BUILDING_COUNT}个楼栋（每{INTERVAL_MINUTES}分钟一个）...")
    
    for i in range(1, BUILDING_COUNT + 1):
        name = f"泰华大厦{i}栋"
        number = to_pinyin(name)
        
        print(f"\n--- 第{i}/{BUILDING_COUNT}个楼栋 ---")
        result = create_building(access_token, name, number)
        
        if result.get("success"):
            print(f"✓ {name} 创建成功!")
        else:
            print(f"✗ {name} 创建失败: {result.get('msg')}")
        
        # 如果不是最后一个，等待
        if i < BUILDING_COUNT:
            print(f"等待{INTERVAL_MINUTES}分钟后创建下一个...")
            time.sleep(INTERVAL_MINUTES * 60)
    
    print("\n" + "=" * 50)
    print("全部完成!")
    print("=" * 50)

if __name__ == "__main__":
    main()
