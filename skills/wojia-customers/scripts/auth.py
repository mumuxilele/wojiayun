#!/usr/bin/env python3
"""
我家云API认证模块
提供Ticket和Access Token获取功能
"""
import json
import time
import hashlib
import urllib.request
import urllib.parse
import ssl
import os

# API配置
API_HOST = "https://api.wojiacloud.cn"
APP_KEY = "6w6caainm1he2hhg"
APP_SECRET = "gbxvr8hyti3vt29194e9zif6xu5164sg"
PID = "319c23c4c60e4def9959c776c32ca7f9"
NUMBER = "18820487064"

TOKEN_FILE = "token_cache.json"

def calculate_signature(app_key, app_secret, client_time, version="V1.0"):
    """计算签名：MD5 + SHA1"""
    param_string = f"appKey={app_key}&clientTime={client_time}&version={version}&{app_secret}"
    md5_hash = hashlib.md5(param_string.encode('utf-8')).hexdigest()
    sha1_hash = hashlib.sha1(md5_hash.encode('utf-8')).hexdigest()
    return sha1_hash

def get_ticket():
    """获取Ticket令牌"""
    client_time = int(time.time() * 1000)
    signature = calculate_signature(APP_KEY, APP_SECRET, client_time)
    
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
    result = json.loads(urllib.request.urlopen(req, context=ctx, timeout=30).read().decode('utf-8'))
    
    if result.get("success") and result.get("data", {}).get("ticket"):
        return result["data"]["ticket"]
    else:
        raise Exception(f"获取Ticket失败: {result.get('msg', '未知错误')}")

def get_access_token(ticket):
    """获取Access Token"""
    data = urllib.parse.urlencode({
        "ticket": ticket,
        "username": NUMBER,
        "pid": PID,
        "type": "2",
        "source": "OpenClaw"
    }).encode('utf-8')
    
    url = f"{API_HOST}/api/users/access_token"
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    result = json.loads(urllib.request.urlopen(req, context=ctx, timeout=30).read().decode('utf-8'))
    
    if result.get("success") and result.get("data", {}).get("access_token"):
        return result["data"]["access_token"]
    else:
        raise Exception(f"获取Access Token失败: {result.get('msg', '未知错误')}")

def save_token(token_data):
    """保存token到文件"""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)

def load_token():
    """从文件加载token"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

def is_token_valid(token_data):
    """检查token是否有效"""
    if not token_data:
        return False
    expires = token_data.get('expires', 0)
    return time.time() < expires

def get_token():
    """获取token（带缓存）"""
    # 尝试加载缓存
    token_data = load_token()
    if token_data and is_token_valid(token_data):
        print(f"使用缓存的Token (剩余 {int(token_data['expires'] - time.time())} 秒)")
        return token_data['token']
    
    # 重新获取
    print("正在获取新Token...")
    ticket = get_ticket()
    print(f"Ticket: {ticket[:20]}...")
    
    token = get_access_token(ticket)
    print(f"Access Token: {token[:20]}...")
    
    # 缓存24小时
    token_data = {
        'token': token,
        'expires': time.time() + 86400 - 300  # 提前5分钟过期
    }
    save_token(token_data)
    print("Token已缓存 (24小时)")
    
    return token

def refresh_token():
    """强制刷新token"""
    print("强制刷新Token...")
    ticket = get_ticket()
    token = get_access_token(ticket)
    
    token_data = {
        'token': token,
        'expires': time.time() + 86400 - 300
    }
    save_token(token_data)
    print("Token已刷新并缓存")
    
    return token

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--refresh":
            token = refresh_token()
            print(f"\n新Token: {token}")
        elif sys.argv[1] == "--check":
            token_data = load_token()
            if token_data and is_token_valid(token_data):
                remaining = int(token_data['expires'] - time.time())
                print(f"Token有效，剩余 {remaining} 秒")
            else:
                print("Token无效或已过期")
        else:
            token = get_token()
            print(f"\n当前Token: {token}")
    else:
        token = get_token()
        print(f"\n当前Token: {token}")
