# V47.0 代码修改指南 - FID主键适配

## 修改原则

1. **导入 FID 工具**
   ```python
   from .fid_utils import generate_fid, generate_business_fid
   ```

2. **INSERT 语句添加 fid 字段**
   - 在 VALUES 前添加 `fid` 字段
   - 在参数列表第一个位置添加 FID 值

3. **FID 生成方式**
   - 通用：`generate_fid()` - 生成32位MD5字符串
   - 带前缀：`generate_business_fid('prefix')` - 如 `generate_business_fid('order')`

## 修改示例

### 修改前
```python
sql = """
    INSERT INTO business_members (
        user_id, phone, nickname
    ) VALUES (%s, %s, %s)
"""
params = [user_id, phone, nickname]
```

### 修改后
```python
member_fid = generate_business_fid('member')  # 生成FID
sql = """
    INSERT INTO business_members (
        fid, user_id, phone, nickname
    ) VALUES (%s, %s, %s, %s)
"""
params = [member_fid, user_id, phone, nickname]
```

## 需要修改的文件清单

### 高优先级（核心业务流程）
| 文件 | 涉及表 | 修改内容 |
|------|--------|----------|
| business-common/order_service.py | business_orders, business_order_details | 订单创建、明细插入 |
| business-common/member_service.py | ✅ 已修改 | 会员注册、积分日志 |
| business-common/application_service.py | business_applications | 申请提交 |
| business-common/visit_service.py | visit_records | 走访记录添加 |
| business/chat_service.py | chat_messages, chat_sessions | 消息发送、会话创建 |
| business-common/auth_service.py | auth_accounts | 账户创建 |

### 中等优先级（业务功能）
| 文件 | 涉及表 | 修改内容 |
|------|--------|----------|
| business-common/review_service.py | business_reviews | 评价提交 |
| business-common/refund_service.py | business_refunds | 退款申请 |
| business-common/feedback_service.py | business_feedback | 反馈提交 |
| business-common/booking_service.py | business_bookings | 预约创建 |
| business-common/product_service.py | business_products | 商品添加 |
| business-common/cart_service.py | business_cart | 购物车添加 |
| business-common/favorites_service.py | business_favorites | 收藏添加 |
| business-common/coupon_service.py | business_coupons, business_user_coupons | 优惠券创建、领取 |
| business-common/invoice_service.py | business_invoices | 发票申请 |
| business-common/aftersales_service.py | business_aftersales | 售后申请 |
| business-common/seckill_service.py | business_seckill_orders | 秒杀订单 |
| business-common/order_tracking_service.py | business_order_tracking | 订单追踪 |
| business-common/approve_service.py | business_approve_nodes | 审批节点 |
| business-common/attachment_service.py | business_application_attachments | 附件上传 |
| business-common/remind_service.py | business_application_reminds | 提醒记录 |

### 低优先级（系统/辅助功能）
- business-common/notification.py - 通知记录
- business-common/payment_service.py - 支付记录
- business-common/logistics_service.py - 物流记录
- business-common/points_mall.py - 积分商城
- business-common/group_buy_service.py - 团购
- business-common/growth_service.py - 成长任务
- ...（其他辅助服务）

## 表与FID前缀对照表

| 表名 | 建议FID前缀 | 示例 |
|------|-------------|------|
| business_applications | `app` | `app_a1b2c3d4...` |
| business_orders | `order` | `order_a1b2c3d4...` |
| business_order_details | `detail` | `detail_a1b2c3d4...` |
| business_bookings | `booking` | `booking_a1b2c3d4...` |
| business_refunds | `refund` | `refund_a1b2c3d4...` |
| business_reviews | `review` | `review_a1b2c3d4...` |
| business_members | `member` | `member_a1b2c3d4...` |
| business_feedback | `feedback` | `feedback_a1b2c3d4...` |
| business_products | `product` | `product_a1b2c3d4...` |
| business_cart | `cart` | `cart_a1b2c3d4...` |
| business_favorites | `fav` | `fav_a1b2c3d4...` |
| business_coupons | `coupon` | `coupon_a1b2c3d4...` |
| business_user_coupons | `user_coupon` | `user_coupon_a1b2c3d4...` |
| business_invoices | `invoice` | `invoice_a1b2c3d4...` |
| business_aftersales | `aftersale` | `aftersale_a1b2c3d4...` |
| business_seckill_orders | `seckill` | `seckill_a1b2c3d4...` |
| business_order_tracking | `track` | `track_a1b2c3d4...` |
| business_approve_nodes | `node` | `node_a1b2c3d4...` |
| business_application_attachments | `attach` | `attach_a1b2c3d4...` |
| business_application_reminds | `remind` | `remind_a1b2c3d4...` |
| business_points_log | `plog` | `plog_a1b2c3d4...` |
| visit_records | `visit` | `visit_a1b2c3d4...` |
| chat_messages | `msg` | `msg_a1b2c3d4...` |
| chat_sessions | `session` | `session_a1b2c3d4...` |
| auth_accounts | `account` | `account_a1b2c3d4...` |

## 注意事项

1. **外键关联**
   - 如果表A有外键引用表B的id，需要改为引用fid
   - 或者保留id作为业务字段，仅主键改为fid

2. **API 返回**
   - 对外API可以继续返回id字段
   - 内部使用fid作为主键

3. **批量插入**
   - 每条记录需要独立生成FID
   - 不能使用同一个FID

4. **测试验证**
   - 修改后需要测试插入功能
   - 验证FID是否正确生成

## 快速修改脚本

创建 `fix_insert_fid.py` 放在项目根目录：

```python
#!/usr/bin/env python3
"""快速为INSERT语句添加FID字段"""
import re
import os

def fix_file(filepath, table_prefix_map):
    """修复单个文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已导入fid_utils
    if 'fid_utils' not in content:
        # 添加导入语句
        import_pattern = r'(from \. import db|from \.service_base import)'
        content = re.sub(
            import_pattern,
            r'from .fid_utils import generate_fid, generate_business_fid  # V47.0\n\1',
            content
        )
    
    # 修复INSERT语句（简化示例，实际需要更复杂的逻辑）
    # 这里仅作为参考，建议手动修改关键文件
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已修复: {filepath}")

# 使用示例
# fix_file('business-common/order_service.py', {'business_orders': 'order'})
```

## 建议执行顺序

1. **第一阶段：核心表**
   - business_orders / order_details
   - business_applications
   - business_members
   - visit_records
   - chat_messages / chat_sessions

2. **第二阶段：业务表**
   - business_reviews
   - business_bookings
   - business_refunds
   - business_feedback

3. **第三阶段：辅助表**
   - 其他所有表

## 验证方法

```python
# 测试FID生成
from business_common.fid_utils import generate_fid, generate_business_fid

print(generate_fid())  # 32位字符串
print(generate_business_fid('order'))  # 带前缀
```

---
**修改完成后，务必进行全量测试！**
