# 我家云项目同步技能

我家云(wojia cloud)项目管理接口，包含项目同步、获取Token等核心接口。

## 功能

1. **获取访问Token** - 获取API调用凭证
2. **同步项目** - 创建或更新项目信息
3. **项目列表** - 获取已有项目列表

## 使用方法

### 1. 获取Token

```bash
cd scripts
python3 auth.py
```

### 2. 同步项目

```bash
cd scripts
python3 sync_project.py <项目名称> [项目编号]
```

### 3. 示例

```bash
# 获取Token
python3 auth.py

# 同步项目
python3 sync_project.py "测试项目" "test_project"
```

## 接口说明

### 获取Token

- **URL**: https://api.wojiacloud.cn/api/login/login
- **方法**: POST
- **参数**: 
  - appKey: 应用密钥
  - appSecret: 应用密码

### 同步项目

- **URL**: https://api.wojiacloud.cn/api/projects/sync_project
- **方法**: POST
- **认证**: 需要 access_token 参数

## 配置

在 `scripts/config.py` 中配置：

```python
APP_KEY = "6w6caainm1he2hhg"
APP_SECRET = "gbxvr8hyti3vt29194e9zif6xu5164sg"
```
