# 客户批量导入 - 我家云系统

将Excel/CSV文件中的客户数据批量导入到我家云系统。

## 使用方法

### 运行脚本

```bash
cd skills/wojia-customers
python3 scripts/import_customers.py <excel或csv文件>
```

### 生成模板

```bash
python3 scripts/import_customers.py --template
```

## 认证模块

### 手动刷新Token

```bash
# 刷新token
python3 scripts/auth.py --refresh

# 检查token状态
python3 scripts/auth.py --check
```

### Token缓存机制

- Token自动缓存24小时
- 脚本会自动检测token有效性
- 过期前自动刷新

## 配置说明

### 修改API凭证

编辑 `scripts/auth.py`：

```python
APP_KEY = "your_app_key"
APP_SECRET = "your_app_secret"
PID = "your_project_id"
NUMBER = "your_phone_number"
```

## 特性

- 自动获取/缓存Token
- 自动识别Excel列头（支持中文列名）
- 中文值自动转英文（如：个人→P，企业→E）
- 自动修复数据（企业无证件号自动生成）
- 分批导入（每批50条）
- 详细的导入日志
