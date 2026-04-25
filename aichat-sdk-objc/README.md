# AI Chat SDK - 纯原生 iOS Objective-C

纯原生 UIKit 实现，不使用 WebView，1:1 还原 `index-v2.html` 所有功能。

## 项目结构

```
aichat-sdk-objc/
├── AIChatSDK.h/m            # SDK 入口
├── AIChatViewController.h/m  # 主控制器
├── AIChatMessage.h/m        # 消息模型
├── AIChatMessageCell.h/m    # 消息气泡 Cell
└── Demo/                    # 示例
```

## 文件说明

| 文件 | 大小 | 说明 |
|------|------|------|
| `AIChatSDK.h/m` | 2.5KB | SDK 入口工厂类 |
| `AIChatViewController.h/m` | 65KB | 主控制器，完整 UI |
| `AIChatMessage.h/m` | 3KB | 消息模型 |
| `AIChatMessageCell.h/m` | 43KB | 气泡 Cell，含 Markdown 渲染、Widget |

## 功能对照

| H5 功能 | iOS 实现 |
|---------|---------|
| 用户/AI 消息气泡 | ✅ `AIChatMessageCell` |
| Markdown 渲染 | ✅ `AIMarkdownParser`（纯代码） |
| 代码块 + 复制按钮 | ✅ `AICodeBlockView` |
| 选项卡片 | ✅ `AIOptionCardsView` |
| 图片上传预览 | ✅ `AIImageThumbView` |
| 图片全屏预览 | ✅ `AIImagePreviewController` |
| 打字指示器（3点动画） | ✅ `AITypingIndicatorView` |
| SSE 流式响应 | ✅ `NSURLSession` 分块接收 |
| 语音/文字模式切换 | ✅ `switchToTextMode` / `switchToVoiceMode` |
| 长按录音 + 上滑取消 | ✅ 手势识别 |
| Widget 渲染 | ✅ `renderWidget:` HTML 片段 |
| 错误提示 Banner | ✅ `showError:` |
| 键盘自动上推 | ✅ `UIKeyboardWillShowNotification` |

## 外部调用方式

```objc
#import "AIChatSDK.h"

// 方式一：推荐，最简洁
UIViewController *vc = [AIChatSDK createChatViewControllerWithAccessToken:@"your_token"];
[self.navigationController pushViewController:vc animated:YES];

// 方式二：完整参数
UIViewController *vc = [AIChatSDK createChatViewControllerWithAccessToken:@"your_token"
                                                                  apiUrl:@"/api"
                                                               pageTitle:@"AI助手"
                                                         customVariables:@{@"empName": @"张三"}];
[self.navigationController pushViewController:vc animated:YES];

// 方式三：配置对象
AIChatConfig *config = [AIChatConfig configWithAccessToken:@"your_token"];
config.apiUrl = @"/api";
config.pageTitle = @"AI助手";
config.enableVoice = YES;
config.customVariables = @{@"empName": @"张三", @"empId": @"001"};
UIViewController *vc = [AIChatSDK createChatViewControllerWithConfig:config];
[self.navigationController pushViewController:vc animated:YES];
```

## 代理回调

```objc
#import "AIChatSDK.h"

@interface YourViewController () <AIChatViewControllerDelegate>
@end

@implementation YourViewController

- (void)openChat {
    UIViewController *vc = [AIChatSDK createChatViewControllerWithAccessToken:@"your_token"];
    ((AIChatViewController *)vc).delegate = self;
    [self.navigationController pushViewController:vc animated:YES];
}

- (void)aiChatDidSendMessage:(NSString *)content {
    NSLog(@"发送: %@", content);
}

- (void)aiChatDidReceiveMessage:(NSString *)content {
    NSLog(@"收到: %@", content);
}

- (void)aiChatDidError:(NSString *)errorMessage {
    NSLog(@"错误: %@", errorMessage);
}

- (void)aiChatDidClose {
    NSLog(@"关闭了");
}

@end
```

## 权限配置

`Info.plist` 添加：

```xml
<key>NSMicrophoneUsageDescription</key>
<string>需要使用麦克风进行语音输入</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>需要访问相册选择图片</string>
<key>NSSpeechRecognitionUsageDescription</key>
<string>需要使用语音识别功能</string>
```

## API 接口要求

服务端需实现：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/userinfo` | GET | 返回 `{success: true, data: {id, empName, ...}}` |
| `/api/chat` | POST | SSE 流式响应，事件类型：`reply`, `error` |
| `/api/upload-image` | POST | 返回 `{success: true, data: [{id, url}]}` |
| `/api/speech-to-text` | POST | 返回 `{success: true, text: "识别文本"}` |

## 编译

1. 将 `AIChatSDK/` 目录添加到 Xcode 项目
2. 添加系统框架：`Foundation`, `UIKit`, `AVFoundation`, `Speech`
3. 编译即可
