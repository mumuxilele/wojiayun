# AI Chat SDK - Capacitor 版本

将 H5 AI 聊天页面编译为 iOS/Android 原生 SDK。

## 项目结构

```
aichat-sdk-capacitor/
├── package.json              # 项目配置
├── vite.config.js            # Vite 构建配置
├── index.html                # 入口 HTML
├── src/
│   ├── main.js               # 入口 JS
│   ├── App.vue               # 根组件
│   ├── index.js              # SDK 导出
│   ├── components/
│   │   └── AiChat.vue        # 主聊天组件 (29KB)
│   └── utils/
│       ├── markdown.js       # Markdown 解析
│       └── widget.js         # Widget 渲染
└── ios/                      # iOS 原生 SDK
    ├── AiChatSDK.h           # SDK 头文件
    ├── AiChatSDK.m           # SDK 实现
    ├── AiChatViewController.h
    └── AiChatViewController.m
```

## 快速开始

```bash
# 安装依赖
npm install

# 开发调试
npm run dev

# 构建 H5
npm run build

# 添加 iOS 平台
npm run cap:add:ios

# 添加 Android 平台
npm run cap:add:android

# 同步到原生平台
npm run cap:sync

# 编译 iOS SDK
npm run build:ios

# 编译 Android SDK
npm run build:android
```

## iOS 原生集成 (Objective-C)

### 1. 导入 SDK

将 `ios/` 目录下的文件添加到 Xcode 项目。

### 2. 初始化

```objc
#import "AiChatSDK.h"

// 方式一：简化调用
UIViewController *chatVC = [AiChatSDK createChatViewControllerWithAccessToken:@"your_token"];
[self.navigationController pushViewController:chatVC animated:YES];

// 方式二：完整配置
AiChatConfig *config = [AiChatConfig configWithAccessToken:@"your_token"
                                                    apiUrl:@"/api"
                                                 pageTitle:@"AI助手"];
config.customVariables = @{@"empName": @"张三"};
UIViewController *chatVC = [AiChatSDK createChatViewControllerWithConfig:config];
[self.navigationController pushViewController:chatVC animated:YES];
```

### 3. 代理回调

```objc
@interface MyViewController () <AiChatDelegate>
@end

@implementation MyViewController

- (void)aiChatDidSendMessage:(NSString *)content {
    NSLog(@"发送消息: %@", content);
}

- (void)aiChatDidReceiveMessage:(NSString *)content {
    NSLog(@"收到回复: %@", content);
}

- (void)aiChatDidError:(NSString *)error {
    NSLog(@"发生错误: %@", error);
}

- (void)aiChatDidClose {
    NSLog(@"SDK 已关闭");
}

@end
```

### 4. 主动调用

```objc
// 发送消息
[chatVC sendMessage:@"你好"];

// 清空消息
[chatVC clearMessages];

// 获取消息列表
NSArray *messages = [chatVC getMessages];
```

## Android 原生集成 (Kotlin/Java)

### 1. 导入 SDK

将编译后的 AAR 文件添加到 Android 项目。

### 2. 初始化 (Kotlin)

```kotlin
import com.wojiayun.aichat.AiChatSDK
import com.wojiayun.aichat.AiChatConfig

// 简化调用
val intent = AiChatSDK.createIntent(this, "your_token")
startActivity(intent)

// 完整配置
val config = AiChatConfig().apply {
    accessToken = "your_token"
    apiUrl = "/api"
    pageTitle = "AI助手"
    customVariables = mapOf("empName" to "张三")
}
val intent = AiChatSDK.createIntent(this, config)
startActivity(intent)
```

## API 接口

服务端需实现：

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/userinfo | GET | 获取用户信息 |
| /api/chat | POST | 发送消息（SSE） |
| /api/upload-image | POST | 上传图片 |
| /api/speech-to-text | POST | 语音转文字 |

## 权限配置

### iOS (Info.plist)

```xml
<key>NSMicrophoneUsageDescription</key>
<string>需要使用麦克风进行语音输入</string>
<key>NSCameraUsageDescription</key>
<string>需要使用摄像头拍照</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>需要访问相册选择图片</key>
```

### Android (AndroidManifest.xml)

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
<uses-permission android:name="android.permission.INTERNET"/>
```
