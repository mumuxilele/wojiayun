# Cookie Browser Loader

使用配置文件中的Cookie打开浏览器并加载指定网页。

## 使用方法

### 1. 准备Cookie配置

复制示例配置文件并填入您的Cookie：

```bash
cp cookies.example.json cookies.json
```

编辑 `cookies.json`，填入您的Cookie：

```json
{
  "url": "https://www.wojiacloud.cn",
  "cookies": [
    {
      "name": "session_id",
      "value": "您的Cookie值",
      "domain": ".wojiacloud.cn",
      "path": "/"
    }
  ]
}
```

### 2. 安装依赖

```bash
pip install selenium webdriver-manager
```

### 3. 运行

```bash
python cookie_browser.py "https://www.wojiacloud.cn/h5/xxx"
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `url` | 要加载的网页URL（必需） |
| `-c, --config` | Cookie配置文件路径（默认：cookies.json） |
| `-e, --example` | 生成示例配置文件 |

## 示例

```bash
# 生成示例配置
python cookie_browser.py -e

# 使用Cookie打开网页
python cookie_browser.py "https://www.wojiacloud.cn/h5/equipmentProjectReport"
```
