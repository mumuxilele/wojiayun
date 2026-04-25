//
//  AIChatSDK.m
//  AIChatSDK
//

#import "AIChatSDK.h"
#import "AIChatViewController.h"

@implementation AIChatConfig

+ (instancetype)configWithAccessToken:(NSString *)accessToken {
    return [self configWithAccessToken:accessToken apiUrl:@"/api"];
}

+ (instancetype)configWithAccessToken:(NSString *)accessToken apiUrl:(NSString *)apiUrl {
    AIChatConfig *cfg = [[AIChatConfig alloc] init];
    cfg.accessToken = accessToken;
    cfg.apiUrl = apiUrl ?: @"/api";
    cfg.enableVoice = YES;
    cfg.pageTitle = @"AI智能助手";
    return cfg;
}

@end

@implementation AIChatSDK

+ (NSString *)version {
    return @"1.0.0";
}

+ (UIViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken {
    return [self createChatViewControllerWithConfig:[AIChatConfig configWithAccessToken:accessToken]];
}

+ (UIViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken
                                                      apiUrl:(NSString *)apiUrl
                                                   pageTitle:(NSString *)pageTitle
                                             customVariables:(NSDictionary *)customVariables {
    AIChatConfig *config = [AIChatConfig configWithAccessToken:accessToken apiUrl:apiUrl];
    config.pageTitle = pageTitle;
    config.customVariables = customVariables;
    return [self createChatViewControllerWithConfig:config];
}

+ (UIViewController *)createChatViewControllerWithConfig:(AIChatConfig *)config {
    if (!config.accessToken || config.accessToken.length == 0) {
        NSLog(@"[AIChatSDK] Error: accessToken is required");
        return nil;
    }
    
    AIChatViewController *vc = [[AIChatViewController alloc] initWithConfig:config];
    return vc;
}

+ (void)setLogLevel:(NSInteger)level {
    // 日志级别控制，可后续扩展
}

@end
