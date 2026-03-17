#!/usr/bin/env python3
"""
同步单个项目
"""
import json, time, hashlib, urllib.request, urllib.parse, ssl, os

# 配置
APP_KEY = "6w6caainm1he2hhg"
APP_SECRET = "gbxvr8hyti3vt29194e9zif6xu5164sg"
PID = "319c23c4c60e4def9959c776c32ca7f9"
NUMBER = "18820487064"
API_HOST = "https://api.wojiacloud.cn"

def get_token():
    cache_file = "/workspace/token_cache.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                c = json.load(f)
            if time.time() - c.get('t', 0) < 24*3600:
                return c['token']
        except: pass
    
    ct = int(time.time()*1000)
    sig = hashlib.sha1(hashlib.md5(f'appKey={APP_KEY}&clientTime={ct}&version=V1.0&{APP_SECRET}'.encode()).hexdigest().encode()).hexdigest()
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    
    ticket = json.loads(urllib.request.urlopen(f"{API_HOST}/api/users/ticket?appKey={APP_KEY}&clientTime={ct}&version=V1.0&signature={sig}", context=ctx).read())['data']['ticket']
    data = urllib.parse.urlencode({"ticket":ticket,"username":NUMBER,"pid":PID,"type":"2","source":"OpenClaw"}).encode()
    req = urllib.request.Request(f"{API_HOST}/api/users/access_token", data=data, headers={'Content-Type':'application/x-www-form-urlencoded'})
    token = json.loads(urllib.request.urlopen(req, context=ctx).read())['data']['access_token']
    
    with open(cache_file, 'w') as f: json.dump({'token':token, 't':time.time()}, f)
    return token

def sync_project(name, number):
    token = get_token()
    url = f"{API_HOST}/api/projects/sync_project?access_token={token}"
    data = {"list":[{"name":name,"number":number}]}
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), headers={'Content-Type':'application/x-www-form-urlencoded'})
    result = json.loads(urllib.request.urlopen(req, context=ctx).read())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result.get('success')

if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "上海ISF国金大厦"
    number = sys.argv[2] if len(sys.argv) > 2 else "shanghai_isf"
    print(f"同步项目: {name} ({number})")
    sync_project(name, number)
