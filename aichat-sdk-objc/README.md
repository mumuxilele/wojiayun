# AI Chat SDK - Objective-C 版本

完整的 Objective-C SDK 包，支持 iOS 11.0+

## 📦 项目结构

```
aichat-sdk-objc/
├── AIChatSDK/              # SDK 源码
│   ├── AIChatSDK.h         # 头文件
│   ├── AIChatSDK.m         # 实现文件
│   └── index.html          # Web 资源
├── Demo/                   # 示例项目
│   ├── AppDelegate.h
│   ├── AppDelegate.m
│   ├── HomeViewController.h
│   ├── HomeViewController.m
│   └── Info.plist
├── AIChatSDK.podspec       # CocoaPods 配置
├── Podfile                 # 依赖配置
└── README.md               # 文档
```

## 🚀 快速开始

### 方式一：CocoaPods 集成（推荐）

#### 1. 创建 Podfile

```ruby
platform :ios, '11.0'
use_frameworks!

target 'YourApp' do
  pod 'AIChatSDK', :path => '../aichat-sdk-objc'
end
```

#### 2. 安装依赖

```bash
pod install
```

#### 3. 导入头文件

```objective-c
#import <AIChatSDK/AIChatSDK.h>
```

### 方式二：手动集成

#### 1. 添加源文件

将 `AIChatSDK/` 文件夹拖入项目

#### 2. 添加依赖框架

- UIKit.framework
- WebKit.framework
- Speech.framework
- AVFoundation.framework

#### 3. 配置 Info.plist

```xml
<!-- 麦克风权限 -->
<key>NSMicrophoneUsageDescription</key>
<string>需要麦克风权限进行语音输入</string>

<!-- 语音识别权限 -->
<key>NSSpeechRecognitionUsageDescription</key>
<string>需要语音识别权限进行语音转文字</string>
```

## 📱 使用示例

### 示例 1：基础集成（Push）

```objective-c
#import "HomeViewController.h"
#import <AIChatSDK/AIChatSDK.h>

@implementation HomeViewController

- (void)openChat {
    // 创建聊天视图控制器
    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"your-access-token"];
    
    // 设置标题
    chatVC.title = @"AI 助手";
    
    // 设置返回按钮
    UIBarButtonItem *backItem = [[UIBarButtonItem alloc] initWithTitle:@"返回"
                                                                 style:UIBarButtonItemStylePlain
                                                                target:nil
                                                                action:nil];
    chatVC.navigationItem.backBarButtonItem = backItem;
    
    // Push 到聊天页面
    [self.navigationController pushViewController:chatVC animated:YES];
}

@end
```

### 示例 2：自定义参数集成

```objective-c
- (void)openChatWithCustomParams {
    // 准备自定义参数
    NSDictionary *customVariables = @{
        @"empName": @"张三",
        @"empId": @"12345",
        @"userId": @"user123",
        @"department": @"技术部"
    };
    
    // 创建聊天视图控制器
    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"your-token"
                                                                          apiUrl:@"https://api.wojiayun.com/api"
                                                                  customVariables:customVariables];
    
    chatVC.title = @"AI 助手";
    
    // Push
    [self.navigationController pushViewController:chatVC animated:YES];
}
```

### 示例 3：异步获取 Token 后集成

```objective-c
- (void)openChatAsync {
    // 显示加载提示
    UIAlertController *loadingAlert = [UIAlertController alertControllerWithTitle:nil
                                                                         message:@"加载中..."
                                                                  preferredStyle:UIAlertControllerStyleAlert];
    [self presentViewController:loadingAlert animated:YES completion:nil];
    
    // 异步获取 Token
    [self fetchAccessToken:^(NSString *token) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [loadingAlert dismissViewControllerAnimated:YES completion:^{
                if (token) {
                    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:token];
                    chatVC.title = @"AI 助手";
                    [self.navigationController pushViewController:chatVC animated:YES];
                } else {
                    [self showError:@"获取访问令牌失败"];
                }
            }];
        });
    }];
}

- (void)fetchAccessToken:(void (^)(NSString *))completion {
    NSURL *url = [NSURL URLWithString:@"https://your-api.com/auth/token"];
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    request.HTTPMethod = @"POST";
    [request setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];
    
    NSDictionary *body = @{@"userId": @"12345"};
    request.HTTPBody = [NSJSONSerialization dataWithJSONObject:body options:0 error:nil];
    
    NSURLSessionDataTask *task = [NSURLSession.sharedSession dataTaskWithRequest:request
        completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
            if (data) {
                NSDictionary *json = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
                NSString *token = json[@"access_token"];
                completion(token);
            } else {
                completion(nil);
            }
        }];
    
    [task resume];
}
```

### 示例 4：Modal 方式展示

```objective-c
- (void)showChatModal {
    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"your-token"];
    chatVC.title = @"AI 助手";
    
    // 添加关闭按钮
    UIBarButtonItem *closeItem = [[UIBarButtonItem alloc] initWithTitle:@"关闭"
                                                                 style:UIBarButtonItemStylePlain
                                                                target:self
                                                                action:@selector(dismissChat)];
    chatVC.navigationItem.rightBarButtonItem = closeItem;
    
    // 包装在 NavigationController 中
    UINavigationController *navVC = [[UINavigationController alloc] initWithRootViewController:chatVC];
    navVC.modalPresentationStyle = UIModalPresentationFullScreen;
    
    [self presentViewController:navVC animated:YES completion:nil];
}

- (void)dismissChat {
    [self dismissViewControllerAnimated:YES completion:nil];
}
```

### 示例 5：TabBar 集成

```objective-c
// TabBarController.m
#import <AIChatSDK/AIChatSDK.h>

@implementation TabBarController

- (void)viewDidLoad {
    [super viewDidLoad];
    
    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"your-token"];
    chatVC.title = @"AI 助手";
    chatVC.tabBarItem = [[UITabBarItem alloc] initWithTitle:@"AI助手"
                                                       image:[UIImage systemImageNamed:@"message"]
                                                         tag:0];
    
    self.viewControllers = @[chatVC];
}

@end
```

## 🎯 完整 API

### AIChatConfig

```objective-c
// 创建配置
AIChatConfig *config = [[AIChatConfig alloc] init];
config.accessToken = @"your-token";
config.apiUrl = @"https://api.wojiayun.com/api";
config.customVariables = @{
    @"empName": @"张三",
    @"empId": @"12345"
};
config.theme = @"light";
config.enableVoice = YES;
config.placeholder = @"输入消息...";
config.welcomeMessage = @"你好！我是 AI 助手";
```

### AIChatSDK

```objective-c
// SDK 版本
NSString *version = [AIChatSDK version];

// 创建视图控制器
UIViewController *vc = [AIChatSDK createChatViewControllerWithConfig:config];
UIViewController *vc = [AIChatSDK createChatViewControllerWithAccessToken:@"token"];
UIViewController *vc = [AIChatSDK createChatViewControllerWithAccessToken:@"token"
                                                                  apiUrl:@"url"
                                                          customVariables:@{...}];

// 创建视图
UIView *view = [AIChatSDK createChatViewWithFrame:frame config:config];
UIView *view = [AIChatSDK createChatViewWithFrame:frame accessToken:@"token"];

// 设置代理
[AIChatSDK setDelegate:self];

// 启用调试
[AIChatSDK setDebugMode:YES];

// 清理资源
[AIChatSDK cleanup];
```

### AIChatSDKDelegate

```objective-c
@interface HomeViewController () <AIChatSDKDelegate>
@end

@implementation HomeViewController

- (void)aiChatDidReceiveMessage:(NSDictionary *)message {
    NSLog(@"收到消息: %@", message);
}

- (void)aiChatDidSendMessage:(NSDictionary *)message {
    NSLog(@"发送消息: %@", message);
}

- (void)aiChatDidError:(NSError *)error {
    NSLog(@"发生错误: %@", error);
}

- (void)aiChatVoiceRecognitionResult:(NSString *)text {
    NSLog(@"语音识别: %@", text);
}

@end
```

## 📝 参数说明

### 必需参数

| 参数 | 类型 | 说明 |
|------|------|------|
| accessToken | NSString | 访问令牌 |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| apiUrl | NSString | "/api" | API 地址 |
| customVariables | NSDictionary | nil | 自定义变量 |
| theme | NSString | "light" | 主题 |
| enableVoice | BOOL | YES | 启用语音 |
| placeholder | NSString | nil | 占位符 |
| welcomeMessage | NSString | nil | 欢迎消息 |

### customVariables 支持的键

```objective-c
@{
    @"empName": @"张三",      // 员工姓名
    @"empId": @"12345",      // 员工 ID
    @"userId": @"user123",   // 用户 ID
    @"userName": @"zhangsan", // 用户名
    @"department": @"技术部", // 部门
    @"role": @"admin"        // 角色
}
```

## 🎨 自定义样式

### 自定义导航栏

```objective-c
UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"token"];
chatVC.title = @"AI 助手";

// iOS 13+
if (@available(iOS 13.0, *)) {
    UINavigationBarAppearance *appearance = [[UINavigationBarAppearance alloc] init];
    [appearance configureWithOpaqueBackground];
    appearance.backgroundColor = [UIColor systemPurpleColor];
    appearance.titleTextAttributes = @{NSForegroundColorAttributeName: [UIColor whiteColor]};
    
    self.navigationController.navigationBar.standardAppearance = appearance;
    self.navigationController.navigationBar.scrollEdgeAppearance = appearance;
}

[self.navigationController pushViewController:chatVC animated:YES];
```

### 自定义返回按钮

```objective-c
UIBarButtonItem *backItem = [[UIBarButtonItem alloc] initWithTitle:@"返回"
                                                             style:UIBarButtonItemStylePlain
                                                            target:nil
                                                            action:nil];
chatVC.navigationItem.backBarButtonItem = backItem;
```

## 🔧 构建 SDK

### 构建 Framework

```bash
# 1. 打开项目
open AIChatSDK.xcodeproj

# 2. 选择 Generic iOS Device

# 3. Product -> Archive

# 4. 导出 Framework
```

### 发布到 CocoaPods

```bash
# 1. 注册 trunk
pod trunk register your@email.com 'Your Name'

# 2. 发布
pod trunk push AIChatSDK.podspec
```

## 🐛 常见问题

### Q1: Push 后导航栏不显示？

**A**: 确保在 AppDelegate 中正确设置了 NavigationController

```objective-c
UINavigationController *navVC = [[UINavigationController alloc] initWithRootViewController:homeVC];
self.window.rootViewController = navVC;
```

### Q2: 语音识别不工作？

**A**: 检查权限配置

```xml
<key>NSMicrophoneUsageDescription</key>
<string>需要麦克风权限进行语音输入</string>

<key>NSSpeechRecognitionUsageDescription</key>
<string>需要语音识别权限进行语音转文字</string>
```

### Q3: 如何处理登录状态？

```objective-c
- (void)openChat {
    NSString *token = [[NSUserDefaults standardUserDefaults] stringForKey:@"access_token"];
    
    if (!token) {
        // 未登录，跳转到登录页
        LoginViewController *loginVC = [[LoginViewController alloc] init];
        [self.navigationController pushViewController:loginVC animated:YES];
        return;
    }
    
    // 已登录，显示聊天
    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:token];
    [self.navigationController pushViewController:chatVC animated:YES];
}
```

### Q4: 如何调试？

```objective-c
// 启用调试模式
[AIChatSDK setDebugMode:YES];

// 设置代理监听事件
[AIChatSDK setDelegate:self];

// 实现代理方法
- (void)aiChatDidError:(NSError *)error {
    NSLog(@"错误: %@", error);
}
```

## 📚 完整示例项目

查看 `Demo/` 文件夹获取完整的示例项目

### 运行示例

```bash
# 1. 安装依赖
cd Demo
pod install

# 2. 打开项目
open AIChatSDKDemo.xcworkspace

# 3. 运行
# Command + R
```

## 📞 技术支持

- 📧 Email: dev@wojiayun.com
- 📖 文档: https://docs.wojiayun.com/aichat-sdk
- 🐛 Issues: https://github.com/wojiayun/aichat-sdk/issues

## 📄 License

MIT License

---

**开始使用 AI Chat SDK，为您的 iOS 应用添加智能对话功能！** 🚀
