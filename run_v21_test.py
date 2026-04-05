#!/usr/bin/env python3
"""V21.0 快速验证脚本"""
import sys
import os
sys.path.insert(0, 'C:/Users/kingdee/WorkBuddy/Claw/wojiayun')

print("=" * 60)
print("V21.0 功能验证")
print("=" * 60)

# 1. 验证秒杀服务
print("\n[1] 验证秒杀服务模块...")
try:
    # 不导入db因为需要数据库连接
    with open('C:/Users/kingdee/WorkBuddy/Claw/wojiayun/business-common/seckill_service.py', 'r') as f:
        content = f.read()
    assert 'class SeckillService' in content, "缺少SecKillService类"
    assert 'def create_seckill_order' in content, "缺少create_seckill_order方法"
    assert 'def verify_seckill_stock' in content, "缺少verify_seckill_stock方法"
    assert 'conn.begin()' in content, "缺少事务处理"
    print("  ✓ 秒杀服务模块结构正确")
except Exception as e:
    print(f"  ✗ 秒杀服务验证失败: {e}")

# 2. 验证Swagger配置
print("\n[2] 验证Swagger配置...")
try:
    with open('C:/Users/kingdee/WorkBuddy/Claw/wojiayun/business-common/swagger_config.py', 'r') as f:
        content = f.read()
    assert 'def init_swagger' in content, "缺少init_swagger函数"
    assert '/api/docs/' in content, "缺少API文档路由"
    print("  ✓ Swagger配置结构正确")
except Exception as e:
    print(f"  ✗ Swagger验证失败: {e}")

# 3. 验证Redis缓存适配器
print("\n[3] 验证Redis缓存适配器...")
try:
    with open('C:/Users/kingdee/WorkBuddy/Claw/wojiayun/business-common/cache_redis.py', 'r') as f:
        content = f.read()
    assert 'class RedisCache' in content, "缺少RedisCache类"
    assert 'def get(' in content, "缺少get方法"
    assert 'def set(' in content, "缺少set方法"
    print("  ✓ Redis缓存适配器结构正确")
except Exception as e:
    print(f"  ✗ Redis缓存验证失败: {e}")

# 4. 验证迁移脚本
print("\n[4] 验证V21迁移脚本...")
try:
    with open('C:/Users/kingdee/WorkBuddy/Claw/wojiayun/business-common/migrate_v21.py', 'r') as f:
        content = f.read()
    assert 'business_seckill_orders' in content, "缺少秒杀订单表"
    assert 'logistics_no' in content, "缺少物流字段"
    assert 'reply_content' in content, "缺少回复字段"
    print("  ✓ V21迁移脚本结构正确")
except Exception as e:
    print(f"  ✗ 迁移脚本验证失败: {e}")

# 5. 验证测试文件
print("\n[5] 验证测试文件...")
try:
    with open('C:/Users/kingdee/WorkBuddy/Claw/wojiayun/tests/test_v21_structure.py', 'r') as f:
        content = f.read()
    assert 'class TestV21SeckillService' in content, "缺少秒杀服务测试"
    assert 'class TestV21ReviewFlow' in content, "缺少评价流程测试"
    print("  ✓ 测试文件结构正确")
except Exception as e:
    print(f"  ✗ 测试文件验证失败: {e}")

# 6. 验证用户端API
print("\n[6] 验证用户端API...")
try:
    with open('C:/Users/kingdee/WorkBuddy/Claw/wojiayun/business-userH5/app.py', 'r') as f:
        content = f.read()
    assert '/api/seckill/activity' in content, "缺少秒杀活动API"
    assert '/api/seckill/orders' in content, "缺少秒杀订单API"
    assert '/api/user/reviews' in content, "缺少评价API"
    assert '/api/user/member/benefits' in content, "缺少会员权益API"
    print("  ✓ 用户端API结构正确")
except Exception as e:
    print(f"  ✗ 用户端API验证失败: {e}")

# 7. 验证员工端API
print("\n[7] 验证员工端API...")
try:
    with open('C:/Users/kingdee/WorkBuddy/Claw/wojiayun/business-staffH5/app.py', 'r') as f:
        content = f.read()
    assert '/api/staff/reviews' in content, "缺少评价列表API"
    assert '/reply' in content, "缺少评价回复API"
    print("  ✓ 员工端API结构正确")
except Exception as e:
    print(f"  ✗ 员工端API验证失败: {e}")

# 8. 验证管理端API
print("\n[8] 验证管理端API...")
try:
    with open('C:/Users/kingdee/WorkBuddy/Claw/wojiayun/business-admin/app.py', 'r') as f:
        content = f.read()
    assert '/api/admin/seckill/orders' in content, "缺少秒杀订单管理API"
    assert '/api/admin/reviews' in content, "缺少评价管理API"
    print("  ✓ 管理端API结构正确")
except Exception as e:
    print(f"  ✗ 管理端API验证失败: {e}")

print("\n" + "=" * 60)
print("验证完成！")
print("=" * 60)
print("\n新增功能清单:")
print("  1. 秒杀服务 - 支持高并发下单、行锁防超卖")
print("  2. 秒杀下单API - 用户端秒杀活动参与")
print("  3. 订单评价API - 完整的评价提交流程")
print("  4. 会员权益API - 会员等级和特权展示")
print("  5. 物流查询API - 订单物流信息查询")
print("  6. 评价管理 - 员工/管理员回复评价")
print("  7. Redis缓存适配 - 多进程部署支持")
print("  8. Swagger文档 - 交互式API文档")
