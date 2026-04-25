# 云之家聊天机器人模块 (V51.0)

## 功能概述

基于云之家开放平台 IM 接口规范实现的聊天机器人管理模块，支持在企业管理后台统一管理云之家群组消息推送功能。

## 访问地址

```
http://47.98.238.209:22313/yzj.html?access_token=YOUR_TOKEN
```

## 功能特性

### 1. 📤 发送消息
支持多种消息类型：
- **文本消息** - 纯文本内容，支持 @提醒功能
- **Markdown** - 富文本格式，支持标题、列表、链接等
- **卡片消息** - 带标题、内容和跳转链接的卡片
- **图片消息** - 支持图片 URL 发送

### 2. ⚙️ 机器人配置
- 添加/编辑/删除机器人
- 配置 Webhook 地址
- 设置 AppKey/AppSecret 用于接口鉴权
- 启用/禁用机器人

### 3. 📝 消息模板
- 创建常用消息模板
- 支持模板分类管理
- 快速使用模板发送
- 使用次数统计

### 4. 📜 发送记录
- 查看历史发送记录
- 按状态筛选(全部/成功/失败)
- 失败消息支持重发
- 详细发送日志查看

### 5. 👥 群组管理
- 同步云之家群组列表
- 群组与机器人绑定
- 查看群组成员数量

### 6. 📚 API 文档
内置云之家开放平台接口文档说明，包括：
- 接口基础信息
- 鉴权参数说明
- 请求/响应示例

## 后端接口列表

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/yzj/stats` | GET | 获取统计数据 |
| `/api/admin/yzj/robots` | GET | 获取机器人列表 |
| `/api/admin/yzj/robots` | POST | 创建/更新机器人 |
| `/api/admin/yzj/robots/<id>` | DELETE | 删除机器人 |
| `/api/admin/yzj/groups` | GET | 获取群组列表 |
| `/api/admin/yzj/groups/sync` | POST | 同步群组 |
| `/api/admin/yzj/send` | POST | 发送消息 |
| `/api/admin/yzj/templates` | GET | 获取模板列表 |
| `/api/admin/yzj/templates` | POST | 创建模板 |
| `/api/admin/yzj/templates/<id>` | DELETE | 删除模板 |
| `/api/admin/yzj/history` | GET | 获取发送记录 |

## 数据库表结构

详见 `sql/V51_yzj_chatbot.sql`

### 核心表

1. **yzj_chatbot_robots** - 机器人配置表
2. **yzj_chatbot_groups** - 群组管理表
3. **yzj_chatbot_templates** - 消息模板表
4. **yzj_chatbot_send_logs** - 发送日志表

## 云之家开放平台规范

参照文档: https://open.yunzhijia.com/opendocs/docs.html#/api/im/chatbot

### 鉴权方式

```
sign = SHA256(appKey + timestamp + appSecret)
```

### 消息格式示例

**文本消息:**
```json
{
  "msgType": "text",
  "content": {
    "text": "这是一条文本消息"
  }
}
```

**卡片消息:**
```json
{
  "msgType": "card",
  "content": {
    "card": {
      "title": "卡片标题",
      "content": "卡片内容",
      "url": "https://example.com"
    }
  }
}
```

## 使用步骤

1. **执行数据库脚本**
   ```bash
   mysql -u root -p visit_system < sql/V51_yzj_chatbot.sql
   ```

2. **配置机器人**
   - 访问 `yzj.html` 页面
   - 在"机器人配置"中添加云之家机器人
   - 填写 Webhook 地址和 AppKey/AppSecret

3. **同步群组**
   - 在"群组管理"中点击"同步群组"
   - 选择要绑定的机器人

4. **发送消息**
   - 进入"发送消息"页面
   - 选择消息类型和目标群组
   - 填写消息内容并发送

## 注意事项

1. 所有接口需要管理员登录权限
2. 数据按照 ec_id 和 project_id 进行隔离
3. 当前版本为演示版本，实际发送需要配置云之家开放平台的真实参数
4. 发送失败的消息可以在"发送记录"中查看并重试

## 后续优化

- [ ] 集成真实的云之家 Webhook 调用
- [ ] 支持消息定时发送
- [ ] 增加消息撤回功能
- [ ] 支持批量群发
- [ ] 增加消息阅读统计
