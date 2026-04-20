# V47.0 数据库迁移执行步骤

## 前置条件
1. 确保数据库已备份
2. 确保应用在低峰期

## 执行步骤

### 1. 登录服务器并进入项目目录
```bash
ssh root@47.98.238.209
cd /www/wwwroot/wojiayun
```

### 2. 备份数据库（必须）
```bash
mkdir -p /www/backup
mysqldump -u root -p visit_system > /www/backup/visit_system_$(date +%Y%m%d_%H%M%S).sql
# 输入MySQL密码
```

### 3. 检查备份是否成功
```bash
ls -lh /www/backup/*.sql | tail -3
```

### 4. 执行数据库迁移
```bash
cd /www/wwwroot/wojiayun
python sql/migrate_v47.py
```

根据提示输入 `yes` 确认执行。

### 5. 检查迁移结果
```bash
mysql -u root -p -e "USE visit_system; DESCRIBE business_orders;" | grep fid
```

### 6. 重启服务
```bash
pm2 restart all
pm2 logs --lines 20
```

## 回滚方案

如果出现问题，可以通过备份恢复：

```bash
mysql -u root -p visit_system < /www/backup/visit_system_xxxxxxxx.sql
```

## 验证命令

检查订单表FID是否正常生成：
```sql
SELECT fid, id, order_no FROM business_orders ORDER BY created_at DESC LIMIT 5;
```

检查所有表是否都有fid列：
```sql
SELECT TABLE_NAME, COLUMN_NAME 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'visit_system' 
AND COLUMN_NAME = 'fid';
```
