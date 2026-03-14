#!/usr/bin/env python3
"""
发放会员积分
"""
import json
import sys

API_HOST = "https://api.wojiacloud.cn"
TOKEN = "edab298a99155402aa7dd6e5e6133ef6a931c56d818e2ea5e393ec997e3c7798"

def grant_integral(phones, integral_count, audit_type=2, remark=""):
    """发放积分"""
    import urllib.request
    
    # 处理手机号
    if isinstance(phones, list):
        phone_str = ",".join(phones)
    else:
        phone_str = phones
    
    # 参数 (token需要放在请求体中)
    params = {
        "phone": phone_str,
        "integralCount": str(integral_count),
        "audit_type": audit_type,
        "access_token": TOKEN
    }
    
    if remark:
        params["remark"] = remark
    
    url = f"{API_HOST}/api/integralGrant/addIntegral"
    
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        url,
        data=json.dumps(params).encode(),
        headers={'Content-Type': 'application/json'}
    )
    
    return json.loads(urllib.request.urlopen(req, context=ctx).read())

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法:")
        print("  python3 grant_integral.py <手机号> <积分数量> [备注] [审核类型]")
        print("")
        print("示例:")
        print("  python3 grant_integral.py 13800138000 100")                       # 单个手机号发放100积分
        print("  python3 grant_integral.py 13800138000,13900139000 100")        # 多个手机号
        print("  python3 grant_integral.py 13800138000 100 '活动奖励'")          # 带备注
        print("  python3 grant_integral.py 13800138000 100 '' 1")                # 需要审核
        sys.exit(1)
    
    phone = sys.argv[1]
    integral_count = sys.argv[2]
    remark = sys.argv[3] if len(sys.argv) > 3 else ""
    audit_type = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    
    print(f"发放积分...")
    print(f"  手机号: {phone}")
    print(f"  积分数量: {integral_count}")
    print(f"  备注: {remark or '无'}")
    print(f"  审核类型: {'自动审核' if audit_type == 2 else '需要审核'}")
    print()
    
    result = grant_integral(phone, integral_count, audit_type, remark)
    
    if result.get("success"):
        print("✅ 积分发放成功!")
        print(f"  {result.get('data', '')}")
    else:
        print(f"❌ 积分发放失败: {result.get('msg', '未知错误')}")
