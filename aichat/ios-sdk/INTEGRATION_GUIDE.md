# AIChatSDK iOS 集成指南

## 目录

1. [环境要求](#环境要求)
2. [SDK 集成](#sdk-集成)
3. [权限配置](#权限配置)
4. [基础使用](#基础使用)
5. [高级功能](#高级功能)

---

## 环境要求

- iOS 11.0+
- Xcode 12.0+
- ARC

---

## SDK 集成

### 步骤 1：添加文件到项目

将以下文件复制到你的 Xcode 项目中：

```
AIChatSDK.h
AIChatSDK.m
AIChatViewController.m
```

### 步骤 2：添加系统框架

在 `Build Phases` -> `Link Binary With Libraries` 中添加以下框架：

- `AVFoundation.framework` - 录音功能
- `Photos.framework` - 相册访问（可选）

### 步骤 3：配置 Info.plist

在 `Info.plist` 中添加以下权限声明：

```xml
<!-- 麦克风权限 -->
<key>NSMicrophoneUsageDescription</key>
<string>需要麦克风权限来使用语音输入功能</string>

<!-- 相册权限 -->
<key>NSPhotoLibraryUsageDescription</key>
<string>需要访问相册来发送图片</string>
```

---

## 权限配置

### 麦克风权限

SDK 会自动请求麦克风权限。你也可以在打开聊天页面前手动请求：

```objc
#import <AVFoundation/AVFoundation.h>

[[AVAudioSession sharedInstance] requestRecordPermission:^(BOOL granted) {
    if (granted) {
        // 已授权，可以打开聊天页面
    }
}];
```

---

## 基础使用

### 最简单的集成方式

```objc
#import "AIChatSDK.h"

- (void)openChat {
    NSString *token = @"your_access_token_here";
    
    // 创建聊天页面
    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:token];
    
    // 设置标题
    chatVC.title = @"AI 助手";
    
    // Push 到聊天页面
    [self.navigationController pushViewController:chatVC animated:YES];
}
```

### 自定义配置

```objc
- (void)openChatWithCustomConfig {
    // 创建自定义配置
    AIChatConfig *config = [[AIChatConfig alloc] init];
    config.baseURL = @"http://47.98.238.209:22314";  // 你的服务器地址
    config.title = @"智能客服";
    config.themeColor = [UIColor systemBlueColor];
    config.welcomeTitle = @"你好！👋";
    config.welcomeMessage = @"有什么可以帮助您的？";
    config.placeholderText = @"请输入问题...";
    config.enableVoiceInput = YES;   // 启用语音
    config.enableImageUpload = YES;  // 启用图片
    
    // 使用自定义配置创建
    NSString *token = @"your_access_token_here";
    AIChatViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:token 
                                                                               config:config];
    
    [self.navigationController pushViewController:chatVC animated:YES];
}
```

---

## 高级功能

### 监听聊天事件

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
    // 用户点击返回
}

- (void)chatViewController:(AIChatViewController *)viewController didSendMessage:(NSString *)content {
    // 用户发送消息
}

- (void)chatViewController:(AIChatViewController *)viewController didReceiveReply:(NSString *)content {
    // 收到助手回复
}

- (void)chatViewController:(AIChatViewController *)viewController didEncounterError:(NSError *)error {
    // 发生错误
}
```

### 全局配置

在 AppDelegate 中设置全局默认配置：

```objc
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {
    
    // 设置全局默认配置
    AIChatConfig *config = [AIChatConfig defaultConfig];
    config.baseURL = @"http://your-server:22314";
    config.themeColor = [UIColor redColor];
    [AIChatSDK setDefaultConfig:config];
    
    return YES;
}
```

### 直接使用服务层

如果需要在聊天页面外调用 API：

```objc
// 创建服务实例
AIChatService *service = [[AIChatService alloc] initWithBaseURL:@"http://server:22314" 
                                                    accessToken:@"TOKEN"];

// 加载用户信息
[service loadUserInfoWithCompletion:^(BOOL success, NSDictionary *userInfo, NSError *error) {
    if (success) {
        NSLog(@"用户: %@", userInfo[@"userName"]);
    }
}];

// 发送消息
[service sendMessage:@"你好" completion:^(BOOL success, AIChatMessage *message, NSError *error) {
    if (success) {
        NSLog(@"回复: %@", message.content);
    }
}];
```

---

## API 说明

### AIChatSDK

| 方法 | 说明 |
|------|------|
| `+version` | 获取 SDK 版本 |
| `+createChatViewControllerWithAccessToken:` | 使用默认配置创建聊天页面 |
| `+createChatViewControllerWithAccessToken:config:` | 使用自定义配置创建聊天页面 |
| `+setDefaultConfig:` | 设置全局默认配置 |
| `+defaultConfig` | 获取当前默认配置 |

### AIChatConfig

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| baseURL | NSString | http://47.98.238.209:22314 | 服务器地址 |
| title | NSString | AI智能助手 | 页面标题 |
| themeColor | UIColor | #30c2b3 | 主题色 |
| welcomeTitle | NSString | 👋 AI智能助手 | 欢迎标题 |
| welcomeMessage | NSString | 我是您的智能助手... | 欢迎消息 |
| placeholderText | NSString | 输入您的问题... | 占位符 |
| enableVoiceInput | BOOL | YES | 启用语音输入 |
| enableImageUpload | BOOL | YES | 启用图片上传 |

### AIChatViewController

| 方法 | 说明 |
|------|------|
| `-scrollToBottom` | 滚动到消息列表底部 |
| `-addSystemMessage:` | 添加系统消息 |
| `-clearChatHistory` | 清空聊天记录 |

---

## 常见问题

### Q: 语音输入没有反应？

A: 请检查：
1. 是否在 Info.plist 中添加了 `NSMicrophoneUsageDescription`
2. 用户是否授权了麦克风权限
3. 真机测试（模拟器不支持录音）

### Q: 图片上传失败？

A: 请检查：
1. 是否在 Info.plist 中添加了 `NSPhotoLibraryUsageDescription`
2. 网络连接是否正常
3. 服务器上传接口是否正常

### Q: 收不到消息回复？

A: 请检查：
1. access_token 是否有效
2. 服务器地址是否正确
3. 网络连接是否正常
4. 查看 Xcode 控制台日志

---

## 完整示例代码

参考 `Example/` 目录下的完整示例项目。

```objc
// 最简示例
#import "AIChatSDK.h"

- (void)viewDidLoad {
    [super viewDidLoad];
    
    UIButton *btn = [UIButton buttonWithType:UIButtonTypeSystem];
    [btn setTitle:@"打开聊天" forState:UIControlStateNormal];
    [btn addTarget:self action:@selector(openChat) forControlEvents:UIControlEventTouchUpInside];
    btn.frame = CGRectMake(100, 200, 120, 44);
    [self.view addSubview:btn];
}

- (void)openChat {
    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"YOUR_TOKEN"];
    chatVC.title = @"AI 助手";
    [self.navigationController pushViewController:chatVC animated:YES];
}
```

---

## 联系支持

如有问题，请联系技术支持。
