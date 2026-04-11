# AI Chat iOS SDK 开发指南

## 📋 目录

1. [方案选择](#方案选择)
2. [快速开始](#快速开始)
3. [参数传递](#参数传递)
4. [集成示例](#集成示例)
5. [常见问题](#常见问题)

## 🎯 方案选择

### 三种方案对比

| 方案 | 开发周期 | 性能 | 包体积 | 推荐指数 |
|------|---------|------|--------|----------|
| **Capacitor** | 1-2天 | ⭐⭐⭐ | ~15MB | ⭐⭐⭐⭐⭐ |
| **React Native** | 2-3周 | ⭐⭐⭐⭐⭐ | ~10MB | ⭐⭐⭐⭐ |
| **原生 WebView** | 1周 | ⭐⭐⭐ | ~3MB | ⭐⭐⭐ |

### 推荐方案

**快速上手** → Capacitor（推荐）
**最佳性能** → React Native
**最小体积** → 原生 WebView

## 🚀 快速开始

### 方案一：Capacitor（推荐）

#### 1. 环境准备

```bash
# 安装 Node.js
brew install node

# 安装 CocoaPods
sudo gem install cocoapods

# 安装 Capacitor
npm install -g @capacitor/cli
```

#### 2. 创建项目

```bash
# 克隆项目
git clone https://github.com/wojiayun/aichat-sdk.git
cd aichat-sdk-capacitor

# 安装依赖
npm install

# 添加 iOS 平台
npx cap add ios
```

#### 3. 集成到 iOS 项目

**Swift 项目：**

```swift
import AIChatSDK

// 创建聊天视图
let chatView = AIChatSDK.createChatView(
  frame: view.bounds,
  accessToken: "your-token",
  customVariables: [
    "empName": "张三",
    "empId": "12345"
  ]
)
view.addSubview(chatView)
```

**Objective-C 项目：**

```objective-c
#import "AIChatSDK-Swift.h"

UIView *chatView = [AIChatSDKBridge createChatViewWithFrame:self.view.bounds
                                                accessToken:@"your-token"
                                                    apiUrl:@"https://api.com/api"
                                            customVariables:@{
                                              @"empName": @"张三",
                                              @"empId": @"12345"
                                            }];
[self.view addSubview:chatView];
```

### 方案二：React Native

#### 1. 创建项目

```bash
# 创建 React Native 库
npx create-react-native-library aichat-sdk-native

cd aichat-sdk-native
npm install
```

#### 2. 开发组件

```typescript
// src/components/ChatView.tsx
import React from 'react';
import { View } from 'react-native';

export const ChatView: React.FC<ChatViewProps> = ({ accessToken, customVariables }) => {
  // 实现聊天逻辑
  return <View>{/* 聊天界面 */}</View>;
};
```

#### 3. 集成到 iOS

```swift
import AIChatSDK

let chatView = AIChatSDK.createChatView(
  accessToken: "your-token",
  customVariables: ["empName": "张三"]
)
```

### 方案三：原生 WebView

#### 1. 创建 WebView

```swift
import WebKit

let webView = WKWebView(frame: view.bounds)

// 加载本地 HTML
if let htmlPath = Bundle.main.path(forResource: "index", ofType: "html") {
  let htmlUrl = URL(fileURLWithPath: htmlPath)
  let urlWithParams = URL(string: "\(htmlUrl)?access_token=your-token&empName=张三")!
  webView.load(URLRequest(url: urlWithParams))
}

view.addSubview(webView)
```

## 📝 参数传递

### URL 参数方式

```swift
// 构建参数 URL
var components = URLComponents()
components.queryItems = [
  URLQueryItem(name: "access_token", value: "your-token"),
  URLQueryItem(name: "empName", value: "张三"),
  URLQueryItem(name: "empId", value: "12345")
]

let url = URL(string: "index.html?\(components.query ?? "")")!
webView.load(URLRequest(url: url))
```

### JavaScript Bridge 方式

```swift
// Swift 端
let script = """
window.chatConfig = {
  accessToken: '\(accessToken)',
  customVariables: {
    empName: '\(empName)',
    empId: '\(empId)'
  }
};
"""

webView.evaluateJavaScript(script)
```

```javascript
// JavaScript 端
const config = window.chatConfig || {
  accessToken: getUrlParam('access_token'),
  customVariables: {
    empName: getUrlParam('empName'),
    empId: getUrlParam('empId')
  }
};
```

### Native Module 方式

```swift
// Swift 原生模块
@objc(ChatConfigModule)
class ChatConfigModule: NSObject {
  @objc static func getConfig() -> [String: Any] {
    return [
      "accessToken": "your-token",
      "customVariables": [
        "empName": "张三",
        "empId": "12345"
      ]
    ]
  }
}
```

## 💡 集成示例

### 示例 1：独立应用

```swift
// AppDelegate.swift
import AIChatSDK

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
  var window: UIWindow?

  func application(_ application: UIApplication,
                   didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {

    let chatVC = AIChatSDK.createChatViewController(
      accessToken: "your-token",
      customVariables: [
        "empName": "张三",
        "empId": "12345"
      ]
    )

    window = UIWindow(frame: UIScreen.main.bounds)
    window?.rootViewController = chatVC
    window?.makeKeyAndVisible()

    return true
  }
}
```

### 示例 2：TabBar 集成

```swift
// TabBarController.swift
import AIChatSDK

class TabBarController: UITabBarController {
  override func viewDidLoad() {
    super.viewDidLoad()

    let chatVC = AIChatSDK.createChatViewController(
      accessToken: "your-token",
      customVariables: ["empName": "张三"]
    )
    chatVC.tabBarItem = UITabBarItem(title: "AI助手", image: UIImage(systemName: "message"), tag: 0)

    viewControllers = [chatVC]
  }
}
```

### 示例 3：Modal 弹窗

```swift
// ViewController.swift
import AIChatSDK

class ViewController: UIViewController {
  @IBAction func showChat(_ sender: UIButton) {
    let chatVC = AIChatSDK.createChatViewController(
      accessToken: "your-token",
      customVariables: ["empName": "张三"]
    )

    let navVC = UINavigationController(rootViewController: chatVC)
    navVC.modalPresentationStyle = .fullScreen

    present(navVC, animated: true)
  }
}
```

## ❓ 常见问题

### Q1: 如何获取 access_token？

**方式 1：从服务器获取**

```swift
func fetchToken(completion: @escaping (String?) -> Void) {
  guard let url = URL(string: "https://your-api.com/auth/token") else {
    completion(nil)
    return
  }

  URLSession.shared.dataTask(with: url) { data, _, _ in
    if let data = data,
       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
       let token = json["access_token"] as? String {
      completion(token)
    } else {
      completion(nil)
    }
  }.resume()
}
```

**方式 2：从本地存储读取**

```swift
let token = UserDefaults.standard.string(forKey: "access_token")
```

**方式 3：从 Keychain 读取**

```swift
// 使用 KeychainAccess 库
import KeychainAccess

let keychain = Keychain(service: "com.wojiayun.app")
let token = try? keychain.get("access_token")
```

### Q2: 如何处理用户登录？

```swift
class AuthManager {
  static let shared = AuthManager()
  private(set) var accessToken: String?
  private(set) var userInfo: [String: String]?

  func login(username: String, password: String, completion: @escaping (Bool) -> Void) {
    // 调用登录接口
    // ...

    // 保存 token 和用户信息
    self.accessToken = "your-token"
    self.userInfo = [
      "empName": "张三",
      "empId": "12345"
    ]

    completion(true)
  }

  func logout() {
    accessToken = nil
    userInfo = nil
  }
}

// 使用
if let token = AuthManager.shared.accessToken,
   let userInfo = AuthManager.shared.userInfo {
  let chatVC = AIChatSDK.createChatViewController(
    accessToken: token,
    customVariables: userInfo
  )
  present(chatVC, animated: true)
}
```

### Q3: 如何自定义主题？

```swift
// 传递主题参数
let chatVC = AIChatSDK.createChatViewController(
  accessToken: "your-token",
  customVariables: [
    "empName": "张三",
    "theme": "dark"  // 暗色主题
  ]
)
```

### Q4: 如何处理网络错误？

```swift
// 监听错误事件
AIChatSDK.onError { error in
  if let networkError = error as? NetworkError {
    switch networkError {
    case .noConnection:
      showAlert("网络连接失败")
    case .timeout:
      showAlert("请求超时")
    case .serverError:
      showAlert("服务器错误")
    }
  }
}
```

### Q5: 如何实现离线缓存？

```swift
// 使用 WKWebView 的缓存策略
let configuration = WKWebViewConfiguration()
configuration.websiteDataStore = WKWebsiteDataStore.default()

let webView = WKWebView(frame: view.bounds, configuration: configuration)

// 启用缓存
URLCache.shared = URLCache(
  memoryCapacity: 50 * 1024 * 1024,  // 50MB 内存缓存
  diskCapacity: 200 * 1024 * 1024,   // 200MB 磁盘缓存
  diskPath: "aichat_cache"
)
```

## 📚 相关文档

- [Capacitor 方案详细文档](./aichat-sdk-capacitor/README.md)
- [React Native 方案详细文档](./aichat-sdk-native/README.md)
- [方案对比文档](./iOS-SDK-COMPARISON.md)
- [快速开始指南](./aichat-sdk-capacitor/QUICKSTART.md)

## 📞 技术支持

- 📧 Email: dev@wojiayun.com
- 📖 文档: https://docs.wojiayun.com/aichat-sdk
- 🐛 Issues: https://github.com/wojiayun/aichat-sdk/issues

---

**选择适合您的方案，开始集成 AI Chat SDK！** 🚀
