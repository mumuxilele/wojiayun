# 我家云项目同步技能

我家云(wojia cloud)项目管理接口，包含项目同步、获取Token等核心接口。

## 安装依赖

```bash
pip install requests
```

## 使用方法

### 方式1: 命令行使用

```bash
cd scripts
python3 main.py "项目名称" "项目编号"
```

示例：
```bash
# 同步项目
python3 main.py "测试项目" "test001"

# 仅传项目名称
python3 main.py "我的项目"
```

### 方式2: 分开执行

```bash
# 1. 先获取Token
python3 auth.py

# 2. 同步项目
python3 sync_project.py "项目名称" "项目编号"
```

## 认证流程

正确的认证流程：
1. 调用 `/api/users/ticket` 获取ticket
2. 调用 `/api/users/access_token` 获取access_token
3. 使用access_token调用项目API

## 文件说明

| 文件 | 说明 |
|------|------|
| main.py | 主程序(推荐使用) |
| auth.py | 获取Token |
| sync_project.py | 同步项目 |
| config.py | 配置文件 |

## 配置修改

直接编辑 `main.py` 中的配置：

```python
APP_KEY = "your_app_key"
APP_SECRET = "your_app_secret"
PID = "your_project_id"
NUMBER = "your_phone_number"
```
