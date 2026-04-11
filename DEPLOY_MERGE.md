# 服务合并部署指南

## 已完成的合并

### 1. 端口22306 → 端口22313
- ✅ 走访台账API已迁移到 `business-admin/app.py`
- ✅ 前端页面API地址已更新：
  - `business-admin/visit_admin.html`
  - `business-staffH5/visit_list.html`
- ✅ ecosystem.config.js 已移除 wojiayun-backend

### 2. 端口22316 废弃
- ✅ ecosystem.config.js 已移除 wojiayun-frontend
- ✅ 创建了 Nginx 配置文件 `nginx/wojiayun.conf`

## 部署步骤

### 第一步：提交代码到Git

```bash
cd /www/wwwroot/wojiayun
git add .
git commit -m "合并服务：22306→22313，废弃22316，使用Nginx替代"
git push origin master
```

### 第二步：停止旧服务

```bash
# 停止22306和22316服务
pm2 stop wojiayun-backend
pm2 stop wojiayun-frontend
pm2 delete wojiayun-backend
pm2 delete wojiayun-frontend
```

### 第三步：部署Nginx配置

```bash
# 复制Nginx配置
cp /www/wwwroot/wojiayun/nginx/wojiayun.conf /etc/nginx/conf.d/

# 测试Nginx配置
nginx -t

# 重载Nginx
nginx -s reload
```

### 第四步：重启管理后台服务

```bash
# 重启管理后台（包含走访台账API）
pm2 restart wojiayun-admin
```

### 第五步：更新PM2配置

```bash
# 拉取最新代码
cd /www/wwwroot/wojiayun
git pull

# 使用新的ecosystem.config.js
pm2 start ecosystem.config.js --update-env

# 保存PM2配置
pm2 save
```

## 服务架构变化

### 合并前
```
22306: 走访台账后端 (Python Flask)
22316: 统一前端服务 (Node.js + WebSocket)
22309: 聊天服务 (Node.js WebSocket)
22313: 管理后台 (Python Flask)
```

### 合并后
```
22309: 聊天服务 (Node.js WebSocket) - 保持不变
22313: 管理后台 (Python Flask) - 包含走访台账API
22316: Nginx静态文件服务 + WebSocket代理
```

## 节省资源

- 减少2个Node.js/Python进程
- 预计节省内存：150-250MB

## 验证测试

### 1. 测试走访台账功能
```bash
# 管理端走访台账
curl "http://47.98.238.209:22313/api/admin/visits?access_token=xxx"

# 员工端走访列表
# 访问 http://47.98.238.209:22312/visit_list.html
```

### 2. 测试聊天功能
```bash
# 用户端聊天
# 访问 http://47.98.238.209:22316/chat/user.html?access_token=xxx

# 客服工作台
# 访问 http://47.98.238.209:22316/chat/staff.html?access_token=xxx
```

### 3. 检查服务状态
```bash
pm2 list
pm2 logs wojiayun-admin
```

## 回滚方案

如果出现问题，可以快速回滚：

```bash
# 恢复旧服务
pm2 start /www/wwwroot/wojiayun/backend/app.py --name wojiayun-backend
pm2 start /www/wwwroot/wojiayun/frontend/unified_server.js --name wojiayun-frontend

# 恢复Nginx配置
# 删除 /etc/nginx/conf.d/wojiayun.conf
nginx -s reload
```

## 注意事项

1. **数据库字段**：走访台账表需要添加 `ec_id` 和 `project_id` 字段（如果还没有）
   ```sql
   ALTER TABLE visit_records ADD COLUMN ec_id VARCHAR(64) COMMENT '企业ID';
   ALTER TABLE visit_records ADD COLUMN project_id VARCHAR(64) COMMENT '项目ID';
   ```

2. **前端缓存**：部署后建议清除浏览器缓存，或使用Ctrl+F5强制刷新

3. **日志监控**：部署后密切监控日志，确保没有错误
   ```bash
   pm2 logs wojiayun-admin --lines 100
   ```

## API路由变化

| 原路由 (22306) | 新路由 (22313) |
|----------------|----------------|
| `/api/visits` | `/api/admin/visits` |
| `/api/visits/:id` | `/api/admin/visits/:id` |
| `/api/visits/stats` | `/api/admin/visits/stats` |
| `/api/employees/search` | `/api/admin/employees/search` |

前端页面已更新API地址，无需手动修改。
