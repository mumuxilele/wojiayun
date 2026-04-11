//
//  AIChatSDK.m
//  AIChatSDK
//
//  Created by wojiacloud on 2026/04/08.
//

#import "AIChatSDK.h"
#import <WebKit/WebKit.h>
#import <Speech/Speech.h>
#import <AVFoundation/AVFoundation.h>

#pragma mark - AIChatConfig

@implementation AIChatConfig

+ (instancetype)configWithAccessToken:(NSString *)accessToken {
    AIChatConfig *config = [[AIChatConfig alloc] init];
    config.accessToken = accessToken;
    config.apiUrl = @"/api";
    config.enableVoice = YES;
    config.theme = @"light";
    return config;
}

@end

#pragma mark - AIChatViewController

/**
 * AI Chat 视图控制器
 */
@interface AIChatViewController : UIViewController <WKNavigationDelegate, WKScriptMessageHandler, SFSpeechRecognizerDelegate>

@property (nonatomic, strong) AIChatConfig *config;
@property (nonatomic, strong) WKWebView *webView;
@property (nonatomic, strong) UIActivityIndicatorView *loadingView;
@property (nonatomic, strong) UILabel *errorLabel;
@property (nonatomic, weak) id<AIChatSDKDelegate> delegate;

// 语音识别
@property (nonatomic, strong) SFSpeechRecognizer *speechRecognizer;
@property (nonatomic, strong) SFSpeechAudioBufferRecognitionRequest *recognitionRequest;
@property (nonatomic, strong) SFSpeechRecognitionTask *recognitionTask;
@property (nonatomic, strong) AVAudioEngine *audioEngine;

@end

@implementation AIChatViewController

- (instancetype)initWithConfig:(AIChatConfig *)config {
    self = [super init];
    if (self) {
        _config = config;
    }
    return self;
}

- (void)viewDidLoad {
    [super viewDidLoad];
    
    self.view.backgroundColor = [UIColor colorWithRed:245/255.0 green:245/255.0 blue:245/255.0 alpha:1.0];
    
    [self setupWebView];
    [self setupLoadingView];
    [self setupNavigationBar];
    [self loadChatPage];
    
    // 初始化语音识别
    if (self.config.enableVoice) {
        [self setupSpeechRecognition];
    }
}

- (void)setupWebView {
    WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];
    configuration.preferences.javaScriptEnabled = YES;
    
    // 添加脚本消息处理器
    WKUserContentController *contentController = [[WKUserContentController alloc] init];
    [contentController addScriptMessageHandler:self name:@"aiChat"];
    configuration.userContentController = contentController;
    
    self.webView = [[WKWebView alloc] initWithFrame:CGRectZero configuration:configuration];
    self.webView.navigationDelegate = self;
    self.webView.translatesAutoresizingMaskIntoConstraints = NO;
    self.webView.backgroundColor = [UIColor colorWithRed:245/255.0 green:245/255.0 blue:245/255.0 alpha:1.0];
    
    [self.view addSubview:self.webView];
    
    [NSLayoutConstraint activateConstraints:@[
        [self.webView.topAnchor constraintEqualToAnchor:self.view.topAnchor],
        [self.webView.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor],
        [self.webView.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor],
        [self.webView.bottomAnchor constraintEqualToAnchor:self.view.bottomAnchor]
    ]];
}

- (void)setupLoadingView {
    self.loadingView = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleLarge];
    self.loadingView.translatesAutoresizingMaskIntoConstraints = NO;
    self.loadingView.hidesWhenStopped = YES;
    [self.view addSubview:self.loadingView];
    
    [NSLayoutConstraint activateConstraints:@[
        [self.loadingView.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor],
        [self.loadingView.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor]
    ]];
    
    [self.loadingView startAnimating];
}

- (void)setupNavigationBar {
    self.title = @"AI 助手";
    
    UIBarButtonItem *closeItem = [[UIBarButtonItem alloc] initWithTitle:@"关闭"
                                                                 style:UIBarButtonItemStylePlain
                                                                target:self
                                                                action:@selector(closeButtonTapped)];
    self.navigationItem.rightBarButtonItem = closeItem;
}

- (void)loadChatPage {
    // 构建 URL
    NSURL *htmlURL = [[NSBundle mainBundle] URLForResource:@"index" withExtension:@"html"];
    
    if (htmlURL) {
        // 构建查询参数
        NSMutableArray *queryItems = [NSMutableArray array];
        [queryItems addObject:[NSURLQueryItem queryItemWithName:@"access_token" value:self.config.accessToken]];
        
        if (self.config.customVariables) {
            [self.config.customVariables enumerateKeysAndObjectsUsingBlock:^(NSString *key, NSString *value, BOOL *stop) {
                [queryItems addObject:[NSURLQueryItem queryItemWithName:key value:value]];
            }];
        }
        
        NSURLComponents *components = [NSURLComponents alloc];
        components.URL = htmlURL;
        components.queryItems = queryItems;
        
        NSURL *finalURL = components.URL;
        NSURLRequest *request = [NSURLRequest requestWithURL:finalURL];
        [self.webView loadRequest:request];
    } else {
        // 如果没有本地 HTML，加载远程 URL
        NSString *urlString = [NSString stringWithFormat:@"%@?access_token=%@",
                               self.config.apiUrl ?: @"/api",
                               self.config.accessToken];
        
        if (self.config.customVariables) {
            [self.config.customVariables enumerateKeysAndObjectsUsingBlock:^(NSString *key, NSString *value, BOOL *stop) {
                urlString = [urlString stringByAppendingFormat:@"&%@=%@", key, value];
            }];
        }
        
        NSURL *url = [NSURL URLWithString:urlString];
        NSURLRequest *request = [NSURLRequest requestWithURL:url];
        [self.webView loadRequest:request];
    }
}

- (void)closeButtonTapped {
    if (self.navigationController) {
        [self.navigationController popViewControllerAnimated:YES];
    } else {
        [self dismissViewControllerAnimated:YES completion:nil];
    }
}

#pragma mark - WKNavigationDelegate

- (void)webView:(WKWebView *)webView didFinishNavigation:(WKNavigation *)navigation {
    [self.loadingView stopAnimating];
    
    // 注入配置
    [self injectConfig];
}

- (void)webView:(WKWebView *)webView didFailNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    [self.loadingView stopAnimating];
    [self showError:error.localizedDescription];
}

- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    [self.loadingView stopAnimating];
    [self showError:error.localizedDescription];
}

#pragma mark - WKScriptMessageHandler

- (void)userContentController:(WKUserContentController *)userContentController didReceiveScriptMessage:(WKScriptMessage *)message {
    if ([message.name isEqualToString:@"aiChat"]) {
        NSDictionary *data = message.body;
        NSString *type = data[@"type"];
        
        if ([type isEqualToString:@"message"]) {
            if ([self.delegate respondsToSelector:@selector(aiChatDidReceiveMessage:)]) {
                [self.delegate aiChatDidReceiveMessage:data[@"payload"]];
            }
        } else if ([type isEqualToString:@"send"]) {
            if ([self.delegate respondsToSelector:@selector(aiChatDidSendMessage:)]) {
                [self.delegate aiChatDidSendMessage:data[@"payload"]];
            }
        } else if ([type isEqualToString:@"error"]) {
            NSError *error = [NSError errorWithDomain:@"AIChatSDK" code:0 userInfo:@{NSLocalizedDescriptionKey: data[@"message"]}];
            if ([self.delegate respondsToSelector:@selector(aiChatDidError:)]) {
                [self.delegate aiChatDidError:error];
            }
        }
    }
}

#pragma mark - JavaScript Bridge

- (void)injectConfig {
    // 注入配置到 JavaScript
    NSMutableDictionary *configDict = [NSMutableDictionary dictionary];
    configDict[@"accessToken"] = self.config.accessToken;
    configDict[@"apiUrl"] = self.config.apiUrl ?: @"/api";
    configDict[@"enableVoice"] = @(self.config.enableVoice);
    configDict[@"theme"] = self.config.theme ?: @"light";
    
    if (self.config.customVariables) {
        configDict[@"customVariables"] = self.config.customVariables;
    }
    
    NSData *jsonData = [NSJSONSerialization dataWithJSONObject:configDict options:0 error:nil];
    NSString *jsonString = [[NSString alloc] initWithData:jsonData encoding:NSUTF8StringEncoding];
    
    NSString *script = [NSString stringWithFormat:@"window.aiChatConfig = %@;", jsonString];
    [self.webView evaluateJavaScript:script completionHandler:nil];
}

- (void)sendMessageToJS:(NSString *)type payload:(id)payload {
    NSMutableDictionary *message = [NSMutableDictionary dictionary];
    message[@"type"] = type;
    message[@"payload"] = payload;
    
    NSData *jsonData = [NSJSONSerialization dataWithJSONObject:message options:0 error:nil];
    NSString *jsonString = [[NSString alloc] initWithData:jsonData encoding:NSUTF8StringEncoding];
    
    NSString *script = [NSString stringWithFormat:@"window.aiChatBridge.receiveMessage(%@)", jsonString];
    [self.webView evaluateJavaScript:script completionHandler:nil];
}

#pragma mark - Speech Recognition

- (void)setupSpeechRecognition {
    self.speechRecognizer = [[SFSpeechRecognizer alloc] initWithLocale:[[NSLocale alloc] initWithLocaleIdentifier:@"zh-CN"]];
    self.speechRecognizer.delegate = self;
    self.audioEngine = [[AVAudioEngine alloc] init];
    
    [SFSpeechRecognizer requestAuthorization:^(SFSpeechRecognizerAuthorizationStatus status) {
        if (status != SFSpeechRecognizerAuthorizationStatusAuthorized) {
            NSLog(@"Speech recognition not authorized");
        }
    }];
}

- (void)startVoiceRecording {
    if (!self.speechRecognizer) {
        return;
    }
    
    [self.recognitionTask cancel];
    self.recognitionTask = nil;
    
    AVAudioSession *audioSession = [AVAudioSession sharedInstance];
    [audioSession setCategory:AVAudioSessionCategoryRecord mode:AVAudioSessionModeMeasurement options:0 error:nil];
    [audioSession setActive:YES withOptions:0 error:nil];
    
    self.recognitionRequest = [[SFSpeechAudioBufferRecognitionRequest alloc] init];
    self.recognitionRequest.shouldReportPartialResults = YES;
    
    __weak typeof(self) weakSelf = self;
    self.recognitionTask = [self.speechRecognizer recognitionTaskWithRequest:self.recognitionRequest resultHandler:^(SFSpeechRecognitionResult * _Nullable result, NSError * _Nullable error) {
        if (result) {
            NSString *transcription = result.bestTranscription.formattedString;
            
            if ([weakSelf.delegate respondsToSelector:@selector(aiChatVoiceRecognitionResult:)]) {
                [weakSelf.delegate aiChatVoiceRecognitionResult:transcription];
            }
            
            // 发送到 JS
            [weakSelf sendMessageToJS:@"voiceResult" payload:@{@"text": transcription}];
            
            if (result.isFinal) {
                [weakSelf sendMessageToJS:@"voiceFinal" payload:@{@"text": transcription}];
            }
        }
        
        if (error) {
            NSLog(@"Speech recognition error: %@", error);
        }
    }];
    
    AVAudioInputNode *inputNode = self.audioEngine.inputNode;
    AVAudioFormat *format = [inputNode outputFormatForBus:0];
    
    [inputNode installTapOnBus:0 bufferSize:1024 format:format block:^(AVAudioPCMBuffer * _Nonnull buffer, AVAudioTime * _Nonnull when) {
        [weakSelf.recognitionRequest appendAudioPCMBuffer:buffer];
    }];
    
    [self.audioEngine prepare];
    [self.audioEngine startAndReturnError:nil];
}

- (void)stopVoiceRecording {
    [self.audioEngine stop];
    [self.recognitionRequest endAudio];
}

#pragma mark - Error Handling

- (void)showError:(NSString *)message {
    if (!self.errorLabel) {
        self.errorLabel = [[UILabel alloc] init];
        self.errorLabel.translatesAutoresizingMaskIntoConstraints = NO;
        self.errorLabel.textColor = [UIColor redColor];
        self.errorLabel.textAlignment = NSTextAlignmentCenter;
        self.errorLabel.numberOfLines = 0;
        [self.view addSubview:self.errorLabel];
        
        [NSLayoutConstraint activateConstraints:@[
            [self.errorLabel.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor],
            [self.errorLabel.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor],
            [self.errorLabel.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor constant:20],
            [self.errorLabel.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor constant:-20]
        ]];
    }
    
    self.errorLabel.text = message;
    self.errorLabel.hidden = NO;
}

@end

#pragma mark - AIChatSDK

@interface AIChatSDK ()

@property (nonatomic, weak) id<AIChatSDKDelegate> delegate;
@property (nonatomic, assign) BOOL debugMode;

@end

@implementation AIChatSDK

static id<AIChatSDKDelegate> _delegate;
static BOOL _debugMode = NO;

+ (NSString *)version {
    return @"1.0.0";
}

+ (UIViewController *)createChatViewControllerWithConfig:(AIChatConfig *)config {
    AIChatViewController *viewController = [[AIChatViewController alloc] initWithConfig:config];
    viewController.delegate = _delegate;
    return viewController;
}

+ (UIViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken {
    AIChatConfig *config = [AIChatConfig configWithAccessToken:accessToken];
    return [self createChatViewControllerWithConfig:config];
}

+ (UIViewController *)createChatViewControllerWithAccessToken:(NSString *)accessToken
                                                      apiUrl:(NSString *)apiUrl
                                              customVariables:(NSDictionary<NSString *,NSString *> *)customVariables {
    AIChatConfig *config = [AIChatConfig configWithAccessToken:accessToken];
    config.apiUrl = apiUrl;
    config.customVariables = customVariables;
    return [self createChatViewControllerWithConfig:config];
}

+ (UIView *)createChatViewWithFrame:(CGRect)frame
                             config:(AIChatConfig *)config {
    UIViewController *viewController = [self createChatViewControllerWithConfig:config];
    viewController.view.frame = frame;
    return viewController.view;
}

+ (UIView *)createChatViewWithFrame:(CGRect)frame
                        accessToken:(NSString *)accessToken {
    AIChatConfig *config = [AIChatConfig configWithAccessToken:accessToken];
    return [self createChatViewWithFrame:frame config:config];
}

+ (void)setDelegate:(id<AIChatSDKDelegate>)delegate {
    _delegate = delegate;
}

+ (void)setDebugMode:(BOOL)enable {
    _debugMode = enable;
}

+ (void)cleanup {
    // 清理资源
}

@end