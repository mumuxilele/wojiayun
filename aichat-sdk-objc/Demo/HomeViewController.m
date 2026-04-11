//
//  HomeViewController.m
//  AIChatSDKDemo
//
//  Created by wojiacloud on 2026/04/08.
//

#import "HomeViewController.h"
#import <AIChatSDK/AIChatSDK.h>

@interface HomeViewController () <AIChatSDKDelegate>

@property (nonatomic, strong) UILabel *titleLabel;
@property (nonatomic, strong) UIButton *basicButton;
@property (nonatomic, strong) UIButton *customButton;
@property (nonatomic, strong) UIButton *asyncButton;
@property (nonatomic, strong) UITextView *logTextView;

@end

@implementation HomeViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    
    self.title = @"AI Chat SDK Demo";
    self.view.backgroundColor = [UIColor whiteColor];
    
    [self setupUI];
    [self setupSDK];
}

- (void)setupUI {
    // 标题
    self.titleLabel = [[UILabel alloc] init];
    self.titleLabel.text = @"AI Chat SDK 集成示例";
    self.titleLabel.font = [UIFont boldSystemFontOfSize:24];
    self.titleLabel.textAlignment = NSTextAlignmentCenter;
    self.titleLabel.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:self.titleLabel];
    
    // 基础集成按钮
    self.basicButton = [UIButton buttonWithType:UIButtonTypeSystem];
    [self.basicButton setTitle:@"基础集成 (Push)" forState:UIControlStateNormal];
    self.basicButton.titleLabel.font = [UIFont systemFontOfSize:16];
    self.basicButton.backgroundColor = [UIColor systemBlueColor];
    [self.basicButton setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    self.basicButton.layer.cornerRadius = 8;
    self.basicButton.translatesAutoresizingMaskIntoConstraints = NO;
    [self.basicButton addTarget:self action:@selector(basicIntegration) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:self.basicButton];
    
    // 自定义参数按钮
    self.customButton = [UIButton buttonWithType:UIButtonTypeSystem];
    [self.customButton setTitle:@"自定义参数集成" forState:UIControlStateNormal];
    self.customButton.titleLabel.font = [UIFont systemFontOfSize:16];
    self.customButton.backgroundColor = [UIColor systemGreenColor];
    [self.customButton setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    self.customButton.layer.cornerRadius = 8;
    self.customButton.translatesAutoresizingMaskIntoConstraints = NO;
    [self.customButton addTarget:self action:@selector(customIntegration) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:self.customButton];
    
    // 异步获取 Token 按钮
    self.asyncButton = [UIButton buttonWithType:UIButtonTypeSystem];
    [self.asyncButton setTitle:@"异步获取 Token" forState:UIControlStateNormal];
    self.asyncButton.titleLabel.font = [UIFont systemFontOfSize:16];
    self.asyncButton.backgroundColor = [UIColor systemOrangeColor];
    [self.asyncButton setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    self.asyncButton.layer.cornerRadius = 8;
    self.asyncButton.translatesAutoresizingMaskIntoConstraints = NO;
    [self.asyncButton addTarget:self action:@selector(asyncIntegration) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:self.asyncButton];
    
    // 日志文本框
    self.logTextView = [[UITextView alloc] init];
    self.logTextView.font = [UIFont systemFontOfSize:12];
    self.logTextView.backgroundColor = [UIColor colorWithRed:245/255.0 green:245/255.0 blue:245/255.0 alpha:1.0];
    self.logTextView.layer.cornerRadius = 8;
    self.logTextView.layer.borderWidth = 1;
    self.logTextView.layer.borderColor = [UIColor colorWithRed:200/255.0 green:200/255.0 blue:200/255.0 alpha:1.0].CGColor;
    self.logTextView.editable = NO;
    self.logTextView.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:self.logTextView];
    
    // 布局约束
    [NSLayoutConstraint activateConstraints:@[
        // 标题
        [self.titleLabel.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor constant:40],
        [self.titleLabel.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor constant:20],
        [self.titleLabel.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor constant:-20],
        
        // 基础集成按钮
        [self.basicButton.topAnchor constraintEqualToAnchor:self.titleLabel.bottomAnchor constant:40],
        [self.basicButton.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor constant:20],
        [self.basicButton.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor constant:-20],
        [self.basicButton.heightAnchor constraintEqualToConstant:50],
        
        // 自定义参数按钮
        [self.customButton.topAnchor constraintEqualToAnchor:self.basicButton.bottomAnchor constant:20],
        [self.customButton.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor constant:20],
        [self.customButton.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor constant:-20],
        [self.customButton.heightAnchor constraintEqualToConstant:50],
        
        // 异步获取 Token 按钮
        [self.asyncButton.topAnchor constraintEqualToAnchor:self.customButton.bottomAnchor constant:20],
        [self.asyncButton.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor constant:20],
        [self.asyncButton.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor constant:-20],
        [self.asyncButton.heightAnchor constraintEqualToConstant:50],
        
        // 日志文本框
        [self.logTextView.topAnchor constraintEqualToAnchor:self.asyncButton.bottomAnchor constant:30],
        [self.logTextView.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor constant:20],
        [self.logTextView.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor constant:-20],
        [self.logTextView.bottomAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.bottomAnchor constant:-20]
    ]];
}

- (void)setupSDK {
    // 设置 SDK 代理
    [AIChatSDK setDelegate:self];
    
    // 启用调试模式
    [AIChatSDK setDebugMode:YES];
    
    [self addLog:@"SDK 版本: %@", [AIChatSDK version]];
    [self addLog:@"SDK 初始化完成"];
}

#pragma mark - 集成方式

/**
 * 方式 1: 基础集成 - 使用 Push
 */
- (void)basicIntegration {
    [self addLog:@"\n=== 基础集成 (Push) ==="];
    
    // 创建聊天视图控制器
    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"demo-access-token-12345"];
    
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
    
    [self addLog:@"Push 成功"];
}

/**
 * 方式 2: 自定义参数集成
 */
- (void)customIntegration {
    [self addLog:@"\n=== 自定义参数集成 ==="];
    
    // 准备自定义参数
    NSDictionary *customVariables = @{
        @"empName": @"张三",
        @"empId": @"12345",
        @"userId": @"user123",
        @"department": @"技术部",
        @"role": @"admin"
    };
    
    [self addLog:@"自定义参数: %@", customVariables];
    
    // 创建聊天视图控制器
    UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:@"demo-access-token-12345"
                                                                          apiUrl:@"https://api.wojiayun.com/api"
                                                                  customVariables:customVariables];
    
    // 设置标题
    chatVC.title = @"AI 助手";
    
    // Push
    [self.navigationController pushViewController:chatVC animated:YES];
    
    [self addLog:@"Push 成功（自定义参数）"];
}

/**
 * 方式 3: 异步获取 Token 后集成
 */
- (void)asyncIntegration {
    [self addLog:@"\n=== 异步获取 Token ==="];
    
    // 显示加载提示
    UIAlertController *loadingAlert = [UIAlertController alertControllerWithTitle:nil
                                                                         message:@"正在获取访问令牌..."
                                                                  preferredStyle:UIAlertControllerStyleAlert];
    [self presentViewController:loadingAlert animated:YES completion:nil];
    
    // 模拟异步获取 Token
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(1.5 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        [loadingAlert dismissViewControllerAnimated:YES completion:^{
            // 模拟获取到的 Token
            NSString *token = [NSString stringWithFormat:@"async-token-%ld", (long)[[NSDate date] timeIntervalSince1970]];
            
            [self addLog:@"获取 Token 成功: %@", token];
            
            // 创建聊天视图控制器
            UIViewController *chatVC = [AIChatSDK createChatViewControllerWithAccessToken:token];
            chatVC.title = @"AI 助手";
            
            // Push
            [self.navigationController pushViewController:chatVC animated:YES];
            
            [self addLog:@"Push 成功（异步）"];
        }];
    });
}

#pragma mark - AIChatSDKDelegate

- (void)aiChatDidReceiveMessage:(NSDictionary *)message {
    [self addLog:@"收到消息: %@", message];
}

- (void)aiChatDidSendMessage:(NSDictionary *)message {
    [self addLog:@"发送消息: %@", message];
}

- (void)aiChatDidError:(NSError *)error {
    [self addLog:@"发生错误: %@", error.localizedDescription];
}

- (void)aiChatVoiceRecognitionResult:(NSString *)text {
    [self addLog:@"语音识别: %@", text];
}

#pragma mark - Helper Methods

- (void)addLog:(NSString *)format, ... {
    va_list args;
    va_start(args, format);
    NSString *message = [[NSString alloc] initWithFormat:format arguments:args];
    va_end(args);
    
    NSDateFormatter *formatter = [[NSDateFormatter alloc] init];
    formatter.dateFormat = @"HH:mm:ss";
    NSString *timestamp = [formatter stringFromDate:[NSDate date]];
    
    NSString *log = [NSString stringWithFormat:@"[%@] %@", timestamp, message];
    
    dispatch_async(dispatch_get_main_queue(), ^{
        self.logTextView.text = [self.logTextView.text stringByAppendingString:log];
        self.logTextView.text = [self.logTextView.text stringByAppendingString:@"\n"];
        
        // 滚动到底部
        NSRange range = NSMakeRange(self.logTextView.text.length - 1, 1);
        [self.logTextView scrollRangeToVisible:range];
    });
}

@end
