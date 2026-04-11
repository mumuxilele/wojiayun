# AI Chat iOS SDK - 快速开始

## 🚀 5分钟快速集成

### 第一步：下载 SDK

```bash
# 下载项目
git clone https://github.com/wojiayun/aichat-sdk.git
cd aichat-sdk-capacitor
```

### 第二步：安装依赖

```bash
# 安装 npm 依赖
npm install

# 安装 CocoaPods 依赖（iOS）
cd ios/App && pod install && cd ../..
```

### 第三步：集成到 iOS 项目

#### Swift 项目

```swift
// 1. 导入 SDK
import AIChatSDK

// 2. 在需要的地方创建聊天视图
class ViewController: UIViewController {
  override func viewDidLoad() {
    super.viewDidLoad()

    // 创建聊天视图
    let chatView = AIChatSDK.createChatView(
      frame: view.bounds,
      accessToken: "your-access-token",
      customVariables: [
        "empName": "张三",
        "empId": "12345"
      ]
    )

    // 添加到视图
    view.addSubview(chatView)
  }
}
```

#### Objective-C 项目

```objective-c
// 1. 导入头文件
#import "AIChatSDK-Swift.h"

// 2. 创建聊天视图
- (void)viewDidLoad {
  [super viewDidLoad];

  UIView *chatView = [AIChatSDKBridge createChatViewWithFrame:self.view.bounds
                                                  accessToken:@"your-access-token"
                                                      apiUrl:@"https://your-api.com/api"
                                              customVariables:@{
                                                @"empName": @"张三",
                                                @"empId": @"12345"
                                              }];

  [self.view addSubview:chatView];
}
```

## 📱 完整示例

### 示例 1：独立聊天应用

```swift
// AppDelegate.swift
import UIKit
import AIChatSDK

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
  var window: UIWindow?

  func application(_ application: UIApplication,
                   didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {

    // 创建聊天视图控制器
    let chatVC = AIChatSDK.createChatViewController(
      accessToken: "your-access-token",
      apiUrl: "https://your-api.com/api",
      customVariables: [
        "empName": "张三",
        "empId": "12345",
        "userId": "user123"
      ]
    )

    // 设置为根视图控制器
    window = UIWindow(frame: UIScreen.main.bounds)
    window?.rootViewController = chatVC
    window?.makeKeyAndVisible()

    return true
  }
}
```

### 示例 2：TabBar 应用集成

```swift
// TabBarController.swift
import UIKit
import AIChatSDK

class TabBarController: UITabBarController {

  override func viewDidLoad() {
    super.viewDidLoad()

    // 创建聊天视图控制器
    let chatVC = AIChatSDK.createChatViewController(
      accessToken: "your-access-token",
      customVariables: [
        "empName": "张三",
        "empId": "12345"
      ]
    )
    chatVC.tabBarItem = UITabBarItem(
      title: "AI助手",
      image: UIImage(systemName: "message"),
      selectedImage: UIImage(systemName: "message.fill")
    )

    // 设置 TabBar
    viewControllers = [chatVC]
  }
}
```

### 示例 3：Navigation 集成

```swift
// HomeViewController.swift
import UIKit
import AIChatSDK

class HomeViewController: UIViewController {

  @IBAction func openChat(_ sender: UIButton) {
    // 创建聊天视图控制器
    let chatVC = AIChatSDK.createChatViewController(
      accessToken: "your-access-token",
      customVariables: [
        "empName": "张三",
        "empId": "12345"
      ]
    )

    // 导航到聊天页面
    navigationController?.pushViewController(chatVC, animated: true)
  }
}
```

### 示例 4：Modal 弹窗

```swift
// ViewController.swift
import UIKit
import AIChatSDK

class ViewController: UIViewController {

  @IBAction func showChat(_ sender: UIButton) {
    // 创建聊天视图控制器
    let chatVC = AIChatSDK.createChatViewController(
      accessToken: "your-access-token",
      customVariables: [
        "empName": "张三",
        "empId": "12345"
      ]
    )

    // 添加关闭按钮
    let closeButton = UIBarButtonItem(
      barButtonSystemItem: .close,
      target: self,
      action: #selector(dismissChat)
    )
    chatVC.navigationItem.rightBarButtonItem = closeButton

    // 包装在 NavigationController 中
    let navVC = UINavigationController(rootViewController: chatVC)

    // 以 Modal 方式展示
    present(navVC, animated: true)
  }

  @objc func dismissChat() {
    dismiss(animated: true)
  }
}
```

## 🔧 参数配置

### 必需参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| accessToken | String | 访问令牌 | "your-token" |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| apiUrl | String | "/api" | API 地址 |
| customVariables | Dictionary | [:] | 自定义变量 |
| theme | String | "light" | 主题 |

### customVariables 示例

```swift
let customVariables = [
  // 用户信息
  "empName": "张三",           // 员工姓名
  "empId": "12345",           // 员工 ID
  "userId": "user123",        // 用户 ID
  "userName": "zhangsan",     // 用户名

  // 组织信息
  "department": "技术部",      // 部门
  "company": "我家云",         // 公司

  // 其他信息
  "role": "admin",            // 角色
  "region": "北京"            // 地区
]
```

## 🎨 自定义样式

### 修改主题

```swift
// 暗色主题
let chatVC = AIChatSDK.createChatViewController(
  accessToken: "your-token",
  customVariables: [:],
  theme: "dark"
)
```

### 自定义导航栏

```swift
let chatVC = AIChatSDK.createChatViewController(
  accessToken: "your-token"
)

// 设置标题
chatVC.title = "AI 助手"

// 设置导航栏样式
chatVC.navigationController?.navigationBar.barTintColor = .systemBlue
chatVC.navigationController?.navigationBar.tintColor = .white
chatVC.navigationController?.navigationBar.titleTextAttributes = [
  .foregroundColor: UIColor.white
]
```

## 📡 事件监听

### 监听消息事件

```swift
// 监听新消息
AIChatSDK.onMessage { message in
  print("收到消息: \(message)")
}

// 监听错误
AIChatSDK.onError { error in
  print("发生错误: \(error)")
}

// 监听发送消息
AIChatSDK.onSend { message in
  print("发送消息: \(message)")
}
```

## 🔐 权限配置

### Info.plist

```xml
<!-- 麦克风权限 -->
<key>NSMicrophoneUsageDescription</key>
<string>需要麦克风权限进行语音输入</string>

<!-- 语音识别权限 -->
<key>NSSpeechRecognitionUsageDescription</key>
<string>需要语音识别权限进行语音转文字</string>

<!-- 网络权限 -->
<key>NSAppTransportSecurity</key>
<dict>
  <key>NSAllowsArbitraryLoads</key>
  <true/>
</dict>
```

## 🐛 常见问题

### Q1: 如何获取 access_token?

```swift
// 从服务器获取
func fetchAccessToken(completion: @escaping (String?) -> Void) {
  let url = URL(string: "https://your-api.com/auth/token")!
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

// 使用
fetchAccessToken { token in
  guard let token = token else { return }

  let chatVC = AIChatSDK.createChatViewController(
    accessToken: token,
    customVariables: [
      "empName": "张三",
      "empId": "12345"
    ]
  )

  DispatchQueue.main.async {
    self.present(chatVC, animated: true)
  }
}
```

### Q2: 如何处理登录状态？

```swift
class ChatManager {
  static let shared = ChatManager()

  private var accessToken: String?

  func login(username: String, password: String, completion: @escaping (Bool) -> Void) {
    // 登录逻辑
    // ...

    // 保存 token
    self.accessToken = "your-token"
    completion(true)
  }

  func showChat(in viewController: UIViewController) {
    guard let token = accessToken else {
      // 未登录，跳转到登录页
      let loginVC = LoginViewController()
      viewController.present(loginVC, animated: true)
      return
    }

    // 已登录，显示聊天
    let chatVC = AIChatSDK.createChatViewController(
      accessToken: token,
      customVariables: [
        "empName": "张三",
        "empId": "12345"
      ]
    )
    viewController.present(chatVC, animated: true)
  }
}

// 使用
ChatManager.shared.showChat(in: self)
```

### Q3: 如何实现多语言？

```swift
// 根据系统语言设置参数
let language = Locale.current.languageCode ?? "zh"

let chatVC = AIChatSDK.createChatViewController(
  accessToken: "your-token",
  customVariables: [
    "empName": "张三",
    "empId": "12345",
    "language": language  // 传递语言参数
  ]
)
```

### Q4: 如何调试？

```swift
// 启用调试模式
AIChatSDK.enableDebugMode(true)

// 查看日志
AIChatSDK.onLog { log in
  print("[AIChatSDK] \(log)")
}
```

## 📦 打包发布

### 构建 Framework

```bash
# 1. 构建 Web 资源
npm run build

# 2. 同步到 iOS
npx cap sync ios

# 3. 打开 Xcode
npx cap open ios

# 4. 在 Xcode 中 Archive
# Product -> Archive -> Distribute App
```

### 发布到 CocoaPods

```bash
# 1. 注册 trunk
pod trunk register your@email.com 'Your Name'

# 2. 发布
pod trunk push AIChatSDK.podspec
```

## 📞 技术支持

- 📧 Email: dev@wojiayun.com
- 📖 文档: https://docs.wojiayun.com/aichat-sdk
- 🐛 Issues: https://github.com/wojiayun/aichat-sdk/issues

---

**开始使用 AI Chat iOS SDK，为您的应用添加智能对话功能！** 🚀
