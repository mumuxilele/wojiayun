#!/usr/bin/env python3
"""
组织架构批量导入工具 - 自动获取Ticket
"""
import json
import time
import hashlib
import urllib.request
import urllib.parse
import ssl
import sys

API_HOST = "https://api.wojiacloud.cn"

# 凭证配置
APP_KEY = "6w6caainm1he2hhg"
APP_SECRET = "gbxvr8hyti3vt29194e9zif6xu5164sg"
PID = "319c23c4c60e4def9959c776c32ca7f9"

def calculate_signature(app_key, app_secret, client_time, version="V1.0"):
    param_string = f"appKey={app_key}&clientTime={client_time}&version={version}&{app_secret}"
    md5_hash = hashlib.md5(param_string.encode('utf-8')).hexdigest()
    sha1_hash = hashlib.sha1(md5_hash.encode('utf-8')).hexdigest()
    return sha1_hash

def get_ticket():
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

def save_org(list_data, ticket):
    url = f"{API_HOST}/api/orgUnit/batchSave"
    
    params = {
        "ticket": ticket,
        "ecID": PID,
        "list": json.dumps(list_data, ensure_ascii=False)
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(params).encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    result = json.loads(urllib.request.urlopen(req, context=ctx, timeout=30).read().decode('utf-8'))
    return result

# 从图片识别的组织架构数据 (准确识别，不自行创建)
ORG_DATA = [
    # 第一层
    {"name": "第一太平戴维斯物业顾问（上海）有限公司", "number": "SAVILLSS", "simpleName": "总部公司", "isCompany": 1, "parent": None},
    
    # 第二层
    {"name": "第一太平戴维斯", "number": "SAVILLS", "simpleName": "集团", "isCompany": 1, "parent": "第一太平戴维斯物业顾问（上海）有限公司"},
    {"name": "华东区", "number": "HD", "simpleName": "华东区", "isCompany": 1, "parent": "第一太平戴维斯物业顾问（上海）有限公司"},
    
    # 第三层 - 华东区下面
    {"name": "锦绣里", "number": "JXH", "simpleName": "锦绣里", "isCompany": 1, "parent": "华东区"},
    {"name": "高登金融大厦", "number": "GDJRDS", "simpleName": "高登大厦", "isCompany": 1, "parent": "华东区"},
    {"name": "中泰广场", "number": "ZTGC", "simpleName": "中泰广场", "isCompany": 1, "parent": "华东区"},
    {"name": "力宝广场", "number": "LBGC", "simpleName": "力宝广场", "isCompany": 1, "parent": "华东区"},
    {"name": "福新名苑", "number": "FXMY", "simpleName": "福新名苑", "isCompany": 1, "parent": "华东区"},
    {"name": "西郊青溪花园", "number": "XJQXGY", "simpleName": "西郊花园", "isCompany": 1, "parent": "华东区"},
    
    # 第四层 - 高登金融大厦下的部门
    {"name": "财务部", "number": "CWB_GD", "simpleName": "财务部", "isCompany": 2, "parent": "高登金融大厦"},
    {"name": "客服部", "number": "KF_GD", "simpleName": "客服部", "isCompany": 2, "parent": "高登金融大厦"},
    {"name": "工程部", "number": "GC_GD", "simpleName": "工程部", "isCompany": 2, "parent": "高登金融大厦"},
    {"name": "行政人事部", "number": "XZRSB_GD", "simpleName": "行政人事", "isCompany": 2, "parent": "高登金融大厦"},
    {"name": "运作部（保安、保洁）", "number": "YZB_GD", "simpleName": "运作部", "isCompany": 2, "parent": "高登金融大厦"},
]

def build_org_list():
    name_map = {org['name']: org for org in ORG_DATA}
    
    for org in ORG_DATA:
        parent_name = org.get('parent')
        org['sourceID'] = f"SAVILLS_{org['number']}"
        org['sourceSystem'] = "IMPORT"
        
        if parent_name and parent_name in name_map:
            parent = name_map[parent_name]
            org['parentID'] = parent['sourceID']
        else:
            org['parentID'] = None
    
    def calc_level(org, visited=None):
        if visited is None:
            visited = set()
        
        if org['name'] in visited:
            return 1, org['number']
        visited.add(org['name'])
        
        parent_id = org.get('parentID')
        if parent_id:
            parent = name_map.get(org.get('parent'))
            if parent:
                parent_level, parent_long = calc_level(parent, visited.copy())
                level = parent_level + 1
                long_number = f"{parent_long}.{org['number']}"
            else:
                level = 1
                long_number = org['number']
        else:
            level = 1
            long_number = org['number']
        
        org['level'] = level
        org['longNumber'] = long_number
        
        return level, long_number
    
    for org in ORG_DATA:
        calc_level(org)
    
    for org in ORG_DATA:
        is_parent = False
        for other in ORG_DATA:
            if other.get('parent') == org['name']:
                is_parent = True
                break
        org['isLeaf'] = 0 if is_parent else 1
    
    for org in ORG_DATA:
        if 'parent' in org:
            del org['parent']
    
    return ORG_DATA

def main():
    print("=" * 60)
    print("组织架构导入工具")
    print("=" * 60)
    
    print("\n组织架构:")
    orgs = build_org_list()
    for org in orgs:
        level = org.get('level', 1)
        indent = "  " * (level - 1)
        is_leaf = "📄" if org.get('isLeaf') == 1 else "📁"
        print(f"  {indent}{is_leaf} {org['name']} ({org['number']})")
    
    print(f"\n共 {len(orgs)} 个组织")
    
    print("\n获取Ticket...")
    try:
        ticket = get_ticket()
        print(f"✓ Ticket获取成功")
    except Exception as e:
        print(f"❌ Ticket获取失败: {e}")
        sys.exit(1)
    
    print("\n调用接口导入...")
    result = save_org(orgs, ticket)
    
    print("\n接口返回:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result.get('success'):
        print("\n✅ 导入成功!")
    else:
        print(f"\n❌ 导入失败: {result.get('msg', '未知错误')}")

if __name__ == "__main__":
    main()
