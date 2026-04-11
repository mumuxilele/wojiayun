# AIChatSDK for iOS

AIChat iOS SDK - 与 V2 版本后端 API 完全对接

## 功能特性

- ✅ 文本聊天（支持流式响应）
- ✅ 图片上传和发送
- ✅ 语音输入（长按录音）
- ✅ Widget 卡片渲染
- ✅ 选项卡片交互
- ✅ 完全自定义 UI 主题

## 安装

### 手动集成

将以下文件添加到你的 Xcode 项目中：

```
AIChatSDK.h
AIChatSDK.m
AIChatViewController.m
```

### 依赖框架

在 `Build Phases` -> `Link Binary With Libraries` 中添加：

- AVFoundation.framework
- Speech.framework (可选，用于语音识别)

## 快速开始

### 1. 基础使用

```objc
#import "AIChatSDK.h"

// 使用默认配置创建聊天页面
UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"YOUR_ACCESS_TOKEN"];

// 设置标题
chatVC.title = @"AI 助手";

// Push 到聊天页面
[self.navigationController pushViewController:chatVC animated:YES];
```

### 2. 自定义配置

```objc
// 创建自定义配置
AIChatConfig *config = [[AIChatConfig alloc] init];
config.baseURL = @"http://your-server:22314";  // 服务器地址
config.title = @"智能客服";                      // 页面标题
config.themeColor = [UIColor systemBlueColor];  // 主题色
config.welcomeTitle = @"你好！";                // 欢迎标题
config.welcomeMessage = @"有什么可以帮助您的？"; // 欢迎消息
config.placeholderText = @"请输入问题...";      // 输入框占位符
config.enableVoiceInput = YES;                  // 启用语音输入
config.enableImageUpload = YES;                 // 启用图片上传

// 使用自定义配置创建
UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"YOUR_ACCESS_TOKEN" 
                                                                        config:config];
[self.navigationController pushViewController:chatVC animated:YES];
```

### 3. 全局配置

```objc
// 设置全局默认配置
AIChatConfig *globalConfig = [AIChatConfig defaultConfig];
globalConfig.themeColor = [UIColor redColor];
[AIChatSDK setDefaultConfig:globalConfig];

// 之后创建的聊天页面都会使用这个配置
UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"TOKEN"];
```

## 高级用法

### 代理回调

```objc
@interface MyViewController () <AIChatViewControllerDelegate>
@end

- (void)openChat {
    AIChatViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"TOKEN"];
    chatVC.delegate = self;
    [self.navigationController pushViewController:chatVC animated:YES];
}

#pragma mark - AIChatViewControllerDelegate

- (void)chatViewControllerDidTapBack:(AIChatViewController *)viewController {
    NSLog(@"用户点击返回");
}

- (void)chatViewController:(AIChatViewController *)viewController didSendMessage:(NSString *)content {
    NSLog(@"用户发送消息: %@", content);
}

- (void)chatViewController:(AIChatViewController *)viewController didReceiveReply:(NSString *)content {
    NSLog(@"收到回复: %@", content);
}

- (void)chatViewController:(AIChatViewController *)viewController didEncounterError:(NSError *)error {
    NSLog(@"发生错误: %@", error.localizedDescription);
}
```

### 直接使用服务层

```objc
// 创建服务实例
AIChatService *service = [[AIChatService alloc] initWithBaseURL:@"http://server:22314" 
                                                    accessToken:@"YOUR_TOKEN"];
service.delegate = self;

// 加载用户信息
[service loadUserInfoWithCompletion:^(BOOL success, NSDictionary *userInfo, NSError *error) {
    if (success) {
        NSLog(@"用户信息: %@", userInfo);
    }
}];

// 发送消息
[service sendMessage:@"你好" completion:^(BOOL success, AIChatMessage *message, NSError *error) {
    if (success) {
        NSLog(@"收到回复: %@", message.content);
    }
}];

// 上传图片
UIImage *image = [UIImage imageNamed:@"photo"];
[service uploadImage:image completion:^(BOOL success, NSString *imageURL, NSError *error) {
    if (success) {
        NSLog(@"图片URL: %@", imageURL);
    }
}];
```

## API 对接说明

本 SDK 与 V2 版本后端完全对接，使用以下 API：

| API | 方法 | 说明 |
|-----|------|------|
| `/api/userinfo` | GET | 获取用户信息 |
| `/api/chat` | POST | 发送消息（SSE 流式响应） |
| `/api/upload-image` | POST | 上传图片 |
| `/api/speech-to-text` | POST | 语音识别 |

### SSE 事件处理

SDK 自动处理以下 SSE 事件：

- `reply` - 文本回复（包含 Widget 卡片）
- `reference` - 参考来源
- `token_stat` - Token 统计
- `thought` - 思考过程
- `error` - 错误信息

## 数据结构

### AIChatMessage

```objc
@interface AIChatMessage : NSObject
@property (nonatomic, copy) NSString *messageId;        // 消息ID
@property (nonatomic, assign) AIChatMessageRole role;   // user/assistant
@property (nonatomic, assign) AIChatMessageType type;   // text/image/widget
@property (nonatomic, copy) NSString *content;          // 文本内容
@property (nonatomic, copy) NSString *imageURL;         // 图片URL
@property (nonatomic, copy) NSDictionary *widgetData;   // Widget数据
@property (nonatomic, copy) NSArray<NSString *> *optionCards; // 选项卡片
@property (nonatomic, strong) NSDate *timestamp;        // 时间戳
@end
```

## 注意事项

1. **麦克风权限**：首次使用语音功能时需要用户授权
2. **网络请求**：所有网络请求都是异步的，在主线程回调
3. **内存管理**：SDK 使用 ARC，无需手动管理内存
4. **线程安全**：所有 UI 操作都在主线程执行

## 版本历史

### 1.0.0
- 初始版本
- 支持文本聊天、图片上传、语音输入
- 对接 V2 版本 API

## License

MIT License
