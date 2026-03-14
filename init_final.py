#!/usr/bin/env python3
"""
我家云开放平台 - 数据初始化完整版
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

def call(token, path, params):
    url = f"{API_HOST}{path}?access_token={token}"
    fd = {k: json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in params.items()}
    ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fd).encode(), headers={'Content-Type':'application/x-www-form-urlencoded'})
    return json.loads(urllib.request.urlopen(req, context=ctx).read())

def main():
    print("="*50)
    print("数据初始化流程")
    print("="*50)
    
    token = get_token()
    print(f"Token: {token[:20]}...")
    
    # 1. 创建项目
    print("\n[1] 创建项目...")
    r = call(token, "/api/projects/sync_project", {"list":[{"name":"泰华小区","number":"THXQ001"}]})
    print(f"  -> {r.get('msg')}")
    
    # 2. 创建楼栋
    print("\n[2] 创建楼栋...")
    bldgs = [
        {"name":"泰华大厦A栋","number":"thdsAdong","overCount":25,"underCount":4},
        {"name":"泰华大厦B栋","number":"thdsBdong","overCount":20,"underCount":2},
    ]
    r = call(token, "/api/buildings/sSave", {"projectID":PID, "list":bldgs})
    print(f"  -> {r.get('msg')}")
    
    # 3. 创建单元 (buildNumber用楼栋编码)
    print("\n[3] 创建单元...")
    units = [
        {"name":"1单元","buildNumber":"thdsAdong"},  # 用楼栋的number
        {"name":"2单元","buildNumber":"thdsAdong"},
    ]
    r = call(token, "/api/buildUnit/sSave", {"projectID":PID, "list":units})
    print(f"  -> {r.get('msg')}")
    
    # 4. 创建房间
    print("\n[4] 创建房间...")
    rms = [
        {"buildingName":"泰华大厦A栋","buildUnitName":"1单元","floor":1,"roomName":"101","roomNumber":"TH101","property":0,"buildingArea":90,"roomArea":75,"chargeArea":75,"productName":"住宅"},
        {"buildingName":"泰华大厦A栋","buildUnitName":"1单元","floor":1,"roomName":"102","roomNumber":"TH102","property":0,"buildingArea":92,"roomArea":80,"chargeArea":80,"productName":"住宅"},
    ]
    r = call(token, "/api/rooms/sSave", {"projectID":PID, "list":rms})
    print(f"  -> {r.get('msg')}")
    
    # 5. 绑定客户
    print("\n[5] 绑定房间客户...")
    rc = [
        {"buildingName":"泰华大厦A栋","roomName":"101","roomNumber":"TH101","property":"0","customerType":"0","joinDate":"2024-01-01","type":"P","customerName":"张三","phone":"13800138001"},
        {"buildingName":"泰华大厦A栋","roomName":"102","roomNumber":"TH102","property":"0","customerType":"0","joinDate":"2024-01-01","type":"P","customerName":"李四","phone":"13800138002"},
    ]
    r = call(token, "/api/rooms/addroomcus", {"pid":PID, "rooms":rc})
    print(f"  -> {r.get('msg')}")
    
    print("\n完成!")

if __name__ == "__main__": main()
