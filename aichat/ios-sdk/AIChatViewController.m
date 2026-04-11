//
//  AIChatViewController.m
//  AIChatSDK
//

#import "AIChatSDK.h"
#import <AVFoundation/AVFoundation.h>
#import <Speech/Speech.h>

#pragma mark - AIChatMessageCell

@interface AIChatMessageCell : UITableViewCell
@property (nonatomic, strong) UILabel *contentLabel;
@property (nonatomic, strong) UIView *bubbleView;
@property (nonatomic, strong) UIImageView *avatarImageView;
- (void)configureWithMessage:(AIChatMessage *)message themeColor:(UIColor *)themeColor;
@end

@implementation AIChatMessageCell

- (instancetype)initWithStyle:(UITableViewCellStyle)style reuseIdentifier:(NSString *)reuseIdentifier {
    self = [super initWithStyle:style reuseIdentifier:reuseIdentifier];
    if (self) {
        self.backgroundColor = [UIColor clearColor];
        self.selectionStyle = UITableViewCellSelectionStyleNone;
        
        // Avatar
        _avatarImageView = [[UIImageView alloc] initWithFrame:CGRectMake(0, 0, 32, 32)];
        _avatarImageView.layer.cornerRadius = 16;
        _avatarImageView.clipsToBounds = YES;
        [self.contentView addSubview:_avatarImageView];
        
        // Bubble
        _bubbleView = [[UIView alloc] init];
        _bubbleView.layer.cornerRadius = 16;
        [self.contentView addSubview:_bubbleView];
        
        // Content
        _contentLabel = [[UILabel alloc] init];
        _contentLabel.numberOfLines = 0;
        _contentLabel.font = [UIFont systemFontOfSize:15];
        [_bubbleView addSubview:_contentLabel];
    }
    return self;
}

- (void)configureWithMessage:(AIChatMessage *)message themeColor:(UIColor *)themeColor {
    CGFloat margin = 15;
    CGFloat bubbleMargin = 50;
    CGFloat maxWidth = [UIScreen mainScreen].bounds.size.width - bubbleMargin - margin * 2 - 40;
    
    // 计算内容大小
    CGSize contentSize = [message.content boundingRectWithSize:CGSizeMake(maxWidth, CGFLOAT_MAX)
                                                       options:NSStringDrawingUsesLineFragmentOrigin
                                                    attributes:@{NSFontAttributeName: self.contentLabel.font}
                                                       context:nil].size;
    contentSize.width = ceil(contentSize.width);
    contentSize.height = ceil(contentSize.height);
    
    CGFloat padding = 12;
    CGFloat bubbleWidth = contentSize.width + padding * 2;
    CGFloat bubbleHeight = contentSize.height + padding * 2;
    
    if (message.role == AIChatMessageRoleUser) {
        // 用户消息 - 右侧
        self.avatarImageView.hidden = YES;
        self.bubbleView.backgroundColor = themeColor;
        self.contentLabel.textColor = [UIColor whiteColor];
        
        self.bubbleView.frame = CGRectMake([UIScreen mainScreen].bounds.size.width - bubbleWidth - margin, 8, bubbleWidth, bubbleHeight);
        self.bubbleView.layer.maskedCorners = kCALayerMinXMinYCorner | kCALayerMinXMaxYCorner | kCALayerMaxXMinYCorner;
    } else {
        // 助手消息 - 左侧
        self.avatarImageView.hidden = NO;
        self.avatarImageView.frame = CGRectMake(margin, 8, 32, 32);
        self.avatarImageView.backgroundColor = themeColor;
        self.avatarImageView.image = nil;
        
        self.bubbleView.backgroundColor = [UIColor whiteColor];
        self.contentLabel.textColor = [UIColor darkTextColor];
        
        self.bubbleView.frame = CGRectMake(margin + 40, 8, bubbleWidth, bubbleHeight);
        self.bubbleView.layer.maskedCorners = kCALayerMaxXMinYCorner | kCALayerMaxXMaxYCorner | kCALayerMinXMaxYCorner;
        self.bubbleView.layer.shadowColor = [UIColor blackColor].CGColor;
        self.bubbleView.layer.shadowOffset = CGSizeMake(0, 1);
        self.bubbleView.layer.shadowOpacity = 0.1;
        self.bubbleView.layer.shadowRadius = 2;
    }
    
    self.contentLabel.frame = CGRectMake(padding, padding, contentSize.width, contentSize.height);
    self.contentLabel.text = message.content;
}

@end


#pragma mark - AIChatInputView

@interface AIChatInputView : UIView
@property (nonatomic, strong) UITextView *textView;
@property (nonatomic, strong) UIButton *sendButton;
@property (nonatomic, strong) UIButton *voiceButton;
@property (nonatomic, strong) UIButton *imageButton;
@property (nonatomic, copy) void (^onSendTap)(NSString *text);
@property (nonatomic, copy) void (^onVoiceLongPress)(UILongPressGestureRecognizer *gesture);
@property (nonatomic, copy) void (^onImageTap)(void);
@end

@implementation AIChatInputView

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        self.backgroundColor = [UIColor whiteColor];
        
        // 添加分割线
        UIView *topLine = [[UIView alloc] initWithFrame:CGRectMake(0, 0, frame.size.width, 0.5)];
        topLine.backgroundColor = [UIColor lightGrayColor];
        topLine.alpha = 0.3;
        [self addSubview:topLine];
        
        // 图片按钮
        _imageButton = [UIButton buttonWithType:UIButtonTypeSystem];
        _imageButton.frame = CGRectMake(10, 10, 30, 30);
        [_imageButton setImage:[UIImage systemImageNamed:@"photo"] forState:UIControlStateNormal];
        _imageButton.tintColor = [UIColor grayColor];
        [_imageButton addTarget:self action:@selector(imageTapped) forControlEvents:UIControlEventTouchUpInside];
        [self addSubview:_imageButton];
        
        // 输入框
        _textView = [[UITextView alloc] initWithFrame:CGRectMake(50, 8, frame.size.width - 110, 34)];
        _textView.layer.cornerRadius = 17;
        _textView.layer.borderWidth = 0.5;
        _textView.layer.borderColor = [UIColor lightGrayColor].CGColor;
        _textView.font = [UIFont systemFontOfSize:16];
        _textView.textContainerInset = UIEdgeInsetsMake(7, 10, 7, 10);
        _textView.returnKeyType = UIReturnKeySend;
        _textView.enablesReturnKeyAutomatically = YES;
        [self addSubview:_textView];
        
        // 发送按钮
        _sendButton = [UIButton buttonWithType:UIButtonTypeSystem];
        _sendButton.frame = CGRectMake(frame.size.width - 50, 10, 40, 30);
        [_sendButton setImage:[UIImage systemImageNamed:@"paperplane.fill"] forState:UIControlStateNormal];
        _sendButton.tintColor = [UIColor colorWithRed:48.0/255.0 green:194.0/255.0 blue:179.0/255.0 alpha:1.0];
        [_sendButton addTarget:self action:@selector(sendTapped) forControlEvents:UIControlEventTouchUpInside];
        [self addSubview:_sendButton];
        
        // 语音按钮（长按）
        _voiceButton = [UIButton buttonWithType:UIButtonTypeSystem];
        _voiceButton.frame = CGRectMake(50, 8, frame.size.width - 110, 34);
        _voiceButton.layer.cornerRadius = 17;
        _voiceButton.backgroundColor = [UIColor colorWithWhite:0.95 alpha:1.0];
        [_voiceButton setTitle:@"按住 说话" forState:UIControlStateNormal];
        [_voiceButton setTitleColor:[UIColor darkTextColor] forState:UIControlStateNormal];
        _voiceButton.titleLabel.font = [UIFont systemFontOfSize:16];
        _voiceButton.hidden = YES;
        [self addSubview:_voiceButton];
        
        // 添加长按手势
        UILongPressGestureRecognizer *longPress = [[UILongPressGestureRecognizer alloc] initWithTarget:self action:@selector(voiceLongPress:)];
        longPress.minimumPressDuration = 0.3;
        [_voiceButton addGestureRecognizer:longPress];
    }
    return self;
}

- (void)sendTapped {
    NSString *text = self.textView.text;
    if (text.length > 0) {
        if (self.onSendTap) {
            self.onSendTap(text);
        }
        self.textView.text = @"";
    }
}

- (void)imageTapped {
    if (self.onImageTap) {
        self.onImageTap();
    }
}

- (void)voiceLongPress:(UILongPressGestureRecognizer *)gesture {
    if (self.onVoiceLongPress) {
        self.onVoiceLongPress(gesture);
    }
}

@end


#pragma mark - AIChatViewController Implementation

@interface AIChatViewController () <UITableViewDelegate, UITableViewDataSource, UITextViewDelegate, AIChatServiceDelegate, UIImagePickerControllerDelegate, UINavigationControllerDelegate>
@property (nonatomic, strong) AIChatConfig *config;
@property (nonatomic, strong, readwrite) AIChatService *chatService;
@property (nonatomic, strong) UITableView *tableView;
@property (nonatomic, strong) AIChatInputView *inputView;
@property (nonatomic, strong) NSMutableArray<AIChatMessage *> *messages;
@property (nonatomic, strong) UIActivityIndicatorView *loadingIndicator;
@property (nonatomic, strong) UIView *voiceStatusView;
@property (nonatomic, strong) UILabel *voiceStatusLabel;
@property (nonatomic, strong) AVAudioRecorder *audioRecorder;
@property (nonatomic, strong) NSURL *audioRecordingURL;
@property (nonatomic, assign) BOOL isRecording;
@end

@implementation AIChatViewController

- (instancetype)initWithConfig:(AIChatConfig *)config accessToken:(NSString *)accessToken {
    self = [super init];
    if (self) {
        _config = config;
        _chatService = [[AIChatService alloc] initWithBaseURL:config.baseURL accessToken:accessToken];
        _chatService.delegate = self;
        _messages = [NSMutableArray array];
    }
    return self;
}

- (instancetype)initWithAccessToken:(NSString *)accessToken {
    return [self initWithConfig:[AIChatConfig defaultConfig] accessToken:accessToken];
}

- (void)viewDidLoad {
    [super viewDidLoad];
    
    self.view.backgroundColor = [UIColor colorWithRed:245.0/255.0 green:245.0/255.0 blue:245.0/255.0 alpha:1.0];
    
    // 设置导航栏
    self.title = self.config.title;
    self.navigationController.navigationBar.backgroundColor = self.config.navigationBarColor;
    
    // 添加返回按钮
    UIBarButtonItem *backItem = [[UIBarButtonItem alloc] initWithTitle:@"返回"
                                                                  style:UIBarButtonItemStylePlain
                                                                 target:self
                                                                 action:@selector(backTapped)];
    self.navigationItem.leftBarButtonItem = backItem;
    
    // 创建消息列表
    [self setupTableView];
    
    // 创建输入框
    [self setupInputView];
    
    // 创建语音状态视图
    [self setupVoiceStatusView];
    
    // 添加欢迎消息
    [self addWelcomeMessage];
    
    // 请求麦克风权限
    [self requestMicrophonePermission];
    
    // 加载用户信息
    [self loadUserInfo];
    
    // 注册键盘通知
    [[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(keyboardWillShow:) name:UIKeyboardWillShowNotification object:nil];
    [[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(keyboardWillHide:) name:UIKeyboardWillHideNotification object:nil];
}

- (void)setupTableView {
    self.tableView = [[UITableView alloc] initWithFrame:CGRectMake(0, 0, self.view.bounds.size.width, self.view.bounds.size.height - 60) style:UITableViewStylePlain];
    self.tableView.delegate = self;
    self.tableView.dataSource = self;
    self.tableView.backgroundColor = [UIColor clearColor];
    self.tableView.separatorStyle = UITableViewCellSeparatorStyleNone;
    self.tableView.estimatedRowHeight = 60;
    self.tableView.rowHeight = UITableViewAutomaticDimension;
    [self.view addSubview:self.tableView];
}

- (void)setupInputView {
    CGFloat bottomSafeArea = 0;
    if (@available(iOS 11.0, *)) {
        bottomSafeArea = self.view.safeAreaInsets.bottom;
    }
    
    self.inputView = [[AIChatInputView alloc] initWithFrame:CGRectMake(0, self.view.bounds.size.height - 60 - bottomSafeArea, self.view.bounds.size.width, 60)];
    
    __weak typeof(self) weakSelf = self;
    self.inputView.onSendTap = ^(NSString *text) {
        [weakSelf sendTextMessage:text];
    };
    
    self.inputView.onVoiceLongPress = ^(UILongPressGestureRecognizer *gesture) {
        [weakSelf handleVoiceLongPress:gesture];
    };
    
    self.inputView.onImageTap = ^{
        [weakSelf selectImage];
    };
    
    [self.view addSubview:self.inputView];
}

- (void)setupVoiceStatusView {
    self.voiceStatusView = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 150, 150)];
    self.voiceStatusView.center = self.view.center;
    self.voiceStatusView.backgroundColor = [UIColor colorWithWhite:0 alpha:0.8];
    self.voiceStatusView.layer.cornerRadius = 10;
    self.voiceStatusView.hidden = YES;
    
    UILabel *micLabel = [[UILabel alloc] initWithFrame:CGRectMake(0, 30, 150, 40)];
    micLabel.text = @"🎤";
    micLabel.font = [UIFont systemFontOfSize:40];
    micLabel.textAlignment = NSTextAlignmentCenter;
    [self.voiceStatusView addSubview:micLabel];
    
    self.voiceStatusLabel = [[UILabel alloc] initWithFrame:CGRectMake(0, 80, 150, 20)];
    self.voiceStatusLabel.text = @"正在录音...";
    self.voiceStatusLabel.textColor = [UIColor whiteColor];
    self.voiceStatusLabel.textAlignment = NSTextAlignmentCenter;
    self.voiceStatusLabel.font = [UIFont systemFontOfSize:14];
    [self.voiceStatusView addSubview:self.voiceStatusLabel];
    
    UILabel *tipLabel = [[UILabel alloc] initWithFrame:CGRectMake(0, 110, 150, 20)];
    tipLabel.text = @"松开发送，上滑取消";
    tipLabel.textColor = [UIColor lightGrayColor];
    tipLabel.textAlignment = NSTextAlignmentCenter;
    tipLabel.font = [UIFont systemFontOfSize:12];
    [self.voiceStatusView addSubview:tipLabel];
    
    [self.view addSubview:self.voiceStatusView];
}

- (void)addWelcomeMessage {
    AIChatMessage *welcomeMessage = [[AIChatMessage alloc] initWithRole:AIChatMessageRoleAssistant type:AIChatMessageTypeText content:[NSString stringWithFormat:@"%@\n%@", self.config.welcomeTitle, self.config.welcomeMessage]];
    [self.messages addObject:welcomeMessage];
    [self.tableView reloadData];
}

- (void)requestMicrophonePermission {
    [[AVAudioSession sharedInstance] requestRecordPermission:^(BOOL granted) {
        NSLog(@"麦克风权限: %@", granted ? @"已授权" : @"被拒绝");
    }];
}

- (void)loadUserInfo {
    [self.chatService loadUserInfoWithCompletion:^(BOOL success, NSDictionary * _Nullable userInfo, NSError * _Nullable error) {
        if (!success) {
            NSLog(@"加载用户信息失败: %@", error.localizedDescription);
        }
    }];
}

#pragma mark - Actions

- (void)backTapped {
    if ([self.delegate respondsToSelector:@selector(chatViewControllerDidTapBack:)]) {
        [self.delegate chatViewControllerDidTapBack:self];
    }
    [self.navigationController popViewControllerAnimated:YES];
}

- (void)sendTextMessage:(NSString *)text {
    if (text.length == 0) return;
    
    // 添加用户消息
    AIChatMessage *userMessage = [[AIChatMessage alloc] initWithRole:AIChatMessageRoleUser type:AIChatMessageTypeText content:text];
    [self.messages addObject:userMessage];
    [self.tableView reloadData];
    [self scrollToBottom];
    
    // 收起键盘
    [self.inputView.textView resignFirstResponder];
    
    // 发送到服务器
    [self.chatService sendMessage:text completion:^(BOOL success, AIChatMessage * _Nullable message, NSError * _Nullable error) {
        if (success && message) {
            [self.messages addObject:message];
            [self.tableView reloadData];
            [self scrollToBottom];
        }
    }];
}

- (void)handleVoiceLongPress:(UILongPressGestureRecognizer *)gesture {
    switch (gesture.state) {
        case UIGestureRecognizerStateBegan:
            [self startRecording];
            break;
        case UIGestureRecognizerStateChanged: {
            CGPoint location = [gesture locationInView:self.view];
            if (location.y < self.view.center.y - 50) {
                self.voiceStatusLabel.text = @"松开取消";
            } else {
                self.voiceStatusLabel.text = @"正在录音...";
            }
            break;
        }
        case UIGestureRecognizerStateEnded:
        case UIGestureRecognizerStateCancelled: {
            CGPoint location = [gesture locationInView:self.view];
            BOOL isCancelled = location.y < self.view.center.y - 50;
            [self stopRecording:cancelled:isCancelled];
            break;
        }
        default:
            break;
    }
}

- (void)startRecording {
    AVAudioSession *session = [AVAudioSession sharedInstance];
    NSError *error;
    [session setCategory:AVAudioSessionCategoryPlayAndRecord error:&error];
    [session setActive:YES error:&error];
    
    NSString *tempDir = NSTemporaryDirectory();
    NSString *audioPath = [tempDir stringByAppendingPathComponent:@"recording.wav"];
    self.audioRecordingURL = [NSURL fileURLWithPath:audioPath];
    
    NSDictionary *settings = @{
        AVFormatIDKey: @(kAudioFormatLinearPCM),
        AVSampleRateKey: @16000.0,
        AVNumberOfChannelsKey: @1,
        AVLinearPCMBitDepthKey: @16
    };
    
    self.audioRecorder = [[AVAudioRecorder alloc] initWithURL:self.audioRecordingURL settings:settings error:&error];
    if (error) {
        NSLog(@"录音初始化失败: %@", error);
        return;
    }
    
    [self.audioRecorder prepareToRecord];
    [self.audioRecorder record];
    self.isRecording = YES;
    
    self.voiceStatusView.hidden = NO;
    self.voiceStatusLabel.text = @"正在录音...";
}

- (void)stopRecording:(BOOL)cancelled {
    if (!self.isRecording) return;
    
    [self.audioRecorder stop];
    self.isRecording = NO;
    self.voiceStatusView.hidden = YES;
    
    if (cancelled) {
        NSLog(@"录音已取消");
        return;
    }
    
    // 发送录音进行识别
    NSData *audioData = [NSData dataWithContentsOfURL:self.audioRecordingURL];
    if (audioData) {
        [self.chatService recognizeSpeechFromAudioData:audioData completion:^(BOOL success, NSString * _Nullable text, NSError * _Nullable error) {
            if (success && text.length > 0) {
                [self sendTextMessage:text];
            } else {
                NSLog(@"语音识别失败: %@", error.localizedDescription);
            }
        }];
    }
}

- (void)selectImage {
    UIImagePickerController *picker = [[UIImagePickerController alloc] init];
    picker.delegate = self;
    picker.sourceType = UIImagePickerControllerSourceTypePhotoLibrary;
    [self presentViewController:picker animated:YES completion:nil];
}

#pragma mark - UIImagePickerControllerDelegate

- (void)imagePickerController:(UIImagePickerController *)picker didFinishPickingMediaWithInfo:(NSDictionary<UIImagePickerControllerInfoKey,id> *)info {
    [picker dismissViewControllerAnimated:YES completion:nil];
    
    UIImage *image = info[UIImagePickerControllerOriginalImage];
    if (image) {
        // 上传图片
        [self.chatService uploadImage:image completion:^(BOOL success, NSString * _Nullable imageURL, NSError * _Nullable error) {
            if (success) {
                // 发送带图片的消息
                [self.chatService sendMessage:@"" imageURLs:@[imageURL] completion:^(BOOL success, AIChatMessage * _Nullable message, NSError * _Nullable error) {
                    if (success) {
                        [self.messages addObject:message];
                        [self.tableView reloadData];
                        [self scrollToBottom];
                    }
                }];
            }
        }];
    }
}

#pragma mark - UITableViewDataSource

- (NSInteger)tableView:(UITableView *)tableView numberOfRowsInSection:(NSInteger)section {
    return self.messages.count;
}

- (UITableViewCell *)tableView:(UITableView *)tableView cellForRowAtIndexPath:(NSIndexPath *)indexPath {
    static NSString *cellId = @"MessageCell";
    AIChatMessageCell *cell = [tableView dequeueReusableCellWithIdentifier:cellId];
    if (!cell) {
        cell = [[AIChatMessageCell alloc] initWithStyle:UITableViewCellStyleDefault reuseIdentifier:cellId];
    }
    
    AIChatMessage *message = self.messages[indexPath.row];
    [cell configureWithMessage:message themeColor:self.config.themeColor];
    
    return cell;
}

#pragma mark - AIChatServiceDelegate

- (void)chatService:(AIChatService *)service didReceiveStreamContent:(NSString *)content forMessage:(AIChatMessage *)message {
    dispatch_async(dispatch_get_main_queue(), ^{
        [self.tableView reloadData];
    });
}

- (void)chatService:(AIChatService *)service didCompleteMessage:(AIChatMessage *)message {
    dispatch_async(dispatch_get_main_queue(), ^{
        [self.tableView reloadData];
        [self scrollToBottom];
    });
}

- (void)chatService:(AIChatService *)service didEncounterError:(NSError *)error {
    dispatch_async(dispatch_get_main_queue(), ^{
        UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"错误" message:error.localizedDescription preferredStyle:UIAlertControllerStyleAlert];
        [alert addAction:[UIAlertAction actionWithTitle:@"确定" style:UIAlertActionStyleDefault handler:nil]];
        [self presentViewController:alert animated:YES completion:nil];
    });
}

#pragma mark - Keyboard Handling

- (void)keyboardWillShow:(NSNotification *)notification {
    CGRect keyboardFrame = [notification.userInfo[UIKeyboardFrameEndUserInfoKey] CGRectValue];
    CGFloat keyboardHeight = keyboardFrame.size.height;
    
    [UIView animateWithDuration:0.3 animations:^{
        self.inputView.frame = CGRectMake(0, self.view.bounds.size.height - 60 - keyboardHeight, self.view.bounds.size.width, 60);
        self.tableView.frame = CGRectMake(0, 0, self.view.bounds.size.width, self.view.bounds.size.height - 60 - keyboardHeight);
    }];
    
    [self scrollToBottom];
}

- (void)keyboardWillHide:(NSNotification *)notification {
    CGFloat bottomSafeArea = 0;
    if (@available(iOS 11.0, *)) {
        bottomSafeArea = self.view.safeAreaInsets.bottom;
    }
    
    [UIView animateWithDuration:0.3 animations:^{
        self.inputView.frame = CGRectMake(0, self.view.bounds.size.height - 60 - bottomSafeArea, self.view.bounds.size.width, 60);
        self.tableView.frame = CGRectMake(0, 0, self.view.bounds.size.width, self.view.bounds.size.height - 60 - bottomSafeArea);
    }];
}

#pragma mark - Public Methods

- (void)scrollToBottom {
    if (self.messages.count > 0) {
        NSIndexPath *indexPath = [NSIndexPath indexPathForRow:self.messages.count - 1 inSection:0];
        [self.tableView scrollToRowAtIndexPath:indexPath atScrollPosition:UITableViewScrollPositionBottom animated:YES];
    }
}

- (void)addSystemMessage:(NSString *)content {
    AIChatMessage *message = [[AIChatMessage alloc] initWithRole:AIChatMessageRoleAssistant type:AIChatMessageTypeText content:content];
    [self.messages addObject:message];
    [self.tableView reloadData];
    [self scrollToBottom];
}

- (void)clearChatHistory {
    [self.messages removeAllObjects];
    [self.tableView reloadData];
    [self addWelcomeMessage];
}

- (void)dealloc {
    [[NSNotificationCenter defaultCenter] removeObserver:self];
}

@end
