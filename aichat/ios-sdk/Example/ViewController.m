//
//  ViewController.m
//  AIChatDemo
//
//  示例代码：展示如何使用 AIChatSDK
//

#import "ViewController.h"
#import "AIChatSDK.h"

@interface ViewController () <AIChatViewControllerDelegate>
@property (nonatomic, strong) UIButton *openChatButton;
@end

@implementation ViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    
    self.view.backgroundColor = [UIColor whiteColor];
    self.title = @"AI Chat Demo";
    
    // 创建打开聊天按钮
    self.openChatButton = [UIButton buttonWithType:UIButtonTypeSystem];
    self.openChatButton.frame = CGRectMake(50, 200, self.view.bounds.size.width - 100, 50);
    self.openChatButton.backgroundColor = [UIColor colorWithRed:48.0/255.0 green:194.0/255.0 blue:179.0/255.0 alpha:1.0];
    [self.openChatButton setTitle:@"打开 AI 聊天" forState:UIControlStateNormal];
    [self.openChatButton setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    self.openChatButton.layer.cornerRadius = 25;
    [self.openChatButton addTarget:self action:@selector(openChatTapped) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:self.openChatButton];
    
    // 配置全局默认配置（可选）
    [self setupGlobalConfig];
}

#pragma mark - 配置方法

/// 设置全局默认配置
- (void)setupGlobalConfig {
    AIChatConfig *config = [AIChatConfig defaultConfig];
    config.baseURL = @"http://47.98.238.209:22314";  // V2 服务器地址
    config.themeColor = [UIColor colorWithRed:48.0/255.0 green:194.0/255.0 blue:179.0/255.0 alpha:1.0];
    config.welcomeTitle = @"👋 AI智能助手";
    config.welcomeMessage = @"我是您的智能助手，可以帮助您解答各种问题";
    config.placeholderText = @"输入您的问题...";
    config.enableVoiceInput = YES;
    config.enableImageUpload = YES;
    
    [AIChatSDK setDefaultConfig:config];
}

#pragma mark - 按钮点击

- (void)openChatTapped {
    // 替换为你的 access_token
    NSString *accessToken = @"36f609b39cde210481120512abf8a39b32e2b3d39b0c02d560ea724eb0738f75";
    
    // ========== 方式1：使用默认配置（最简单）==========
    // UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:accessToken];
    
    // ========== 方式2：使用自定义配置 ==========
    AIChatConfig *customConfig = [[AIChatConfig alloc] init];
    customConfig.baseURL = @"http://47.98.238.209:22314";
    customConfig.title = @"AI 智能助手";
    customConfig.themeColor = [UIColor colorWithRed:48.0/255.0 green:194.0/255.0 blue:179.0/255.0 alpha:1.0];
    customConfig.welcomeTitle = @"👋 欢迎使用";
    customConfig.welcomeMessage = @"我是您的专属AI助手，请问有什么可以帮您？";
    customConfig.placeholderText = @"请输入您的问题...";
    customConfig.enableVoiceInput = YES;
    customConfig.enableImageUpload = YES;
    
    AIChatViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:accessToken 
                                                                               config:customConfig];
    
    // 设置代理（可选）
    chatVC.delegate = self;
    
    // 设置返回按钮
    UIBarButtonItem *backItem = [[UIBarButtonItem alloc] initWithTitle:@"返回"
                                                                  style:UIBarButtonItemStylePlain
                                                                 target:nil
                                                                 action:nil];
    chatVC.navigationItem.backBarButtonItem = backItem;
    
    // Push 到聊天页面
    [self.navigationController pushViewController:chatVC animated:YES];
}

#pragma mark - AIChatViewControllerDelegate

/// 用户点击返回按钮
- (void)chatViewControllerDidTapBack:(AIChatViewController *)viewController {
    NSLog(@"[Demo] 用户点击返回");
}

/// 用户发送消息
- (void)chatViewController:(AIChatViewController *)viewController didSendMessage:(NSString *)content {
    NSLog(@"[Demo] 用户发送: %@", content);
}

/// 收到助手回复
- (void)chatViewController:(AIChatViewController *)viewController didReceiveReply:(NSString *)content {
    NSLog(@"[Demo] 收到回复: %@", content);
}

/// 发生错误
- (void)chatViewController:(AIChatViewController *)viewController didEncounterError:(NSError *)error {
    NSLog(@"[Demo] 错误: %@", error.localizedDescription);
    
    // 显示错误提示
    UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"提示"
                                                                   message:error.localizedDescription
                                                            preferredStyle:UIAlertControllerStyleAlert];
    [alert addAction:[UIAlertAction actionWithTitle:@"确定" style:UIAlertActionStyleDefault handler:nil]];
    [self presentViewController:alert animated:YES completion:nil];
}

@end
