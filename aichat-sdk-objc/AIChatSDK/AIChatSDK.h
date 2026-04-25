//
//  AIChatSDK.h
//  AIChatSDK
//
//  AI 智能助手聊天 SDK - Objective-C 接口
//  使用 self.navigationController pushViewController: 调用
//

#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN

#pragma mark - 配置类

@interface AIChatConfig : NSObject

/// 访问令牌（必填）
@property (nonatomic, copy) NSString *accessToken;

/// API 地址（可选，默认 "/api"）
@property (nonatomic, copy, nullable) NSString *apiUrl;

/// 页面标题（可选，默认 "AI智能助手"）
@property (nonatomic, copy, nullable) NSString *pageTitle;

/// 自定义变量（可选）
@property (nonatomic, copy, nullable) NSDictionary<NSString *, NSString *> *customVariables;

/// 是否启用语音输入（可选，默认 YES）
@property (nonatomic, assign) BOOL enableVoice;

/// 便捷初始化
+ (instancetype)configWithAccessToken:(NSString *)accessToken;

/// 完整初始化
+ (instancetype)configWithAccessToken:(NSString *)accessToken apiUrl:(nullable NSString *)apiUrl;

@end

#pragma mark - 代理协议

@protocol AIChatViewControllerDelegate <NSObject>
@optional
- (void)aiChatDidSendMessage:(NSString *)content;
- (void)aiChatDidReceiveMessage:(NSString *)content;
- (void)aiChatDidError:(NSString *)errorMessage;
- (void)aiChatDidClose;
@end

#pragma mark - SDK 主类

@interface AIChatSDK : NSObject

/// SDK 版本
+ (NSString *)version;

/// 创建聊天控制器（推荐）
/// @param accessToken 访问令牌
/// @return 可直接 push 到 navigationController
+ (UIViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken;

/// 创建聊天控制器（完整参数）
/// @param accessToken 访问令牌
/// @param apiUrl API 地址
/// @param pageTitle 页面标题
/// @param customVariables 自定义变量
/// @return 聊天控制器
+ (UIViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken
                                                       apiUrl:(nullable NSString *)apiUrl
                                                    pageTitle:(nullable NSString *)pageTitle
                                              customVariables:(nullable NSDictionary<NSString *, NSString *> *)customVariables;

/// 使用配置对象创建
+ (UIViewController *)createChatViewControllerWithConfig:(AIChatConfig *)config;

/// 设置日志级别（0=关闭, 1=错误, 2=警告, 3=信息, 4=调试）
+ (void)setLogLevel:(NSInteger)level;

@end

NS_ASSUME_NONNULL_END
