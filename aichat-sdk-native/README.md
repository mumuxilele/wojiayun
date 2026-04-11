# AI Chat iOS SDK - React Native 版本

## 项目结构

```
aichat-sdk-native/
├── src/
│   ├── components/
│   │   ├── ChatView.tsx           # 聊天视图组件
│   │   ├── MessageList.tsx        # 消息列表
│   │   ├── InputBar.tsx           # 输入栏
│   │   └── VoiceButton.tsx        # 语音按钮
│   ├── services/
│   │   ├── ChatService.ts         # 聊天服务
│   │   └── VoiceService.ts        # 语音服务
│   ├── hooks/
│   │   └── useChat.ts             # 聊天 Hook
│   ├── types/
│   │   └── index.ts               # 类型定义
│   └── index.ts                   # 导出入口
├── ios/                           # iOS 原生代码
│   └── AIChatSDK.xcodeproj
├── android/                       # Android 原生代码
├── package.json
└── README.md
```

## 安装依赖

```bash
# 创建 React Native 库
npx create-react-native-library aichat-sdk-native

# 安装依赖
cd aichat-sdk-native
npm install

# 安装额外依赖
npm install @react-native-voice/voice
npm install react-native-markdown-display
npm install react-native-gesture-handler
npm install react-native-reanimated
```

## 核心代码实现

### 1. ChatView 组件

```typescript
// src/components/ChatView.tsx
import React from 'react';
import { View, StyleSheet, Platform } from 'react-native';
import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { useChat } from '../hooks/useChat';

export interface ChatViewProps {
  accessToken: string;
  apiUrl?: string;
  customVariables?: Record<string, string>;
  theme?: 'light' | 'dark';
  onMessage?: (message: any) => void;
  onError?: (error: Error) => void;
}

export const ChatView: React.FC<ChatViewProps> = ({
  accessToken,
  apiUrl = '/api',
  customVariables = {},
  theme = 'light',
  onMessage,
  onError,
}) => {
  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    startRecording,
    stopRecording,
  } = useChat({
    accessToken,
    apiUrl,
    customVariables,
  });

  return (
    <View style={[styles.container, theme === 'dark' && styles.darkContainer]}>
      <MessageList 
        messages={messages} 
        isStreaming={isStreaming}
      />
      <InputBar
        onSend={sendMessage}
        onStartRecording={startRecording}
        onStopRecording={stopRecording}
        disabled={isStreaming}
        placeholder="输入消息或长按语音按钮..."
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  darkContainer: {
    backgroundColor: '#1a1a1a',
  },
});
```

### 2. VoiceService（iOS 原生语音识别）

```typescript
// src/services/VoiceService.ts
import { Platform, NativeModules, NativeEventEmitter } from 'react-native';

const { VoiceModule } = NativeModules;
const voiceEmitter = new NativeEventEmitter(VoiceModule);

export class VoiceService {
  private static instance: VoiceService;
  private isRecording = false;

  static getInstance(): VoiceService {
    if (!VoiceService.instance) {
      VoiceService.instance = new VoiceService();
    }
    return VoiceService.instance;
  }

  async startRecognition(): Promise<void> {
    if (Platform.OS === 'ios') {
      try {
        await VoiceModule.startRecognition('zh-CN');
        this.isRecording = true;
      } catch (error) {
        console.error('启动语音识别失败:', error);
        throw error;
      }
    }
  }

  async stopRecognition(): Promise<string> {
    if (Platform.OS === 'ios' && this.isRecording) {
      try {
        const result = await VoiceModule.stopRecognition();
        this.isRecording = false;
        return result;
      } catch (error) {
        console.error('停止语音识别失败:', error);
        throw error;
      }
    }
    return '';
  }

  addListener(callback: (text: string) => void) {
    return voiceEmitter.addListener('onSpeechResults', (event) => {
      callback(event.value);
    });
  }
}
```

### 3. iOS 原生模块（Objective-C）

```objective-c
// ios/VoiceModule.m
#import <React/RCTBridgeModule.h>
#import <React/RCTEventEmitter.h>
#import <Speech/Speech.h>

@interface VoiceModule : RCTEventEmitter <RCTBridgeModule>
@property (nonatomic, strong) SFSpeechRecognizer *recognizer;
@property (nonatomic, strong) SFSpeechAudioBufferRecognitionRequest *request;
@property (nonatomic, strong) AVAudioEngine *audioEngine;
@end

@implementation VoiceModule

RCT_EXPORT_MODULE();

- (instancetype)init {
  if (self = [super init]) {
    _recognizer = [[SFSpeechRecognizer alloc] initWithLocale:[[NSLocale alloc] initWithLocaleIdentifier:@"zh-CN"]];
    _audioEngine = [[AVAudioEngine alloc] init];
  }
  return self;
}

RCT_EXPORT_METHOD(startRecognition:(NSString *)locale) {
  // 请求权限
  [SFSpeechRecognizer requestAuthorization:^(SFSpeechRecognizerAuthorizationStatus status) {
    if (status == SFSpeechRecognizerAuthorizationStatusAuthorized) {
      [self startRecording];
    }
  }];
}

RCT_EXPORT_METHOD(stopRecognition:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject) {
  [_audioEngine stop];
  [_request endAudio];
  resolve(@"");
}

- (void)startRecording {
  _request = [[SFSpeechAudioBufferRecognitionRequest alloc] init];
  AVAudioNode *inputNode = _audioEngine.inputNode;
  
  [_request addKeyword:@"开始"];
  
  [_recognizer recognitionTaskWithRequest:_request resultHandler:^(SFSpeechRecognitionResult *result, NSError *error) {
    if (result) {
      NSString *transcription = result.bestTranscription.formattedString;
      [self sendEventWithName:@"onSpeechResults" body:@{@"value": transcription}];
    }
  }];
  
  AVAudioFormat *format = [inputNode outputFormatForBus:0];
  [inputNode installTapOnBus:0 bufferSize:1024 format:format block:^(AVAudioBuffer *buffer, AVAudioTime *when) {
    [_request appendAudioPCMBuffer:buffer];
  }];
  
  [_audioEngine prepare];
  [_audioEngine startAndReturnError:nil];
}

- (NSArray<NSString *> *)supportedEvents {
  return @[@"onSpeechResults", @"onSpeechError"];
}

@end
```

## 打包 iOS SDK

### 1. 配置 podspec

```ruby
# AIChatSDK.podspec
Pod::Spec.new do |s|
  s.name         = "AIChatSDK"
  s.version      = "1.0.0"
  s.summary      = "AI Chat SDK for iOS"
  s.description  = "A React Native AI Chat SDK"
  s.homepage     = "https://github.com/wojiayun/aichat-sdk"
  s.license      = "MIT"
  s.author       = { "wojiayun" => "dev@wojiayun.com" }
  s.platform     = :ios, "11.0"
  s.source       = { :git => "https://github.com/wojiayun/aichat-sdk.git", :tag => "#{s.version}" }
  
  s.source_files = "ios/**/*.{h,m,mm,swift}"
  s.dependency "React"
  s.dependency "RCT-Folly"
end
```

### 2. 构建命令

```bash
# 构建 iOS 库
cd aichat-sdk-native
npm run build

# 生成 Xcode 项目
npx pod-install

# 打包成 .framework
xcodebuild -workspace AIChatSDK.xcworkspace \
  -scheme AIChatSDK \
  -sdk iphoneos \
  -configuration Release \
  -archivePath build/AIChatSDK.xcarchive \
  archive

# 导出 .framework
xcodebuild -exportArchive \
  -archivePath build/AIChatSDK.xcarchive \
  -exportPath build/AIChatSDK.framework
```

## iOS 项目集成

### 1. CocoaPods 集成

```ruby
# Podfile
platform :ios, '11.0'
use_frameworks!

target 'YourApp' do
  pod 'AIChatSDK', :path => '../aichat-sdk-native'
end
```

```bash
pod install
```

### 2. 原生 iOS 项目中使用

```swift
// AppDelegate.swift
import AIChatSDK
import React

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {
  var window: UIWindow?
  var bridge: RCTBridge?
  
  func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
    // 初始化 React Native Bridge
    bridge = RCTBridge(delegate: self, launchOptions: launchOptions)
    
    // 创建 AI Chat 视图
    let chatView = AIChatSDK.createChatView(
      accessToken: "your-access-token",
      apiUrl: "https://your-api.com/api",
      customVariables: [
        "empName": "张三",
        "empId": "12345"
      ]
    )
    
    window = UIWindow(frame: UIScreen.main.bounds)
    window?.rootViewController = UIViewController()
    window?.rootViewController?.view = chatView
    window?.makeKeyAndVisible()
    
    return true
  }
}

// 扩展 RCTBridgeDelegate
extension AppDelegate: RCTBridgeDelegate {
  func sourceURL(for bridge: RCTBridge!) -> URL! {
    return Bundle.main.url(forResource: "main", withExtension: "jsbundle")
  }
}
```

### 3. Swift 传参示例

```swift
import AIChatSDK

class ChatViewController: UIViewController {
  override func viewDidLoad() {
    super.viewDidLoad()
    
    // 创建配置
    let config = ChatConfig(
      accessToken: "your-access-token",
      apiUrl: "https://your-api.com/api",
      customVariables: [
        "empName": "张三",
        "empId": "12345",
        "userId": "user123"
      ],
      theme: .light,
      enableVoice: true
    )
    
    // 创建聊天视图
    let chatView = AIChatSDK.createChatView(config: config)
    
    // 添加到视图层级
    chatView.frame = view.bounds
    chatView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
    view.addSubview(chatView)
    
    // 监听事件
    AIChatSDK.onMessage { message in
      print("收到消息: \(message)")
    }
    
    AIChatSDK.onError { error in
      print("发生错误: \(error)")
    }
  }
}

// 配置结构体
struct ChatConfig {
  let accessToken: String
  let apiUrl: String
  let customVariables: [String: String]
  let theme: Theme
  let enableVoice: Bool
  
  enum Theme {
    case light
    case dark
  }
}
```

### 4. Objective-C 项目中使用

```objective-c
// ViewController.m
#import <AIChatSDK/AIChatSDK.h>

@interface ViewController ()
@property (nonatomic, strong) UIView *chatView;
@end

@implementation ViewController

- (void)viewDidLoad {
  [super viewDidLoad];
  
  // 创建配置
  NSDictionary *config = @{
    @"accessToken": @"your-access-token",
    @"apiUrl": @"https://your-api.com/api",
    @"customVariables": @{
      @"empName": @"张三",
      @"empId": @"12345"
    },
    @"theme": @"light",
    @"enableVoice": @YES
  };
  
  // 创建聊天视图
  self.chatView = [AIChatSDK createChatViewWithConfig:config];
  self.chatView.frame = self.view.bounds;
  self.chatView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
  [self.view addSubview:self.chatView];
  
  // 监听消息事件
  [AIChatSDK onMessage:^(NSDictionary *message) {
    NSLog(@"收到消息: %@", message);
  }];
  
  // 监听错误事件
  [AIChatSDK onError:^(NSError *error) {
    NSLog(@"发生错误: %@", error);
  }];
}

@end
```

## 参数说明

### 必需参数

| 参数 | 类型 | 说明 |
|------|------|------|
| accessToken | String | 访问令牌（必填） |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| apiUrl | String | '/api' | API 地址 |
| customVariables | Dictionary | {} | 自定义变量 |
| theme | String | 'light' | 主题（light/dark） |
| enableVoice | Bool | true | 是否启用语音 |

### customVariables 参数

```swift
let customVariables = [
  "access_token": "your-token",      // 访问令牌
  "empName": "张三",                  // 员工姓名
  "empId": "12345",                  // 员工 ID
  "userId": "user123",               // 用户 ID
  "userName": "zhangsan",            // 用户名
  "department": "技术部"              // 部门
]
```

## 权限配置

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

## 测试

```swift
// 单元测试
import XCTest
@testable import AIChatSDK

class AIChatSDKTests: XCTestCase {
  func testChatViewCreation() {
    let config = ChatConfig(
      accessToken: "test-token",
      apiUrl: "https://test.com/api",
      customVariables: [:],
      theme: .light,
      enableVoice: true
    )
    
    let chatView = AIChatSDK.createChatView(config: config)
    XCTAssertNotNil(chatView)
  }
}
```

## 发布

```bash
# 发布到 npm
npm publish

# 发布到 CocoaPods
pod trunk push AIChatSDK.podspec
```

## 支持

- iOS 11.0+
- Swift 5.0+
- React Native 0.60+
