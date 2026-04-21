# MVC架构改造 - 批量改造记录
# 日期: 2026-04-20
# 改造范围: wojiayun/business-userH5/app.py

## 改造进度

### userH5 app.py
| 指标 | 改造前 | 改造后 | 减少 |
|------|--------|--------|------|
| 直接DB调用 | 199处 | 178处 | 21处 |
| 改造接口数 | 0 | 5个 | - |

### 新增 Service 文件
1. user_service.py (之前已创建)
2. review_service.py ✅
3. favorite_service.py ✅
4. checkin_service.py ✅

## 已完成的改造

### 1. /api/user/profile
- 原来: 35行代码，5条SQL
- 现在: 3行代码，调用UserService.get_user_profile()

### 2. _update_review_stats()
- 原来: 30+行代码，6条SQL
- 现在: 2行代码，调用ReviewService.update_target_rating()

### 3. /api/user/favorites (GET)
- 原来: 40+行代码，直接SQL
- 现在: 6行代码，调用FavoriteService.get_user_favorites()

### 4. /api/user/favorites (POST)
- 原来: 35行代码，4条SQL
- 现在: 15行代码，调用FavoriteService.add_favorite()

### 5. /api/user/checkin/status
- 原来: 50+行代码，6条SQL
- 现在: 8行代码，调用CheckinService.get_checkin_status()

## 待改造的高优先级接口

userH5 app.py 中仍有 178 处直接DB调用，按频率排序：

### 高频 (10+ 次DB调用)
- create_order: 5次
- create_review: 5次
- get_product_detail: 5次
- cancel_order: 4次
- pay_booking: 4次
- get_seckill_activity: 3次
- apply_invoice_from_order: 4次

### 中频 (3-5 次)
- get_member_benefits: 3次
- update_address: 3次
- add_search_history: 4次
- update_invoice_title: 3次

### 低频 (1-2 次)
- 大约 160+ 个小接口

## staffH5 app.py 改造计划
- 直接DB调用: ~142处
- 优先级: 高
- 建议: 先改造申请审批相关接口

## admin app.py 改造计划
- 直接DB调用: ~235处
- 优先级: 中
- 建议: 用户端和员工端改造完成后再处理

## 技术要点

### 1. Service 层模式
```python
class XxxService:
    def __init__(self):
        from business_common import db
        self.db = db
    
    def get_xxx(self, ...):
        # 业务逻辑
        result = self.db.get_all(...)
        return result
    
    def do_xxx(self, ...):
        # 业务操作
        self.db.execute(...)
        return {'success': True}

# 单例
_xxx_service = None
def get_xxx_service() -> XxxService:
    global _xxx_service
    if _xxx_service is None:
        _xxx_service = XxxService()
    return _xxx_service
```

### 2. Controller 层改造模式
```python
# 改造前
@app.route('/api/xxx')
def get_xxx():
    data = db.get_one("SELECT ...", [id])
    return jsonify({'success': True, 'data': data})

# 改造后
@app.route('/api/xxx')
def get_xxx():
    from business_common.xxx_service import get_xxx_service
    service = get_xxx_service()
    return jsonify(service.get_xxx(id))
```

## 下一步建议

1. **批量创建高频 Service**
   - OrderService (订单)
   - ProductService (商品)
   - ApplicationService (申请)

2. **继续改造 userH5**
   - create_order
   - create_review
   - get_product_detail

3. **同步改造 staffH5**
   - 申请审批相关
   - 订单管理相关

4. **测试验证**
   - 确保改造后功能不变
   - 检查日志和错误
