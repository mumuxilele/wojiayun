# V47.0 代码修改指南

## 概述

将单据表主键从自增 INT/BIGINT 改为 VARCHAR(32) 的 FID，需要修改以下代码：

1. INSERT 语句 - 使用 fid_utils.generate_fid() 生成主键
2. 外键关联 - 使用 fid 字段替代 id 字段
3. 查询语句 - 使用 fid 作为主键查询

## 修改步骤

### 1. 导入 fid_utils 模块

在所有需要生成 FID 的文件顶部添加：

```python
from business_common.fid_utils import generate_fid, generate_business_fid
```

### 2. 修改 INSERT 语句

#### 修改前：
```python
sql = """
    INSERT INTO business_orders 
    (order_no, user_id, total_amount, status)
    VALUES (%s, %s, %s, %s)
"""
cursor.execute(sql, (order_no, user_id, total_amount, status))
order_id = cursor.lastrowid  # 获取自增ID
```

#### 修改后：
```python
from business_common.fid_utils import generate_fid

fid = generate_fid()  # 先生成FID

sql = """
    INSERT INTO business_orders 
    (fid, order_no, user_id, total_amount, status)
    VALUES (%s, %s, %s, %s, %s)
"""
cursor.execute(sql, (fid, order_no, user_id, total_amount, status))
order_id = fid  # 直接使用fid
```

### 3. 修改外键关联

#### 修改前：
```python
sql = """
    INSERT INTO business_order_items 
    (order_id, product_id, quantity, price)
    VALUES (%s, %s, %s, %s)
"""
cursor.execute(sql, (order_id, product_id, quantity, price))
```

#### 修改后：
```python
sql = """
    INSERT INTO business_order_items 
    (order_fid, product_fid, quantity, price)
    VALUES (%s, %s, %s, %s)
"""
cursor.execute(sql, (order_fid, product_fid, quantity, price))
```

### 4. 修改主键查询

#### 修改前：
```python
sql = "SELECT * FROM business_orders WHERE id = %s"
cursor.execute(sql, (order_id,))
```

#### 修改后：
```python
sql = "SELECT * FROM business_orders WHERE fid = %s"
cursor.execute(sql, (order_fid,))
```

## 需要修改的文件清单

### 高优先级（核心单据表）

1. `business_common/order_service.py` - 订单服务
2. `business_common/application_service.py` - 申请服务
3. `business_common/booking_service.py` - 预约服务
4. `business_common/refund_service.py` - 退款服务
5. `business_common/member_service.py` - 会员服务
6. `business_common/review_service.py` - 评价服务
7. `business_common/visit_service.py` - 走访服务

### 中优先级（辅助功能）

8. `business_common/cart_service.py` - 购物车服务
9. `business_common/coupon_service.py` - 优惠券服务
10. `business_common/invoice_service.py` - 发票服务
11. `business_common/aftersales_service.py` - 售后服务
12. `business_common/payment_service.py` - 支付服务

### 低优先级（配置和统计）

13. `business_common/notification_service.py` - 通知服务
14. `business_common/log_service.py` - 日志服务

## 批量修改脚本

创建 `sql/batch_update_code.py` 来批量修改代码：

```python
#!/usr/bin/env python3
"""
批量修改代码中的INSERT语句，添加FID生成
"""
import os
import re

# 需要修改的文件列表
FILES_TO_UPDATE = [
    'business_common/order_service.py',
    'business_common/application_service.py',
    # ... 其他文件
]

def add_fid_import(content):
    """添加fid_utils导入"""
    if 'from business_common.fid_utils import' in content:
        return content
    
    # 在文件头部添加导入
    import_stmt = 'from business_common.fid_utils import generate_fid\n'
    
    # 找到最后一个import语句后添加
    lines = content.split('\n')
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i
    
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, import_stmt)
    else:
        lines.insert(0, import_stmt)
    
    return '\n'.join(lines)

def update_insert_statements(content):
    """修改INSERT语句"""
    # 这里需要根据实际代码模式编写正则替换规则
    # 示例：
    pattern = r'INSERT INTO (\w+) \(([^)]+)\) VALUES'
    def replace_insert(match):
        table = match.group(1)
        columns = match.group(2)
        if 'fid' not in columns and table.startswith('business_'):
            return f'INSERT INTO {table} (fid, {columns}) VALUES'
        return match.group(0)
    
    return re.sub(pattern, replace_insert, content)

def main():
    for filepath in FILES_TO_UPDATE:
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        content = add_fid_import(content)
        content = update_insert_statements(content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"已更新: {filepath}")
        else:
            print(f"无需修改: {filepath}")

if __name__ == '__main__':
    main()
```

## 注意事项

1. **备份数据库** - 执行前务必备份
2. **分批执行** - 建议分表执行，便于回滚
3. **测试验证** - 在测试环境充分测试后再上生产
4. **外键约束** - 注意外键关联表的修改顺序
5. **API兼容性** - 对外API接口可能需要添加id到fid的映射

## 回滚方案

如果出现问题，可以通过以下SQL回滚：

```sql
-- 恢复自增主键（仅适用于未删除id列的情况）
ALTER TABLE business_orders 
DROP PRIMARY KEY,
ADD PRIMARY KEY (id),
DROP COLUMN fid;
```
