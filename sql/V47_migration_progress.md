# V47.0 主键改造进度报告

## 完成情况

### 1. 数据库改造 ✅ 已完成
- **已完成**: 15个表主键改为FID (VARCHAR(32))
- **已生成**: 所有现有数据的FID
- **已保留**: 原id字段作为唯一索引用于兼容

**已改造表列表**:
```
business_applications    ✅
business_orders          ✅
business_reviews         ✅
business_members         ✅
business_feedback        ✅
business_products        ✅
business_coupons         ✅
business_user_coupons    ✅
business_approve_nodes   ✅
business_application_attachments ✅
business_application_reminds     ✅
visit_records            ✅
chat_messages            ✅
chat_sessions            ✅
auth_accounts            ✅
```

### 2. 代码修改 ✅ 部分完成

**已修改文件** (6个):
| 文件 | 说明 |
|------|------|
| `business-common/member_service.py` | 会员注册、积分日志 |
| `business-common/order_service.py` | 订单创建、订单明细 |
| `business-userH5/app.py` | 申请提交 |
| `business-admin/app.py` | 走访记录 |
| `chat/ChatDao.js` | 聊天消息保存 |
| `chat/sql/queries.json` | 聊天SQL配置 |
| `auth/app.py` | 账户创建 |

**待修改文件** (约50个):
```
business-common/
├── v44_api.py
├── user_settings_service.py
├── user_behavior_service.py
├── task_queue_service.py
├── system_linkage_service.py
├── share_service.py
├── seckill_service.py
├── search_service.py
├── search_enhance_service.py
├── review_reward_service.py
├── push_service.py
├── promotion_engine_service.py
├── product_spec_service.py
├── product_service.py
├── product_qa_service.py
├── print_service.py
├── points_scheduler.py
├── points_mall.py
├── payment_service.py
├── order_tracking_service.py
├── order_expire_scheduler.py
├── order_enhance_service.py
├── notification.py
├── member_lifecycle_service.py
├── member_level.py
├── logistics_service.py
├── invoice_service.py
├── inventory_alert_service.py
├── growth_task_service.py
├── growth_service.py
├── group_buy_service.py
├── faq_service.py
├── data_export_service.py
├── cart_service.py
├── cancel_expired_orders.py
├── cancel_expired_bookings.py
├── batch_operation_service.py
├── backup_service.py
├── aftersales_service.py
├── address_enhance_service.py
├── ... (其他业务服务)
```

## 修改模式

### Python 文件
```python
# 1. 添加导入
from business_common.fid_utils import generate_fid, generate_business_fid

# 2. 生成FID
fid = generate_business_fid('prefix')  # 或使用 generate_fid()

# 3. 修改INSERT语句
sql = """
    INSERT INTO table_name (
        fid, field1, field2  -- 添加fid字段
    ) VALUES (%s, %s, %s)
"""
params = [fid, value1, value2]
```

### Node.js 文件 (chat服务)
```javascript
// 1. 使用 generateFid() 方法
const fid = this.generateFid();

// 2. SQL添加fid字段
const sql = `INSERT INTO table (fid, ...) VALUES (?, ...)`;
```

## 表与FID前缀对照表

| 表名 | FID前缀 | 生成方式 |
|------|---------|----------|
| business_applications | `app` | `generate_business_fid('app')` |
| business_orders | `order` | `generate_business_fid('order')` |
| business_order_details | `detail` | `generate_fid()` |
| business_bookings | `booking` | `generate_business_fid('booking')` |
| business_refunds | `refund` | `generate_business_fid('refund')` |
| business_reviews | `review` | `generate_business_fid('review')` |
| business_members | `member` | `generate_business_fid('member')` |
| business_feedback | `feedback` | `generate_business_fid('feedback')` |
| business_products | `product` | `generate_business_fid('product')` |
| business_cart | `cart` | `generate_fid()` |
| business_favorites | `fav` | `generate_fid()` |
| business_coupons | `coupon` | `generate_business_fid('coupon')` |
| business_user_coupons | `user_coupon` | `generate_fid()` |
| business_invoices | `invoice` | `generate_business_fid('invoice')` |
| business_aftersales | `aftersale` | `generate_business_fid('aftersale')` |
| business_seckill_orders | `seckill` | `generate_fid()` |
| business_order_tracking | `track` | `generate_fid()` |
| business_approve_nodes | `node` | `generate_fid()` |
| business_application_attachments | `attach` | `generate_fid()` |
| business_application_reminds | `remind` | `generate_fid()` |
| business_points_log | `plog` | `generate_fid()` |
| visit_records | `visit` | `generate_business_fid('visit')` |
| chat_messages | `msg` | `generateFid()` (JS) |
| chat_sessions | `session` | `generateFid()` (JS) |
| auth_accounts | `account` | `generate_fid()` |

## 快速修改命令

### 使用 sed 批量替换 (Linux/Mac)
```bash
# 查找所有包含 INSERT INTO business_ 的 Python 文件
grep -r "INSERT INTO.*business_" --include="*.py" business-common/

# 建议逐个文件手动修改，避免批量替换出错
```

## 注意事项

1. **迁移脚本文件** (`migrate_v*.py`) 通常不需要修改，因为它们是历史迁移脚本
2. **测试文件** (`test_*.py`) 根据需要修改
3. **外键关联**: 如果表A有外键引用表B的id，保持现状即可（id字段仍存在且有唯一索引）
4. **API返回**: 对外API可以继续返回id字段，不影响前端

## 下一步建议

1. **优先级1** (核心业务):
   - payment_service.py - 支付记录
   - refund_service.py - 退款
   - booking_service.py - 预约
   - review_service.py - 评价

2. **优先级2** (业务功能):
   - product_service.py - 商品
   - cart_service.py - 购物车
   - coupon_service.py - 优惠券
   - seckill_service.py - 秒杀

3. **优先级3** (辅助功能):
   - 其他所有服务文件

## 验证方法

```python
# 测试FID生成
from business_common.fid_utils import generate_fid, generate_business_fid

print(generate_fid())  # 32位MD5字符串
print(generate_business_fid('order'))  # order_xxxxx...
```

---
**报告生成时间**: 2026-04-12
