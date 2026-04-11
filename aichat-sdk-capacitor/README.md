# AI Chat iOS SDK - Capacitor 方案

## 简介

使用 Capacitor 将现有的 Web React SDK 快速打包成 iOS SDK。

**优点**：
- 快速打包，无需重写代码
- 保留所有 Web 功能
- 支持原生插件扩展

**适合**：
- 已有 Web SDK
- 快速验证
- 跨平台需求

## 项目结构

```
aichat-sdk-capacitor/
├── src/                    # Web 源代码
│   ├── index.ts
│   ├── components/
│   └── services/
├── ios/                    # iOS 原生项目
│   └── App/
│       └── App.xcworkspace
├── android/                # Android 原生项目
├── capacitor.config.ts
├── package.json
└── README.md
```

## 快速开始

### 1. 安装 Capacitor

```bash
# 创建项目
npm init -y

# 安装 Capacitor
npm install @capacitor/core @capacitor/cli @capacitor/ios

# 初始化 Capacitor
npx cap init AIChatSDK com.wojiayun.aichat

# 添加 iOS 平台
npx cap add ios
```

### 2. 配置 capacitor.config.ts

```typescript
import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.wojiayun.aichat',
  appName: 'AI Chat SDK',
  webDir: 'dist',
  bundledWebRuntime: false,
  ios: {
    contentInset: 'automatic',
    allowsLinkPreview: false,
    scrollEnabled: true,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 0,
      backgroundColor: '#f5f5f5',
      showSpinner: false,
    },
    Keyboard: {
      resize: 'body',
      resizeOnFullScreen: true,
    },
  },
};

export default config;
```

### 3. 创建 iOS SDK 包装器

```swift
// ios/App/App/AIChatSDK.swift
import Foundation
import Capacitor

@objc public class AIChatSDK: NSObject {
  
  /// 创建聊天视图控制器
  @objc public static func createChatViewController(
    accessToken: String,
    apiUrl: String = "/api",
    customVariables: [String: String] = [:]
  ) -> UIViewController {
    
    // 创建 Capacitor WebView
    let viewController = CAPBridgeViewController()
    
    // 配置 URL 参数
    var urlComponents = URLComponents()
    urlComponents.queryItems = [
      URLQueryItem(name: "access_token", value: accessToken)
    ]
    
    // 添加 custom_variables
    for (key, value) in customVariables {
      urlComponents.queryItems?.append(URLQueryItem(name: key, value: value))
    }
    
    // 设置初始 URL
    viewController.startPath = "/index.html?\(urlComponents.query ?? "")"
    
    return viewController
  }
  
  /// 创建聊天视图（用于嵌入）
  @objc public static func createChatView(
    frame: CGRect,
    accessToken: String,
    apiUrl: String = "/api",
    customVariables: [String: String] = [:]
  ) -> UIView {
    
    let webView = WKWebView(frame: frame)
    
    // 构建带参数的 URL
    var urlComponents = URLComponents()
    urlComponents.queryItems = [
      URLQueryItem(name: "access_token", value: accessToken)
    ]
    
    for (key, value) in customVariables {
      urlComponents.queryItems?.append(URLQueryItem(name: key, value: value))
    }
    
    // 加载本地 HTML
    if let htmlPath = Bundle.main.path(forResource: "index", ofType: "html"),
       let htmlUrl = URL(string: "file://\(htmlPath)?\(urlComponents.query ?? "")") {
      webView.load(URLRequest(url: htmlUrl))
    }
    
    return webView
  }
}
```

### 4. 创建桥接文件

```swift
// ios/App/App/AIChatSDKBridge.swift
import Foundation

/// Objective-C 桥接，方便 OC 项目调用
@objc public class AIChatSDKBridge: NSObject {
  
  @objc public static func createChatViewController(
    accessToken: String,
    apiUrl: String,
    customVariables: [String: Any]
  ) -> UIViewController {
    
    // 转换参数类型
    let variables = customVariables as? [String: String] ?? [:]
    
    return AIChatSDK.createChatViewController(
      accessToken: accessToken,
      apiUrl: apiUrl,
      customVariables: variables
    )
  }
  
  @objc public static func createChatView(
    frame: CGRect,
    accessToken: String,
    apiUrl: String,
    customVariables: [String: Any]
  ) -> UIView {
    
    let variables = customVariables as? [String: String] ?? [:]
    
    return AIChatSDK.createChatView(
      frame: frame,
      accessToken: accessToken,
      apiUrl: apiUrl,
      customVariables: variables
    )
  }
}
```

### 5. 添加语音识别插件

```swift
// ios/App/App/Plugins/VoicePlugin.swift
import Foundation
import Capacitor
import Speech

@objc(VoicePlugin)
public class VoicePlugin: CAPPlugin {
  
  private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "zh-CN"))
  private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
  private var recognitionTask: SFSpeechRecognitionTask?
  private let audioEngine = AVAudioEngine()
  
  @objc func startRecognition(_ call: CAPPluginCall) {
    // 请求权限
    SFSpeechRecognizer.requestAuthorization { authStatus in
      OperationQueue.main.addOperation {
        switch authStatus {
        case .authorized:
          do {
            try self.startRecording()
            call.resolve()
          } catch {
            call.reject("启动录音失败: \(error.localizedDescription)")
          }
        case .denied:
          call.reject("语音识别权限被拒绝")
        case .restricted:
          call.reject("语音识别受限")
        case .notDetermined:
          call.reject("语音识别权限未确定")
        @unknown default:
          call.reject("未知错误")
        }
      }
    }
  }
  
  @objc func stopRecognition(_ call: CAPPluginCall) {
    audioEngine.stop()
    recognitionRequest?.endAudio()
    call.resolve()
  }
  
  private func startRecording() throws {
    recognitionTask?.cancel()
    recognitionTask = nil
    
    let audioSession = AVAudioSession.sharedInstance()
    try audioSession.setCategory(.record, mode: .measurement, options: .duckOthers)
    try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
    
    recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
    guard let recognitionRequest = recognitionRequest else { return }
    
    recognitionRequest.shouldReportPartialResults = true
    
    recognitionTask = speechRecognizer?.recognitionTask(with: recognitionRequest) { result, error in
      if let result = result {
        let transcription = result.bestTranscription.formattedString
        self.notifyListeners("onSpeechResults", data: ["text": transcription])
        
        if result.isFinal {
          self.notifyListeners("onSpeechFinal", data: ["text": transcription])
        }
      }
      
      if error != nil {
        self.notifyListeners("onSpeechError", data: ["error": error?.localizedDescription ?? ""])
      }
    }
    
    let inputNode = audioEngine.inputNode
    let recordingFormat = inputNode.outputFormat(forBus: 0)
    
    inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
      self.recognitionRequest?.append(buffer)
    }
    
    audioEngine.prepare()
    try audioEngine.start()
  }
}
```

### 6. 注册插件

```swift
// ios/App/App/capacitor.config.json
{
  "appId": "com.wojiayun.aichat",
  "appName": "AI Chat SDK",
  "webDir": "dist",
  "plugins": {
    "VoicePlugin": {
      "path": "Plugins/VoicePlugin.swift"
    }
  }
}
```

## iOS 项目集成

### Swift 项目集成

```swift
// AppDelegate.swift
import UIKit
import Capacitor

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
  
  var window: UIWindow?
  
  func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
    
    // 方式 1: 作为独立应用
    window = UIWindow(frame: UIScreen.main.bounds)
    window?.rootViewController = AIChatSDK.createChatViewController(
      accessToken: "your-access-token",
      apiUrl: "https://your-api.com/api",
      customVariables: [
        "empName": "张三",
        "empId": "12345"
      ]
    )
    window?.makeKeyAndVisible()
    
    return true
  }
}

// 方式 2: 嵌入到现有视图
class ChatViewController: UIViewController {
  override func viewDidLoad() {
    super.viewDidLoad()
    
    let chatView = AIChatSDK.createChatView(
      frame: view.bounds,
      accessToken: "your-access-token",
      apiUrl: "https://your-api.com/api",
      customVariables: [
        "empName": "张三",
        "empId": "12345"
      ]
    )
    
    view.addSubview(chatView)
  }
}
```

### Objective-C 项目集成

```objective-c
// ViewController.m
#import <UIKit/UIKit.h>
#import "AIChatSDK-Swift.h"

@interface ViewController ()
@end

@implementation ViewController

- (void)viewDidLoad {
  [super viewDidLoad];
  
  // 方式 1: 创建视图控制器
  UIViewController *chatVC = [AIChatSDKBridge createChatViewControllerWithAccessToken:@"your-token"
                                                                              apiUrl:@"https://your-api.com/api"
                                                                      customVariables:@{
                                                                        @"empName": @"张三",
                                                                        @"empId": @"12345"
                                                                      }];
  [self presentViewController:chatVC animated:YES completion:nil];
  
  // 方式 2: 创建嵌入视图
  UIView *chatView = [AIChatSDKBridge createChatViewWithFrame:self.view.bounds
                                                  accessToken:@"your-token"
                                                      apiUrl:@"https://your-api.com/api"
                                              customVariables:@{
                                                @"empName": @"张三",
                                                @"empId": @"12345"
                                              }];
  [self.view addSubview:chatView];
}

@end
```

## 参数传递

### URL 参数方式

```swift
let accessToken = "your-token"
let empName = "张三"
let empId = "12345"

// 构建参数
let params = [
  "access_token": accessToken,
  "empName": empName,
  "empId": empId
]

// 创建视图
let chatVC = AIChatSDK.createChatViewController(
  accessToken: accessToken,
  customVariables: params
)
```

### JavaScript 桥接方式

```swift
// 在 Swift 中调用 JavaScript
let webView = WKWebView()

// 注入参数
let script = """
  window.chatConfig = {
    accessToken: '\(accessToken)',
    apiUrl: '\(apiUrl)',
    customVariables: {
      empName: '\(empName)',
      empId: '\(empId)'
    }
  };
"""

webView.evaluateJavaScript(script) { result, error in
  if let error = error {
    print("注入配置失败: \(error)")
  }
}
```

```javascript
// 在 Web 端读取配置
const config = window.chatConfig || {
  accessToken: getUrlParam('access_token'),
  apiUrl: getUrlParam('apiUrl') || '/api',
  customVariables: {
    empName: getUrlParam('empName'),
    empId: getUrlParam('empId')
  }
};
```

## 构建

```bash
# 构建 Web 资源
npm run build

# 同步到 iOS
npx cap sync ios

# 打开 Xcode
npx cap open ios

# 在 Xcode 中构建 Archive
# Product -> Archive -> Distribute App
```

## 发布

### CocoaPods

```ruby
# AIChatSDK.podspec
Pod::Spec.new do |s|
  s.name         = "AIChatSDK"
  s.version      = "1.0.0"
  s.summary      = "AI Chat SDK for iOS"
  s.homepage     = "https://github.com/wojiayun/aichat-sdk"
  s.license      = "MIT"
  s.author       = { "wojiayun" => "dev@wojiayun.com" }
  s.platform     = :ios, "12.0"
  s.source       = { :git => "https://github.com/wojiayun/aichat-sdk.git" }
  s.vendored_frameworks = "AIChatSDK.framework"
end
```

```bash
pod trunk push AIChatSDK.podspec
```

## 优势

✅ **快速开发** - 无需重写代码
✅ **跨平台** - 一套代码，iOS/Android 通用
✅ **热更新** - Web 资源可独立更新
✅ **原生集成** - 支持原生插件扩展

## 限制

⚠️ **性能** - WebView 性能不如原生
⚠️ **包体积** - 包含整个 WebView 引擎
⚠️ **离线** - 需要额外处理离线场景

## 适用场景

- ✅ 快速验证 MVP
- ✅ 已有 Web SDK 需要打包
- ✅ 需要跨平台一致性
- ✅ 团队熟悉 Web 开发
