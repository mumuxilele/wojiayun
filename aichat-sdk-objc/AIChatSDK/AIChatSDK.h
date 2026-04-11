//
//  AIChatSDK.h
//  AIChatSDK
//
//  Created by wojiacloud on 2026/04/08.
//

#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>

NS_ASSUME_NONNULL_BEGIN

/**
 * AI Chat SDK 配置类
 */
@interface AIChatConfig : NSObject

/**
 * 访问令牌（必填）
 */
@property (nonatomic, copy) NSString *accessToken;

/**
 * API 地址（可选，默认为 "/api"）
 */
@property (nonatomic, copy, nullable) NSString *apiUrl;

/**
 * 自定义变量（可选）
 * 支持的键：empName, empId, userId, userName, department, role 等
 */
@property (nonatomic, copy, nullable) NSDictionary<NSString *, NSString *> *customVariables;

/**
 * 主题（可选，默认为 light）
 * 可选值：light, dark
 */
@property (nonatomic, copy, nullable) NSString *theme;

/**
 * 是否启用语音输入（可选，默认为 YES）
 */
@property (nonatomic, assign) BOOL enableVoice;

/**
 * 占位符文本（可选）
 */
@property (nonatomic, copy, nullable) NSString *placeholder;

/**
 * 欢迎消息（可选）
 */
@property (nonatomic, copy, nullable) NSString *welcomeMessage;

/**
 * 便捷初始化方法
 */
+ (instancetype)configWithAccessToken:(NSString *)accessToken;

@end

/**
 * AI Chat SDK 代理协议
 */
@protocol AIChatSDKDelegate <NSObject>

@optional

/**
 * 收到新消息
 */
- (void)aiChatDidReceiveMessage:(NSDictionary *)message;

/**
 * 发送消息
 */
- (void)aiChatDidSendMessage:(NSDictionary *)message;

/**
 * 发生错误
 */
- (void)aiChatDidError:(NSError *)error;

/**
 * 语音识别结果
 */
- (void)aiChatVoiceRecognitionResult:(NSString *)text;

@end

/**
 * AI Chat SDK 主类
 */
@interface AIChatSDK : NSObject

/**
 * SDK 版本
 */
+ (NSString *)version;

/**
 * 创建聊天视图控制器
 * @param config SDK 配置
 * @return 聊天视图控制器
 */
+ (UIViewController *)createChatViewControllerWithConfig:(AIChatConfig *)config;

/**
 * 创建聊天视图控制器（便捷方法）
 * @param accessToken 访问令牌
 * @return 聊天视图控制器
 */
+ (UIViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken;

/**
 * 创建聊天视图控制器（完整参数）
 * @param accessToken 访问令牌
 * @param apiUrl API 地址
 * @param customVariables 自定义变量
 * @return 聊天视图控制器
 */
+ (UIViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken
                                                      apiUrl:(nullable NSString *)apiUrl
                                              customVariables:(nullable NSDictionary<NSString *, NSString *> *)customVariables;

/**
 * 创建聊天视图（用于嵌入）
 * @param frame 视图尺寸
 * @param config SDK 配置
 * @return 聊天视图
 */
+ (UIView *)createChatViewWithFrame:(CGRect)frame
                             config:(AIChatConfig *)config;

/**
 * 创建聊天视图（便捷方法）
 * @param frame 视图尺寸
 * @param accessToken 访问令牌
 * @return 聊天视图
 */
+ (UIView *)createChatViewWithFrame:(CGRect)frame
                        accessToken:(NSString *)accessToken;

/**
 * 设置代理
 */
+ (void)setDelegate:(id<AIChatSDKDelegate>)delegate;

/**
 * 设置调试模式
 */
+ (void)setDebugMode:(BOOL)enable;

/**
 * 清理资源
 */
+ (void)cleanup;

@end

NS_ASSUME_NONNULL_END