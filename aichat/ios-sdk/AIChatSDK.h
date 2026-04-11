//
//  AIChatSDK.h
//  AIChatSDK
//
//  iOS SDK for AI Chat V2
//  与 aichat V2 版本 API 对接
//

#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN

#pragma mark - AIChatConfig

@interface AIChatConfig : NSObject

/// 服务器基础URL (默认: http://47.98.238.209:22314)
@property (nonatomic, copy) NSString *baseURL;

/// 页面标题
@property (nonatomic, copy) NSString *title;

/// 是否启用语音输入 (默认: YES)
@property (nonatomic, assign) BOOL enableVoiceInput;

/// 是否启用图片上传 (默认: YES)
@property (nonatomic, assign) BOOL enableImageUpload;

/// 主题色 (默认: #30c2b3)
@property (nonatomic, strong) UIColor *themeColor;

/// 导航栏背景色
@property (nonatomic, strong) UIColor *navigationBarColor;

/// 导航栏文字颜色
@property (nonatomic, strong) UIColor *navigationBarTitleColor;

/// 欢迎消息标题
@property (nonatomic, copy) NSString *welcomeTitle;

/// 欢迎消息内容
@property (nonatomic, copy) NSString *welcomeMessage;

/// 占位符文字
@property (nonatomic, copy) NSString *placeholderText;

/// 初始化默认配置
+ (instancetype)defaultConfig;

@end


#pragma mark - AIChatMessage

typedef NS_ENUM(NSInteger, AIChatMessageRole) {
    AIChatMessageRoleUser,
    AIChatMessageRoleAssistant
};

typedef NS_ENUM(NSInteger, AIChatMessageType) {
    AIChatMessageTypeText,
    AIChatMessageTypeImage,
    AIChatMessageTypeWidget,
    AIChatMessageTypeTyping
};

@interface AIChatMessage : NSObject

@property (nonatomic, copy) NSString *messageId;
@property (nonatomic, assign) AIChatMessageRole role;
@property (nonatomic, assign) AIChatMessageType type;
@property (nonatomic, copy, nullable) NSString *content;
@property (nonatomic, copy, nullable) NSString *imageURL;
@property (nonatomic, copy, nullable) NSDictionary *widgetData;
@property (nonatomic, copy, nullable) NSArray<NSString *> *optionCards;
@property (nonatomic, strong) NSDate *timestamp;

- (instancetype)initWithRole:(AIChatMessageRole)role 
                        type:(AIChatMessageType)type 
                     content:(nullable NSString *)content;

@end


#pragma mark - AIChatService

@class AIChatService;

@protocol AIChatServiceDelegate <NSObject>

@optional
/// 收到新的消息内容（流式更新）
- (void)chatService:(AIChatService *)service didReceiveStreamContent:(NSString *)content forMessage:(AIChatMessage *)message;

/// 消息接收完成
- (void)chatService:(AIChatService *)service didCompleteMessage:(AIChatMessage *)message;

/// 收到错误
- (void)chatService:(AIChatService *)service didEncounterError:(NSError *)error;

/// 用户信息加载成功
- (void)chatService:(AIChatService *)service didLoadUserInfo:(NSDictionary *)userInfo;

@end

@interface AIChatService : NSObject

@property (nonatomic, weak) id<AIChatServiceDelegate> delegate;
@property (nonatomic, copy, readonly) NSString *accessToken;
@property (nonatomic, copy, readonly, nullable) NSDictionary *userInfo;
@property (nonatomic, copy, readonly, nullable) NSString *visitorId;
@property (nonatomic, copy, readonly, nullable) NSString *sessionId;

/// 初始化服务
- (instancetype)initWithBaseURL:(NSString *)baseURL accessToken:(NSString *)accessToken;

/// 加载用户信息
- (void)loadUserInfoWithCompletion:(void (^)(BOOL success, NSDictionary * _Nullable userInfo, NSError * _Nullable error))completion;

/// 发送文本消息（流式响应）
- (void)sendMessage:(NSString *)content completion:(void (^)(BOOL success, AIChatMessage * _Nullable message, NSError * _Nullable error))completion;

/// 发送带图片的消息
- (void)sendMessage:(NSString *)content imageURLs:(NSArray<NSString *> *)imageURLs completion:(void (^)(BOOL success, AIChatMessage * _Nullable message, NSError * _Nullable error))completion;

/// 上传图片
- (void)uploadImage:(UIImage *)image completion:(void (^)(BOOL success, NSString * _Nullable imageURL, NSError * _Nullable error))completion;

/// 语音识别
- (void)recognizeSpeechFromAudioData:(NSData *)audioData completion:(void (^)(BOOL success, NSString * _Nullable text, NSError * _Nullable error))completion;

/// 取消当前请求
- (void)cancelCurrentRequest;

@end


#pragma mark - AIChatViewController

@class AIChatViewController;

@protocol AIChatViewControllerDelegate <NSObject>

@optional
/// 用户点击返回按钮
- (void)chatViewControllerDidTapBack:(AIChatViewController *)viewController;

/// 用户发送消息
- (void)chatViewController:(AIChatViewController *)viewController didSendMessage:(NSString *)content;

/// 收到助手回复
- (void)chatViewController:(AIChatViewController *)viewController didReceiveReply:(NSString *)content;

/// 发生错误
- (void)chatViewController:(AIChatViewController *)viewController didEncounterError:(NSError *)error;

@end

@interface AIChatViewController : UIViewController

@property (nonatomic, weak) id<AIChatViewControllerDelegate> delegate;
@property (nonatomic, strong, readonly) AIChatService *chatService;
@property (nonatomic, strong, readonly) AIChatConfig *config;

/// 使用配置初始化
- (instancetype)initWithConfig:(AIChatConfig *)config accessToken:(NSString *)accessToken;

/// 使用默认配置初始化
- (instancetype)initWithAccessToken:(NSString *)accessToken;

/// 滚动到底部
- (void)scrollToBottom;

/// 添加系统消息
- (void)addSystemMessage:(NSString *)content;

/// 清空聊天记录
- (void)clearChatHistory;

@end


#pragma mark - AIChatSDK

@interface AIChatSDK : NSObject

/// SDK 版本号
+ (NSString *)version;

/// 创建聊天视图控制器（使用默认配置）
+ (AIChatViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken;

/// 创建聊天视图控制器（使用自定义配置）
+ (AIChatViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken config:(AIChatConfig *)config;

/// 配置全局默认配置
+ (void)setDefaultConfig:(AIChatConfig *)config;

/// 获取当前全局默认配置
+ (AIChatConfig *)defaultConfig;

@end

NS_ASSUME_NONNULL_END
