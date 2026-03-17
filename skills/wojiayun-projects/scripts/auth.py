#!/usr/bin/env python3
"""
获取我家云API访问Token - 正确的认证流程
"""
import hashlib
import time
import json
import requests
import urllib.parse
import ssl
import os

# API配置
API_BASE_URL = "https://api.wojiacloud.cn"

# 应用凭证
APP_KEY = "6w6caainm1he2hhg"
APP_SECRET = "gbxvr8hyti3vt29194e9zif6xu5164sg"
PROJECT_ID = "319c23c4c60e4def9959c776c32ca7f9"
NUMBER = "18820487064"

# Token缓存文件
TOKEN_CACHE = "/workspace/token_cache.json"

def get_token():
    """获取访问Token - 使用ticket方式"""
    # 检查缓存
    if os.path.exists(TOKEN_CACHE):
        try:
            with open(TOKEN_CACHE) as f:
                c = json.load(f)
            if time.time() - c.get('t', 0) < 24*3600:
                print(f"✅ 使用缓存Token: {c['token'][:30]}...")
                return c['token']
        except:
            pass
    
    # 获取ticket
    ct = int(time.time() * 1000)
    sig = hashlib.sha1(
        hashlib.md5(f'appKey={APP_KEY}&clientTime={ct}&version=V1.0&{APP_SECRET}'.encode()).hexdigest().encode()
    ).hexdigest()
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    ticket_url = f"{API_BASE_URL}/api/users/ticket?appKey={APP_KEY}&clientTime={ct}&version=V1.0&signature={sig}"
    print(f"请求ticket: {ticket_url}")
    
    ticket_response = requests.get(ticket_url, context=ctx, timeout=30)
    ticket_data = ticket_response.json()
    print(f"ticket响应: {ticket_data}")
    
    if not ticket_data.get('success'):
        print(f"❌ 获取ticket失败: {ticket_data.get('msg')}")
        return None
    
    ticket = ticket_data['data']['ticket']
    
    # 使用ticket获取access_token
    token_url = f"{API_BASE_URL}/api/users/access_token"
    data = {
        "ticket": ticket,
        "username": NUMBER,
        "pid": PROJECT_ID,
        "type": "2",
        "source": "OpenClaw"
    }
    
    print(f"请求token: {token_url}")
    token_response = requests.post(token_url, data=data, timeout=30)
    token_data = token_response.json()
    print(f"token响应: {token_data}")
    
    if not token_data.get('success'):
        print(f"❌ 获取token失败: {token_data.get('msg')}")
        return None
    
    access_token = token_data['data']['access_token']
    
    # 缓存Token
    with open(TOKEN_CACHE, 'w') as f:
        json.dump({'token': access_token, 't': time.time()}, f)
    
    print(f"✅ Token获取成功: {access_token[:30]}...")
    return access_token

def sync_project(project_name, project_number=None, access_token=None):
    """同步项目"""
    if not access_token:
        print("正在获取Token...")
        access_token = get_token()
        if not access_token:
            print("❌ 无法获取Token")
            return False
    
    if not project_number:
        project_number = project_name
    
    url = f"{API_BASE_URL}/api/projects/sync_project?access_token={access_token}"
    
    data = {
        "list": [{
            "name": project_name,
            "number": project_number
        }]
    }
    
    print(f"\n请求URL: {url}")
    print(f"请求参数: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        print(f"\n响应结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get("success"):
            print(f"\n✅ 项目同步成功!")
            return True
        else:
            print(f"\n❌ 项目同步失败: {result.get('msg')}")
            return False
            
    except Exception as e:
        print(f"请求失败: {e}")
        return False

if __name__ == "__main__":
    import sys
    print("=" * 50)
    print("我家云API - 获取Token")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # 同步项目
        project_name = sys.argv[1]
        project_number = sys.argv[2] if len(sys.argv) > 2 None
        sync_project(project_name, project_number)
    else:
        # 仅获取Token
        get_token()
