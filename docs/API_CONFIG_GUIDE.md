# API配置指南 V32.0

本文档提供我家云社区商业系统第三方API配置指南，用于生产环境部署。

---

## 一、环境变量配置

### 1.1 配置方式

生产环境通过环境变量配置敏感信息，示例:

```bash
# Linux/Mac
export DB_HOST=your_db_host
export DB_PASSWORD=your_db_password
export DB_NAME=visit_system

# Windows PowerShell
$env:DB_HOST="your_db_host"
$env:DB_PASSWORD="your_db_password"
```

或在PM2进程管理中配置:

```javascript
// ecosystem.config.js
{
  env: {
    DB_HOST: '47.98.238.209',
    DB_PASSWORD: 'your_password',
    // ... 其他配置
  }
}
```

### 1.2 必需配置

| 变量名 | 必需 | 说明 | 示例值 |
|--------|------|------|--------|
| `DB_HOST` | 是 | 数据库地址 | 47.98.238.209 |
| `DB_PASSWORD` | 是 | 数据库密码 | your_password |
| `DB_NAME` | 是 | 数据库名 | visit_system |
| `DB_USER` | 否 | 数据库用户 | root |
| `DB_PORT` | 否 | 数据库端口 | 3306 |

---

## 二、微信支付配置

### 2.1 申请材料

1. 微信支付商户号 (MCHID)
2. 商户证书 (apiclient_key.pem, apiclient_cert.pem)
3. 证书序列号
4. APIv3密钥 (32位随机字符串)

### 2.2 配置步骤

#### 步骤1: 获取微信支付资质

访问 [微信支付商户平台](https://pay.weixin.qq.com) 申请入驻

#### 步骤2: 获取API证书

1. 登录商户平台
2. 进入「账户中心」→「API安全」
3. 下载证书

#### 步骤3: 设置APIv3密钥

1. 在商户平台设置32位APIv3密钥
2. 保存好密钥，微信不提供找回功能

### 2.3 环境变量配置

```bash
# 微信支付配置
export WECHAT_APP_ID=wx1234567890abcdef   # 公众号AppID
export WECHAT_MCH_ID=1234567890            # 商户号
export WECHAT_SERIAL_NO=XXXXXXXXXXXXXXXXXX # 证书序列号
export WECHAT_API_V3_KEY=your_api_v3_key_32_chars   # APIv3密钥
```

证书文件放置在安全位置:

```bash
# 私钥文件
export WECHAT_PRIVATE_KEY_PATH=/path/to/apiclient_key.pem

# 证书文件
export WECHAT_CERT_PATH=/path/to/apiclient_cert.pem
```

### 2.4 支付回调配置

在微信支付商户平台设置支付回调URL:

```
https://your-domain.com/api/user/payment/callback
```

### 2.5 代码配置位置

```python
# business-common/payment_service.py
WECHAT_CONFIG = {
    'app_id': os.environ.get('WECHAT_APP_ID', ''),
    'mch_id': os.environ.get('WECHAT_MCH_ID', ''),
    'serial_no': os.environ.get('WECHAT_SERIAL_NO', ''),
    'api_v3_key': os.environ.get('WECHAT_API_V3_KEY', ''),
    'private_key': load_from_file(os.environ.get('WECHAT_PRIVATE_KEY_PATH')),
    'notify_url': os.environ.get('WECHAT_NOTIFY_URL', ''),
}
```

---

## 三、支付宝支付配置

### 3.1 申请材料

1. 支付宝开放平台应用AppID
2. 应用私钥 (rsa_private_key.pem)
3. 支付宝公钥 (rsa_public_key.pem)

### 3.2 配置步骤

#### 步骤1: 创建应用

访问 [支付宝开放平台](https://open.alipay.com) 创建应用

#### 步骤2: 获取密钥

1. 使用支付宝密钥工具生成RSA2密钥对
2. 在开放平台上传公钥获取支付宝公钥

### 3.3 环境变量配置

```bash
# 支付宝配置
export ALIPAY_APP_ID=2021001234567890       # 应用AppID
export ALIPAY_PRIVATE_KEY=your_private_key  # 应用私钥(RSA2)
export ALIPAY_PUBLIC_KEY=alipay_public_key   # 支付宝公钥
export ALIPAY_NOTIFY_URL=https://your-domain.com/api/user/payment/alipay/callback
```

### 3.4 代码配置位置

```python
# business-common/payment_service.py
ALIPAY_CONFIG = {
    'app_id': os.environ.get('ALIPAY_APP_ID', ''),
    'private_key': os.environ.get('ALIPAY_PRIVATE_KEY', ''),
    'alipay_public_key': os.environ.get('ALIPAY_PUBLIC_KEY', ''),
    'notify_url': os.environ.get('ALIPAY_NOTIFY_URL', ''),
    'gateway': 'https://openapi.alipay.com/gateway.do',
}
```

---

## 四、物流追踪配置

### 4.1 快递100 API

#### 申请方式

1. 访问 [快递100官网](https://www.kuaidi100.com)
2. 注册并申请API接口
3. 免费版每天100次查询

#### 环境变量配置

```bash
# 快递100配置
export KUAIDI100_KEY=your_kuaidi100_key
export KUAIDI100_CUSTOMER=your_customer_code
```

#### 订阅推送配置

设置回调URL接收物流状态变更:

```
https://your-domain.com/api/user/logistics/subscribe
```

### 4.2 菜鸟物流 API (可选)

```bash
# 菜鸟物流配置
export CN_TAOBAO_API=your_taobao_api_url
export CN_TAOBAO_SECRET=your_secret
```

### 4.3 代码配置位置

```python
# business-common/logistics_service.py
KUAIDI100_API = 'https://poll.kuaidi100.com/poll/query.do'
KUAIDI100_SUBSCRIBE = 'https://poll.kuaidi100.com/poll/subscribe.do'
KUAIDI100_KEY = os.environ.get('KUAIDI100_KEY', '')
KUAIDI100_CUSTOMER = os.environ.get('KUAIDI100_CUSTOMER', '')
```

---

## 五、短信服务配置

### 5.1 阿里云短信服务

#### 申请步骤

1. 访问 [阿里云短信服务](https://dysms.console.aliyun.com)
2. 开通短信服务
3. 申请签名和模板
4. 获取AccessKey

#### 环境变量配置

```bash
# 阿里云短信配置
export ALIYUN_ACCESS_KEY_ID=your_access_key_id
export ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret
export ALIYUN_SMS_SIGN_NAME=我家云      # 签名名称
export ALIYUN_SMS_TEMPLATE_LOGIN=SMS_xxx  # 登录验证码模板
export ALIYUN_SMS_TEMPLATE_ORDER=SMS_xxx  # 订单通知模板
```

#### 模板示例

| 模板名称 | 模板内容 |
|----------|----------|
| 登录验证码 | 您的验证码是${code}，5分钟内有效 |
| 订单通知 | 您的订单${order_no}已${status} |

### 5.2 代码配置位置

```python
# business-common/push_service.py
ALIYUN_SMS_CONFIG = {
    'access_key_id': os.environ.get('ALIYUN_ACCESS_KEY_ID', ''),
    'access_key_secret': os.environ.get('ALIYUN_ACCESS_KEY_SECRET', ''),
    'sign_name': os.environ.get('ALIYUN_SMS_SIGN_NAME', ''),
    'template_login': os.environ.get('ALIYUN_SMS_TEMPLATE_LOGIN', ''),
}
```

---

## 六、微信订阅消息配置

### 6.1 申请步骤

1. 在微信公众平台申请订阅消息
2. 选择所需消息模板
3. 获取模板ID

### 6.2 推荐模板

| 模板名称 | 模板ID | 用途 |
|----------|--------|------|
| 订单状态通知 | TM00001 | 订单支付/发货/签收 |
| 预约成功通知 | TM00781 | 场地预约确认 |
| 会员积分变动 | TM00006 | 积分增减通知 |

### 6.3 环境变量配置

```bash
# 微信订阅消息配置
export WECHAT_TEMPLATE_ORDER=TM00001
export WECHAT_TEMPLATE_BOOKING=TM00781
export WECHAT_TEMPLATE_POINTS=TM00006
```

---

## 七、生产环境部署检查清单

### 7.1 必检项

```markdown
□ 数据库密码已修改为强密码
□ DB_PASSWORD环境变量已设置
□ 微信支付商户号已配置
□ 微信支付APIv3密钥已设置
□ 支付宝应用已创建并配置
□ 物流追踪API Key已配置
□ 所有回调URL已正确设置
□ HTTPS已启用(生产必需)
```

### 7.2 推荐检项

```markdown
□ 短信服务已开通并配置
□ 微信订阅消息已申请
□ 日志系统已配置
□ 监控告警已设置
□ 定期备份已配置
```

---

## 八、环境变量模板

创建 `.env.example` 文件供参考:

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=change_me_in_production
DB_NAME=visit_system

# 微信支付配置
WECHAT_APP_ID=
WECHAT_MCH_ID=
WECHAT_SERIAL_NO=
WECHAT_API_V3_KEY=
WECHAT_PRIVATE_KEY_PATH=
WECHAT_CERT_PATH=

# 支付宝配置
ALIPAY_APP_ID=
ALIPAY_PRIVATE_KEY=
ALIPAY_PUBLIC_KEY=

# 物流追踪配置
KUAIDI100_KEY=
KUAIDI100_CUSTOMER=

# 短信服务配置
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
ALIYUN_SMS_SIGN_NAME=

# 微信订阅消息
WECHAT_TEMPLATE_ORDER=
WECHAT_TEMPLATE_BOOKING=
```

---

## 九、常见问题

### Q1: 支付回调验签失败

1. 检查证书文件是否正确
2. 确认APIv3密钥是否匹配
3. 检查回调URL是否正确

### Q2: 物流查询无数据

1. 确认快递100 Key配置正确
2. 检查订阅推送是否开通
3. 验证快递单号格式

### Q3: 短信发送失败

1. 检查AccessKey权限
2. 确认签名和模板已审核通过
3. 查看阿里云短信服务日志

---

**文档版本**: V1.0
**更新日期**: 2026-04-05
