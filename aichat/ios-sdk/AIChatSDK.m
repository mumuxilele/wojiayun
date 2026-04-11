//
//  AIChatSDK.m
//  AIChatSDK
//

#import "AIChatSDK.h"
#import <AVFoundation/AVFoundation.h>

#pragma mark - AIChatConfig Implementation

@implementation AIChatConfig

+ (instancetype)defaultConfig {
    AIChatConfig *config = [[AIChatConfig alloc] init];
    config.baseURL = @"http://47.98.238.209:22314";
    config.title = @"AI智能助手";
    config.enableVoiceInput = YES;
    config.enableImageUpload = YES;
    config.themeColor = [UIColor colorWithRed:48.0/255.0 green:194.0/255.0 blue:179.0/255.0 alpha:1.0];
    config.navigationBarColor = [UIColor whiteColor];
    config.navigationBarTitleColor = [UIColor blackColor];
    config.welcomeTitle = @"👋 AI智能助手";
    config.welcomeMessage = @"我是您的智能助手，可以帮助您解答各种问题";
    config.placeholderText = @"输入您的问题...";
    return config;
}

@end


#pragma mark - AIChatMessage Implementation

@implementation AIChatMessage

- (instancetype)initWithRole:(AIChatMessageRole)role type:(AIChatMessageType)type content:(nullable NSString *)content {
    self = [super init];
    if (self) {
        _messageId = [[NSUUID UUID] UUIDString];
        _role = role;
        _type = type;
        _content = content;
        _timestamp = [NSDate date];
    }
    return self;
}

@end


#pragma mark - AIChatService Implementation

@interface AIChatService ()
@property (nonatomic, copy, readwrite) NSString *accessToken;
@property (nonatomic, copy, readwrite) NSString *baseURL;
@property (nonatomic, copy, readwrite, nullable) NSDictionary *userInfo;
@property (nonatomic, copy, readwrite, nullable) NSString *visitorId;
@property (nonatomic, copy, readwrite, nullable) NSString *sessionId;
@property (nonatomic, strong) NSURLSession *session;
@property (nonatomic, strong) NSURLSessionDataTask *currentTask;
@end

@implementation AIChatService

- (instancetype)initWithBaseURL:(NSString *)baseURL accessToken:(NSString *)accessToken {
    self = [super init];
    if (self) {
        _baseURL = baseURL;
        _accessToken = accessToken;
        _sessionId = [self generateUUID];
        
        NSURLSessionConfiguration *config = [NSURLSessionConfiguration defaultSessionConfiguration];
        config.timeoutIntervalForRequest = 60.0;
        config.timeoutIntervalForResource = 300.0;
        _session = [NSURLSession sessionWithConfiguration:config];
    }
    return self;
}

- (NSString *)generateUUID {
    return [[NSUUID UUID] UUIDString];
}

- (void)loadUserInfoWithCompletion:(void (^)(BOOL success, NSDictionary * _Nullable userInfo, NSError * _Nullable error))completion {
    NSString *urlString = [NSString stringWithFormat:@"%@/api/userinfo?access_token=%@", self.baseURL, self.accessToken];
    NSURL *url = [NSURL URLWithString:urlString];
    
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    [request setHTTPMethod:@"GET"];
    [request setValue:@"application/json" forHTTPHeaderField:@"Accept"];
    
    NSURLSessionDataTask *task = [self.session dataTaskWithRequest:request completionHandler:^(NSData * _Nullable data, NSURLResponse * _Nullable response, NSError * _Nullable error) {
        dispatch_async(dispatch_get_main_queue(), ^{
            if (error) {
                if (completion) completion(NO, nil, error);
                return;
            }
            
            NSError *jsonError;
            NSDictionary *json = [NSJSONSerialization JSONObjectWithData:data options:0 error:&jsonError];
            
            if (jsonError) {
                if (completion) completion(NO, nil, jsonError);
                return;
            }
            
            if ([json[@"success"] boolValue] && json[@"data"]) {
                NSDictionary *userData = json[@"data"][@"data"] ?: json[@"data"];
                self.userInfo = userData;
                self.visitorId = userData[@"id"] ?: userData[@"userId"] ?: userData[@"user_id"] ?: userData[@"empId"];
                
                if ([self.delegate respondsToSelector:@selector(chatService:didLoadUserInfo:)]) {
                    [self.delegate chatService:self didLoadUserInfo:userData];
                }
                
                if (completion) completion(YES, userData, nil);
            } else {
                NSError *apiError = [NSError errorWithDomain:@"AIChatSDK" code:1001 userInfo:@{NSLocalizedDescriptionKey: json[@"error"] ?: @"获取用户信息失败"}];
                if (completion) completion(NO, nil, apiError);
            }
        });
    }];
    
    [task resume];
}

- (void)sendMessage:(NSString *)content completion:(void (^)(BOOL success, AIChatMessage * _Nullable message, NSError * _Nullable error))completion {
    [self sendMessage:content imageURLs:@[] completion:completion];
}

- (void)sendMessage:(NSString *)content imageURLs:(NSArray<NSString *> *)imageURLs completion:(void (^)(BOOL success, AIChatMessage * _Nullable message, NSError * _Nullable error))completion {
    if (!self.visitorId) {
        NSError *error = [NSError errorWithDomain:@"AIChatSDK" code:1002 userInfo:@{NSLocalizedDescriptionKey: @"用户信息未加载"}];
        if (completion) completion(NO, nil, error);
        return;
    }
    
    // 构建完整内容（文字 + 图片markdown）
    NSString *fullContent = content;
    if (imageURLs.count > 0) {
        NSMutableString *markdownImages = [NSMutableString string];
        for (NSString *url in imageURLs) {
            [markdownImages appendFormat:@"![](%@)", url];
        }
        fullContent = [content stringByAppendingString:markdownImages];
    }
    
    NSString *urlString = [NSString stringWithFormat:@"%@/api/chat", self.baseURL];
    NSURL *url = [NSURL URLWithString:urlString];
    
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    [request setHTTPMethod:@"POST"];
    [request setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];
    [request setValue:@"application/json" forHTTPHeaderField:@"Accept"];
    
    NSDictionary *body = @{
        @"session_id": self.sessionId,
        @"visitor_biz_id": self.visitorId,
        @"content": fullContent,
        @"custom_variables": @{
            @"access_token": self.accessToken,
            @"empName": self.userInfo[@"empName"] ?: @"",
            @"userName": self.userInfo[@"userName"] ?: @"",
            @"empId": self.userInfo[@"empId"] ?: @"",
            @"userId": self.userInfo[@"userId"] ?: self.userInfo[@"id"] ?: @""
        }
    };
    
    NSError *jsonError;
    NSData *bodyData = [NSJSONSerialization dataWithJSONObject:body options:0 error:&jsonError];
    if (jsonError) {
        if (completion) completion(NO, nil, jsonError);
        return;
    }
    
    [request setHTTPBody:bodyData];
    
    // 创建助手消息对象
    AIChatMessage *assistantMessage = [[AIChatMessage alloc] initWithRole:AIChatMessageRoleAssistant type:AIChatMessageTypeText content:@""];
    
    NSURLSessionDataTask *task = [self.session dataTaskWithRequest:request completionHandler:^(NSData * _Nullable data, NSURLResponse * _Nullable response, NSError * _Nullable error) {
        dispatch_async(dispatch_get_main_queue(), ^{
            if (error) {
                if ([self.delegate respondsToSelector:@selector(chatService:didEncounterError:)]) {
                    [self.delegate chatService:self didEncounterError:error];
                }
                if (completion) completion(NO, nil, error);
                return;
            }
            
            NSString *responseString = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
            [self parseSSEData:responseString assistantMessage:assistantMessage];
            
            if ([self.delegate respondsToSelector:@selector(chatService:didCompleteMessage:)]) {
                [self.delegate chatService:self didCompleteMessage:assistantMessage];
            }
            
            if (completion) completion(YES, assistantMessage, nil);
        });
    }];
    
    self.currentTask = task;
    [task resume];
}

- (void)parseSSEData:(NSString *)data assistantMessage:(AIChatMessage *)message {
    NSArray *lines = [data componentsSeparatedByString:@"\n"];
    NSMutableString *contentBuilder = [NSMutableString string];
    NSMutableArray *references = [NSMutableArray array];
    
    for (NSString *line in lines) {
        if ([line hasPrefix:@"data:"]) {
            NSString *jsonString = [[line substringFromIndex:5] stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceCharacterSet]];
            if (jsonString.length == 0) continue;
            
            NSError *error;
            NSDictionary *eventData = [NSJSONSerialization JSONObjectWithData:[jsonString dataUsingEncoding:NSUTF8StringEncoding] options:0 error:&error];
            if (error) continue;
            
            NSString *eventType = eventData[@"type"];
            
            if ([eventType isEqualToString:@"reply"]) {
                NSDictionary *payload = eventData[@"payload"];
                if (payload) {
                    // 跳过用户自己的消息
                    if ([payload[@"is_from_self"] boolValue]) continue;
                    
                    NSString *textContent = payload[@"content"];
                    if (textContent) {
                        // 处理 Widget 内容
                        NSDictionary *workFlow = payload[@"work_flow"];
                        if (workFlow && workFlow[@"contents"]) {
                            NSArray *contents = workFlow[@"contents"];
                            for (NSDictionary *contentItem in contents) {
                                if ([contentItem[@"type"] isEqualToString:@"widget"]) {
                                    message.type = AIChatMessageTypeWidget;
                                    message.widgetData = contentItem[@"widget"];
                                }
                            }
                        }
                        
                        // 处理选项卡片
                        NSArray *optionCards = payload[@"option_cards"];
                        if (optionCards.count > 0) {
                            message.optionCards = optionCards;
                        }
                        
                        [contentBuilder appendString:textContent];
                        message.content = [contentBuilder copy];
                        
                        if ([self.delegate respondsToSelector:@selector(chatService:didReceiveStreamContent:forMessage:)]) {
                            [self.delegate chatService:self didReceiveStreamContent:textContent forMessage:message];
                        }
                    }
                }
            } else if ([eventType isEqualToString:@"reference"]) {
                NSDictionary *payload = eventData[@"payload"];
                if (payload[@"references"]) {
                    [references addObjectsFromArray:payload[@"references"]];
                }
            } else if ([eventType isEqualToString:@"error"]) {
                NSDictionary *errorData = eventData[@"error"];
                NSString *errorMessage = errorData[@"message"] ?: @"未知错误";
                NSError *error = [NSError errorWithDomain:@"AIChatSDK" code:1003 userInfo:@{NSLocalizedDescriptionKey: errorMessage}];
                if ([self.delegate respondsToSelector:@selector(chatService:didEncounterError:)]) {
                    [self.delegate chatService:self didEncounterError:error];
                }
            }
        }
    }
}

- (void)uploadImage:(UIImage *)image completion:(void (^)(BOOL success, NSString * _Nullable imageURL, NSError * _Nullable error))completion {
    NSString *urlString = [NSString stringWithFormat:@"%@/api/upload-image", self.baseURL];
    NSURL *url = [NSURL URLWithString:urlString];
    
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    [request setHTTPMethod:@"POST"];
    
    NSString *boundary = [[NSUUID UUID] UUIDString];
    [request setValue:[NSString stringWithFormat:@"multipart/form-data; boundary=%@", boundary] forHTTPHeaderField:@"Content-Type"];
    
    NSMutableData *bodyData = [NSMutableData data];
    
    // 添加 access_token
    [bodyData appendData:[[NSString stringWithFormat:@"--%@\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];
    [bodyData appendData:[@"Content-Disposition: form-data; name=\"access_token\"\r\n\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [bodyData appendData:[self.accessToken dataUsingEncoding:NSUTF8StringEncoding]];
    [bodyData appendData:[@"\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    
    // 添加图片数据
    NSData *imageData = UIImageJPEGRepresentation(image, 0.8);
    [bodyData appendData:[[NSString stringWithFormat:@"--%@\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];
    [bodyData appendData:[@"Content-Disposition: form-data; name=\"image\"; filename=\"image.jpg\"\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [bodyData appendData:[@"Content-Type: image/jpeg\r\n\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [bodyData appendData:imageData];
    [bodyData appendData:[@"\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    
    [bodyData appendData:[[NSString stringWithFormat:@"--%@--\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];
    
    [request setHTTPBody:bodyData];
    
    NSURLSessionDataTask *task = [self.session dataTaskWithRequest:request completionHandler:^(NSData * _Nullable data, NSURLResponse * _Nullable response, NSError * _Nullable error) {
        dispatch_async(dispatch_get_main_queue(), ^{
            if (error) {
                if (completion) completion(NO, nil, error);
                return;
            }
            
            NSError *jsonError;
            NSDictionary *json = [NSJSONSerialization JSONObjectWithData:data options:0 error:&jsonError];
            
            if (jsonError) {
                if (completion) completion(NO, nil, jsonError);
                return;
            }
            
            if ([json[@"success"] boolValue] && json[@"url"]) {
                if (completion) completion(YES, json[@"url"], nil);
            } else {
                NSError *apiError = [NSError errorWithDomain:@"AIChatSDK" code:1004 userInfo:@{NSLocalizedDescriptionKey: json[@"error"] ?: @"图片上传失败"}];
                if (completion) completion(NO, nil, apiError);
            }
        });
    }];
    
    [task resume];
}

- (void)recognizeSpeechFromAudioData:(NSData *)audioData completion:(void (^)(BOOL success, NSString * _Nullable text, NSError * _Nullable error))completion {
    NSString *urlString = [NSString stringWithFormat:@"%@/api/speech-to-text", self.baseURL];
    NSURL *url = [NSURL URLWithString:urlString];
    
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    [request setHTTPMethod:@"POST"];
    
    NSString *boundary = [[NSUUID UUID] UUIDString];
    [request setValue:[NSString stringWithFormat:@"multipart/form-data; boundary=%@", boundary] forHTTPHeaderField:@"Content-Type"];
    
    NSMutableData *bodyData = [NSMutableData data];
    
    // 添加音频数据
    [bodyData appendData:[[NSString stringWithFormat:@"--%@\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];
    [bodyData appendData:[@"Content-Disposition: form-data; name=\"audio\"; filename=\"audio.wav\"\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [bodyData appendData:[@"Content-Type: audio/wav\r\n\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [bodyData appendData:audioData];
    [bodyData appendData:[@"\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    
    [bodyData appendData:[[NSString stringWithFormat:@"--%@--\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];
    
    [request setHTTPBody:bodyData];
    
    NSURLSessionDataTask *task = [self.session dataTaskWithRequest:request completionHandler:^(NSData * _Nullable data, NSURLResponse * _Nullable response, NSError * _Nullable error) {
        dispatch_async(dispatch_get_main_queue(), ^{
            if (error) {
                if (completion) completion(NO, nil, error);
                return;
            }
            
            NSError *jsonError;
            NSDictionary *json = [NSJSONSerialization JSONObjectWithData:data options:0 error:&jsonError];
            
            if (jsonError) {
                if (completion) completion(NO, nil, jsonError);
                return;
            }
            
            if ([json[@"success"] boolValue] && json[@"text"]) {
                if (completion) completion(YES, json[@"text"], nil);
            } else {
                NSError *apiError = [NSError errorWithDomain:@"AIChatSDK" code:1005 userInfo:@{NSLocalizedDescriptionKey: json[@"error"] ?: @"语音识别失败"}];
                if (completion) completion(NO, nil, apiError);
            }
        });
    }];
    
    [task resume];
}

- (void)cancelCurrentRequest {
    [self.currentTask cancel];
    self.currentTask = nil;
}

@end


#pragma mark - AIChatSDK Main Class

static AIChatConfig *globalDefaultConfig = nil;

@implementation AIChatSDK

+ (NSString *)version {
    return @"1.0.0";
}

+ (AIChatViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken {
    return [self createChatViewControllerWithAccessToken:accessToken config:nil];
}

+ (AIChatViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken config:(AIChatConfig *)config {
    AIChatConfig *useConfig = config ?: [self defaultConfig];
    AIChatViewController *vc = [[AIChatViewController alloc] initWithConfig:useConfig accessToken:accessToken];
    return vc;
}

+ (void)setDefaultConfig:(AIChatConfig *)config {
    globalDefaultConfig = config;
}

+ (AIChatConfig *)defaultConfig {
    return globalDefaultConfig ?: [AIChatConfig defaultConfig];
}

@end
