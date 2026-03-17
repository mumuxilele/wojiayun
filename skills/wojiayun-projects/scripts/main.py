#!/usr/bin/env python3
"""
我家云项目同步 - 完整版
用法: python3 main.py <项目名称> [项目编号]
"""
import hashlib
import time
import json
import requests
import urllib.parse
import ssl
import os
import sys

# 配置
API_HOST = "https://api.wojiacloud.cn"
APP_KEY = "6w6caainm1he2hhg"
APP_SECRET = "gbxvr8hyti3vt29194e9zif6xu5164sg"
PID = "319c23c4c60e4def9959c776c32ca7f9"
NUMBER = "18820487064"
TOKEN_CACHE = "token_cache.json"

def get_token():
    """获取Token"""
    # 检查缓存
    if os.path.exists(TOKEN_CACHE):
        try:
            with open(TOKEN_CACHE) as f:
                c = json.load(f)
            if time.time() - c.get('t', 0) < 24*3600:
                print(f"✓ 使用缓存Token")
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
    
    # 请求ticket
    ticket_url = f"{API_HOST}/api/users/ticket?appKey={APP_KEY}&clientTime={ct}&version=V1.0&signature={sig}"
    ticket_resp = requests.get(ticket_url, context=ctx, timeout=30)
    ticket_data = ticket_resp.json()
    
    if not ticket_data.get('success'):
        print(f"✗ 获取ticket失败: {ticket_data.get('msg')}")
        return None
    
    ticket = ticket_data['data']['ticket']
    
    # 请求access_token
    token_url = f"{API_HOST}/api/users/access_token"
    data = {
        "ticket": ticket,
        "username": NUMBER,
        "pid": PID,
        "type": "2",
        "source": "OpenClaw"
    }
    token_resp = requests.post(token_url, data=data, timeout=30)
    token_data = token_resp.json()
    
    if not token_data.get('success'):
        print(f"✗ 获取token失败: {token_data.get('msg')}")
        return None
    
    access_token = token_data['data']['access_token']
    
    # 缓存
    with open(TOKEN_CACHE, 'w') as f:
        json.dump({'token': access_token, 't': time.time()}, f)
    
    print(f"✓ Token获取成功")
    return access_token

def sync_project(project_name, project_number=None):
    """同步项目"""
    token = get_token()
    if not token:
        return False
    
    if not project_number:
        project_number = project_name
    
    url = f"{API_HOST}/api/projects/sync_project?access_token={token}"
    
    payload = {
        "list": [{
            "name": project_name,
            "number": project_number
        }]
    }
    
    print(f"\n正在同步项目: {project_name} ({project_number})")
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        result = resp.json()
        
        print(f"\n响应: {json.dumps(result, ensure_ascii=False)}")
        
        if result.get('success'):
            print(f"\n✅ 项目同步成功!")
            return True
        else:
            print(f"\n✗ 项目同步失败: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def main():
    print("=" * 50)
    print("我家云 - 项目同步工具")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("\n用法:")
        print("  python3 main.py <项目名称> [项目编号]")
        print("\n示例:")
        print("  python3 main.py \"测试项目\" \"test001\"")
        sys.exit(1)
    
    project_name = sys.argv[1]
    project_number = sys.argv[2] if len(sys.argv) > 2 else project_name
    
    sync_project(project_name, project_number)

if __name__ == "__main__":
    main()
