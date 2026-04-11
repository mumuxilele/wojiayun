//
//  AIChatViewControllerV2.m
//  AIChatSDK - V2 Version (1:1 with Web)
//

#import "AIChatSDK.h"
#import <AVFoundation/AVFoundation.h>
#import <Speech/Speech.h>
#import <Photos/Photos.h>

#pragma mark - Constants

#define kThemeColor [UIColor colorWithRed:48.0/255.0 green:194.0/255.0 blue:179.0/255.0 alpha:1.0]
#define kThemeColorDark [UIColor colorWithRed:38.0/255.0 green:166.0/255.0 blue:154.0/255.0 alpha:1.0]
#define kBackgroundColor [UIColor colorWithRed:245.0/255.0 green:245.0/255.0 blue:245.0/255.0 alpha:1.0]
#define kInputBoxColor [UIColor colorWithRed:245.0/255.0 green:245.0/255.0 blue:245.0/255.0 alpha:1.0]
#define kBorderColor [UIColor colorWithRed:221.0/255.0 green:221.0/255.0 blue:221.0/255.0 alpha:1.0]

#pragma mark - AIChatMessageCell (V2)

@interface AIChatMessageCellV2 : UITableViewCell
@property (nonatomic, strong) UILabel *contentLabel;
@property (nonatomic, strong) UIView *bubbleView;
@property (nonatomic, strong) UIImageView *avatarImageView;
@property (nonatomic, strong) UIImageView *messageImageView;
@property (nonatomic, strong) UIView *widgetContainerView;
- (void)configureWithMessage:(AIChatMessage *)message themeColor:(UIColor *)themeColor;
+ (CGFloat)heightForMessage:(AIChatMessage *)message width:(CGFloat)width;
@end

@implementation AIChatMessageCellV2

- (instancetype)initWithStyle:(UITableViewCellStyle)style reuseIdentifier:(NSString *)reuseIdentifier {
    self = [super initWithStyle:style reuseIdentifier:reuseIdentifier];
    if (self) {
        self.backgroundColor = [UIColor clearColor];
        self.selectionStyle = UITableViewCellSelectionStyleNone;
        
        // Avatar (助手消息显示)
        _avatarImageView = [[UIImageView alloc] init];
        _avatarImageView.layer.cornerRadius = 16;
        _avatarImageView.clipsToBounds = YES;
        _avatarImageView.backgroundColor = kThemeColor;
        [self.contentView addSubview:_avatarImageView];
        
        // Bubble
        _bubbleView = [[UIView alloc] init];
        _bubbleView.layer.cornerRadius = 16;
        [self.contentView addSubview:_bubbleView];
        
        // Content Label
        _contentLabel = [[UILabel alloc] init];
        _contentLabel.numberOfLines = 0;
        _contentLabel.font = [UIFont systemFontOfSize:15];
        [_bubbleView addSubview:_contentLabel];
        
        // Image View (for user images)
        _messageImageView = [[UIImageView alloc] init];
        _messageImageView.layer.cornerRadius = 8;
        _messageImageView.clipsToBounds = YES;
        _messageImageView.contentMode = UIViewContentModeScaleAspectFill;
        [self.contentView addSubview:_messageImageView];
        
        // Widget Container (for assistant widget messages)
        _widgetContainerView = [[UIView alloc] init];
        _widgetContainerView.hidden = YES;
        [self.contentView addSubview:_widgetContainerView];
    }
    return self;
}

- (void)configureWithMessage:(AIChatMessage *)message themeColor:(UIColor *)themeColor {
    CGFloat margin = 15;
    CGFloat bubbleMargin = 50;
    CGFloat maxWidth = [UIScreen mainScreen].bounds.size.width - bubbleMargin - margin * 2 - 40;
    
    // Reset
    self.widgetContainerView.hidden = YES;
    self.messageImageView.hidden = YES;
    self.bubbleView.hidden = NO;
    self.contentLabel.hidden = NO;
    
    if (message.role == AIChatMessageRoleUser) {
        // 用户消息 - 右侧
        self.avatarImageView.hidden = YES;
        
        // 渐变色背景
        CAGradientLayer *gradient = [CAGradientLayer layer];
        gradient.frame = CGRectMake(0, 0, 100, 44);
        gradient.colors = @[(__bridge id)[UIColor colorWithRed:48.0/255.0 green:194.0/255.0 blue:179.0/255.0 alpha:1.0].CGColor,
                           (__bridge id)[UIColor colorWithRed:38.0/255.0 green:166.0/255.0 blue:154.0/255.0 alpha:1.0].CGColor];
        gradient.startPoint = CGPointMake(0, 0);
        gradient.endPoint = CGPointMake(1, 1);
        gradient.cornerRadius = 16;
        
        // 移除旧gradient
        for (CALayer *layer in self.bubbleView.layer.sublayers) {
            if ([layer isKindOfClass:[CAGradientLayer class]]) {
                [layer removeFromSuperlayer];
            }
        }
        [self.bubbleView.layer insertSublayer:gradient atIndex:0];
        
        self.bubbleView.backgroundColor = [UIColor clearColor];
        self.contentLabel.textColor = [UIColor whiteColor];
        
        // 圆角设置 - 左上和左下圆角
        self.bubbleView.layer.maskedCorners = kCALayerMinXMinYCorner | kCALayerMinXMaxYCorner | kCALayerMaxXMinYCorner;
        
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
        
        self.bubbleView.frame = CGRectMake([UIScreen mainScreen].bounds.size.width - bubbleWidth - margin, 8, bubbleWidth, bubbleHeight);
        self.contentLabel.frame = CGRectMake(padding, padding, contentSize.width, contentSize.height);
        self.contentLabel.text = message.content;
        
    } else {
        // 助手消息 - 左侧
        self.avatarImageView.hidden = NO;
        self.avatarImageView.frame = CGRectMake(margin, 8, 32, 32);
        
        self.bubbleView.backgroundColor = [UIColor whiteColor];
        self.contentLabel.textColor = [UIColor darkTextColor];
        
        // 阴影
        self.bubbleView.layer.shadowColor = [UIColor blackColor].CGColor;
        self.bubbleView.layer.shadowOffset = CGSizeMake(0, 1);
        self.bubbleView.layer.shadowOpacity = 0.1;
        self.bubbleView.layer.shadowRadius = 2;
        
        // 圆角设置 - 右上和右下圆角
        self.bubbleView.layer.maskedCorners = kCALayerMaxXMinYCorner | kCALayerMaxXMaxYCorner | kCALayerMinXMaxYCorner;
        
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
        
        self.bubbleView.frame = CGRectMake(margin + 40, 8, bubbleWidth, bubbleHeight);
        self.contentLabel.frame = CGRectMake(padding, padding, contentSize.width, contentSize.height);
        self.contentLabel.text = message.content;
    }
}

+ (CGFloat)heightForMessage:(AIChatMessage *)message width:(CGFloat)width {
    CGFloat margin = 15;
    CGFloat bubbleMargin = 50;
    CGFloat maxWidth = width - bubbleMargin - margin * 2 - 40;
    
    CGSize contentSize = [message.content boundingRectWithSize:CGSizeMake(maxWidth, CGFLOAT_MAX)
                                                       options:NSStringDrawingUsesLineFragmentOrigin
                                                    attributes:@{NSFontAttributeName: [UIFont systemFontOfSize:15]}
                                                       context:nil].size;
    contentSize.height = ceil(contentSize.height);
    
    return contentSize.height + 24 + 16; // padding + margin
}

@end

#pragma mark - Image Preview Cell

@interface AIChatImagePreviewCell : UICollectionViewCell
@property (nonatomic, strong) UIImageView *imageView;
@property (nonatomic, strong) UIButton *removeButton;
@property (nonatomic, copy) void (^onRemove)(void);
@end

@implementation AIChatImagePreviewCell

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        // Image view
        _imageView = [[UIImageView alloc] initWithFrame:CGRectMake(0, 0, 60, 60)];
        _imageView.layer.cornerRadius = 8;
        _imageView.clipsToBounds = YES;
        _imageView.contentMode = UIViewContentModeScaleAspectFill;
        [self.contentView addSubview:_imageView];
        
        // Remove button
        _removeButton = [UIButton buttonWithType:UIButtonTypeCustom];
        _removeButton.frame = CGRectMake(45, -6, 20, 20);
        _removeButton.layer.cornerRadius = 10;
        _removeButton.backgroundColor = [UIColor colorWithRed:255.0/255.0 green:68.0/255.0 blue:68.0/255.0 alpha:1.0];
        _removeButton.titleLabel.font = [UIFont systemFontOfSize:14];
        [_removeButton setTitle:@"×" forState:UIControlStateNormal];
        [_removeButton setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
        _removeButton.layer.borderWidth = 2;
        _removeButton.layer.borderColor = [UIColor whiteColor].CGColor;
        [_removeButton addTarget:self action:@selector(removeTapped) forControlEvents:UIControlEventTouchUpInside];
        [self.contentView addSubview:_removeButton];
    }
    return self;
}

- (void)removeTapped {
    if (self.onRemove) {
        self.onRemove();
    }
}

@end

#pragma mark - Input View (V2 Style)

@interface AIChatInputViewV2 : UIView
@property (nonatomic, strong) UIView *inputBoxView;
@property (nonatomic, strong) UIButton *modeSwitchButton;
@property (nonatomic, strong) UITextView *textView;
@property (nonatomic, strong) UIButton *voiceButton;
@property (nonatomic, strong) UIButton *galleryButton;
@property (nonatomic, strong) UIButton *sendButton;
@property (nonatomic, assign) BOOL isVoiceMode;
@property (nonatomic, copy) void (^onSendTap)(NSString *text);
@property (nonatomic, copy) void (^onVoiceLongPress)(UILongPressGestureRecognizer *gesture);
@property (nonatomic, copy) void (^onGalleryTap)(void);
@property (nonatomic, copy) void (^onModeSwitch)(void);
@end

@implementation AIChatInputViewV2

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        self.backgroundColor = [UIColor whiteColor];
        self.isVoiceMode = YES; // 默认语音模式
        
        // 顶部分割线
        UIView *topLine = [[UIView alloc] initWithFrame:CGRectMake(0, 0, frame.size.width, 0.5)];
        topLine.backgroundColor = [UIColor colorWithRed:229.0/255.0 green:229.0/255.0 blue:229.0/255.0 alpha:1.0];
        [self addSubview:topLine];
        
        // 输入框容器
        _inputBoxView = [[UIView alloc] initWithFrame:CGRectMake(10, 10, frame.size.width - 20, 44)];
        _inputBoxView.backgroundColor = kInputBoxColor;
        _inputBoxView.layer.cornerRadius = 22;
        _inputBoxView.layer.borderWidth = 1;
        _inputBoxView.layer.borderColor = kBorderColor.CGColor;
        [self addSubview:_inputBoxView];
        
        // 模式切换按钮（左侧）
        _modeSwitchButton = [UIButton buttonWithType:UIButtonTypeCustom];
        _modeSwitchButton.frame = CGRectMake(10, 6, 32, 32);
        [_modeSwitchButton setImage:[self keyboardIcon] forState:UIControlStateNormal];
        _modeSwitchButton.tintColor = [UIColor colorWithRed:153.0/255.0 green:153.0/255.0 blue:153.0/255.0 alpha:1.0];
        [_modeSwitchButton addTarget:self action:@selector(modeSwitchTapped) forControlEvents:UIControlEventTouchUpInside];
        [_inputBoxView addSubview:_modeSwitchButton];
        
        // 文本输入框
        _textView = [[UITextView alloc] initWithFrame:CGRectMake(50, 0, frame.size.width - 140, 44)];
        _textView.backgroundColor = [UIColor clearColor];
        _textView.font = [UIFont systemFontOfSize:16];
        _textView.textContainerInset = UIEdgeInsetsMake(11, 0, 11, 0);
        _textView.returnKeyType = UIReturnKeySend;
        _textView.enablesReturnKeyAutomatically = YES;
        _textView.hidden = YES;
        [_inputBoxView addSubview:_textView];
        
        // 语音按钮（长按）
        _voiceButton = [UIButton buttonWithType:UIButtonTypeCustom];
        _voiceButton.frame = CGRectMake(50, 0, frame.size.width - 140, 44);
        _voiceButton.backgroundColor = [UIColor clearColor];
        [_voiceButton setTitle:@"按住 说话" forState:UIControlStateNormal];
        [_voiceButton setTitleColor:[UIColor colorWithRed:51.0/255.0 green:51.0/255.0 blue:51.0/255.0 alpha:1.0] forState:UIControlStateNormal];
        _voiceButton.titleLabel.font = [UIFont systemFontOfSize:16 weight:UIFontWeightMedium];
        [_inputBoxView addSubview:_voiceButton];
        
        // 长按手势
        UILongPressGestureRecognizer *longPress = [[UILongPressGestureRecognizer alloc] initWithTarget:self action:@selector(voiceLongPress:)];
        longPress.minimumPressDuration = 0.3;
        [_voiceButton addGestureRecognizer:longPress];
        
        // 右侧按钮容器
        UIView *rightContainer = [[UIView alloc] initWithFrame:CGRectMake(frame.size.width - 90, 6, 70, 32)];
        [_inputBoxView addSubview:rightContainer];
        
        // 相册按钮
        _galleryButton = [UIButton buttonWithType:UIButtonTypeCustom];
        _galleryButton.frame = CGRectMake(0, 0, 32, 32);
        [_galleryButton setImage:[self galleryIcon] forState:UIControlStateNormal];
        _galleryButton.tintColor = [UIColor colorWithRed:153.0/255.0 green:153.0/255.0 blue:153.0/255.0 alpha:1.0];
        [_galleryButton addTarget:self action:@selector(galleryTapped) forControlEvents:UIControlEventTouchUpInside];
        [rightContainer addSubview:_galleryButton];
        
        // 发送按钮（初始隐藏）
        _sendButton = [UIButton buttonWithType:UIButtonTypeCustom];
        _sendButton.frame = CGRectMake(38, 0, 32, 32);
        [_sendButton setImage:[self sendIcon] forState:UIControlStateNormal];
        _sendButton.tintColor = kThemeColor;
        _sendButton.hidden = YES;
        [_sendButton addTarget:self action:@selector(sendTapped) forControlEvents:UIControlEventTouchUpInside];
        [rightContainer addSubview:_sendButton];
        
        // 添加聚焦效果
        [self addFocusAnimation];
    }
    return self;
}

- (void)addFocusAnimation {
    // 监听textView的聚焦状态
    [[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(textViewDidBeginEditing:) name:UITextViewTextDidBeginEditingNotification object:self.textView];
    [[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(textViewDidEndEditing:) name:UITextViewTextDidEndEditingNotification object:self.textView];
}

- (void)textViewDidBeginEditing:(NSNotification *)notification {
    [self startBorderGlowAnimation];
}

- (void)textViewDidEndEditing:(NSNotification *)notification {
    [self stopBorderGlowAnimation];
}

- (void)startBorderGlowAnimation {
    CABasicAnimation *animation = [CABasicAnimation animationWithKeyPath:@"borderColor"];
    animation.fromValue = (__bridge id)kThemeColor.CGColor;
    animation.toValue = (__bridge id)[UIColor colorWithRed:30.0/255.0 green:158.0/255.0 blue:143.0/255.0 alpha:1.0].CGColor;
    animation.duration = 1.0;
    animation.autoreverses = YES;
    animation.repeatCount = HUGE_VALF;
    [self.inputBoxView.layer addAnimation:animation forKey:@"borderGlow"];
    
    self.inputBoxView.layer.borderColor = kThemeColor.CGColor;
    self.inputBoxView.layer.shadowColor = kThemeColor.CGColor;
    self.inputBoxView.layer.shadowOffset = CGSizeMake(0, 0);
    self.inputBoxView.layer.shadowRadius = 5;
    self.inputBoxView.layer.shadowOpacity = 0.3;
}

- (void)stopBorderGlowAnimation {
    [self.inputBoxView.layer removeAnimationForKey:@"borderGlow"];
    self.inputBoxView.layer.borderColor = kBorderColor.CGColor;
    self.inputBoxView.layer.shadowOpacity = 0;
}

- (void)modeSwitchTapped {
    self.isVoiceMode = !self.isVoiceMode;
    
    if (self.isVoiceMode) {
        // 切换到语音模式
        [self.modeSwitchButton setImage:[self keyboardIcon] forState:UIControlStateNormal];
        self.textView.hidden = YES;
        self.voiceButton.hidden = NO;
        self.sendButton.hidden = YES;
        [self.textView resignFirstResponder];
    } else {
        // 切换到文本模式
        [self.modeSwitchButton setImage:[self microphoneIcon] forState:UIControlStateNormal];
        self.textView.hidden = NO;
        self.voiceButton.hidden = YES;
        self.sendButton.hidden = NO;
        [self.textView becomeFirstResponder];
    }
    
    if (self.onModeSwitch) {
        self.onModeSwitch();
    }
}

- (void)sendTapped {
    NSString *text = self.textView.text;
    if (text.length > 0 && self.onSendTap) {
        self.onSendTap(text);
        self.textView.text = @"";
    }
}

- (void)galleryTapped {
    if (self.onGalleryTap) {
        self.onGalleryTap();
    }
}

- (void)voiceLongPress:(UILongPressGestureRecognizer *)gesture {
    if (self.onVoiceLongPress) {
        self.onVoiceLongPress(gesture);
    }
}

#pragma mark - Icons

- (UIImage *)keyboardIcon {
    // 简单的键盘图标绘制
    UIGraphicsBeginImageContextWithOptions(CGSizeMake(24, 24), NO, 0);
    CGContextRef context = UIGraphicsGetCurrentContext();
    
    [[UIColor grayColor] setStroke];
    CGContextSetLineWidth(context, 1.5);
    
    // 外框
    CGRect rect = CGRectMake(2, 5, 20, 14);
    CGContextStrokeRectWithWidth(context, rect, 1.5);
    
    // 横线
    CGContextMoveToPoint(context, 5, 9);
    CGContextAddLineToPoint(context, 19, 9);
    CGContextStrokePath(context);
    
    CGContextMoveToPoint(context, 5, 13);
    CGContextAddLineToPoint(context, 19, 13);
    CGContextStrokePath(context);
    
    UIImage *image = UIGraphicsGetImageFromCurrentImageContext();
    UIGraphicsEndImageContext();
    return [image imageWithRenderingMode:UIImageRenderingModeAlwaysTemplate];
}

- (UIImage *)microphoneIcon {
    UIGraphicsBeginImageContextWithOptions(CGSizeMake(24, 24), NO, 0);
    CGContextRef context = UIGraphicsGetCurrentContext();
    
    [[UIColor grayColor] setStroke];
    CGContextSetLineWidth(context, 1.5);
    
    // 麦克风主体
    CGRect rect = CGRectMake(8, 3, 8, 10);
    CGContextStrokeRectWithWidth(context, rect, 1.5);
    
    // 弧线
    CGContextMoveToPoint(context, 5, 10);
    CGContextAddQuadCurveToPoint(context, 5, 16, 12, 16);
    CGContextAddQuadCurveToPoint(context, 19, 16, 19, 10);
    CGContextStrokePath(context);
    
    // 竖线
    CGContextMoveToPoint(context, 12, 16);
    CGContextAddLineToPoint(context, 12, 21);
    CGContextStrokePath(context);
    
    UIImage *image = UIGraphicsGetImageFromCurrentImageContext();
    UIGraphicsEndImageContext();
    return [image imageWithRenderingMode:UIImageRenderingModeAlwaysTemplate];
}

- (UIImage *)galleryIcon {
    UIGraphicsBeginImageContextWithOptions(CGSizeMake(24, 24), NO, 0);
    CGContextRef context = UIGraphicsGetCurrentContext();
    
    [[UIColor grayColor] setStroke];
    CGContextSetLineWidth(context, 1.5);
    
    // 外框
    CGRect rect = CGRectMake(3, 6, 18, 14);
    CGContextStrokeRectWithWidth(context, rect, 1.5);
    
    // 圆
    CGRect circle = CGRectMake(9, 10, 6, 6);
    CGContextStrokeEllipseInRect(context, circle);
    
    UIImage *image = UIGraphicsGetImageFromCurrentImageContext();
    UIGraphicsEndImageContext();
    return [image imageWithRenderingMode:UIImageRenderingModeAlwaysTemplate];
}

- (UIImage *)sendIcon {
    UIGraphicsBeginImageContextWithOptions(CGSizeMake(24, 24), NO, 0);
    CGContextRef context = UIGraphicsGetCurrentContext();
    
    [kThemeColor setStroke];
    CGContextSetLineWidth(context, 1.5);
    
    // 纸飞机
    CGContextMoveToPoint(context, 3, 12);
    CGContextAddLineToPoint(context, 21, 3);
    CGContextAddLineToPoint(context, 14, 21);
    CGContextAddLineToPoint(context, 11, 14);
    CGContextAddLineToPoint(context, 3, 12);
    CGContextStrokePath(context);
    
    UIImage *image = UIGraphicsGetImageFromCurrentImageContext();
    UIGraphicsEndImageContext();
    return [image imageWithRenderingMode:UIImageRenderingModeAlwaysTemplate];
}

@end

#pragma mark - Voice Recording View

@interface AIChatVoiceRecordingView : UIView
@property (nonatomic, strong) UILabel *micLabel;
@property (nonatomic, strong) UILabel *statusLabel;
@property (nonatomic, strong) UILabel *tipLabel;
@property (nonatomic, strong) UIView *pulseView;
@end

@implementation AIChatVoiceRecordingView

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        self.backgroundColor = [UIColor colorWithWhite:0 alpha:0.8];
        self.layer.cornerRadius = 10;
        self.hidden = YES;
        
        // 麦克风图标
        _micLabel = [[UILabel alloc] initWithFrame:CGRectMake(0, 30, 150, 40)];
        _micLabel.text = @"🎤";
        _micLabel.font = [UIFont systemFontOfSize:40];
        _micLabel.textAlignment = NSTextAlignmentCenter;
        [self addSubview:_micLabel];
        
        // 脉冲动画视图
        _pulseView = [[UIView alloc] initWithFrame:CGRectMake(65, 35, 20, 20)];
        _pulseView.backgroundColor = kThemeColor;
        _pulseView.layer.cornerRadius = 10;
        _pulseView.alpha = 0.3;
        [self addSubview:_pulseView];
        
        // 状态文字
        _statusLabel = [[UILabel alloc] initWithFrame:CGRectMake(0, 80, 150, 20)];
        _statusLabel.text = @"正在录音...";
        _statusLabel.textColor = [UIColor whiteColor];
        _statusLabel.textAlignment = NSTextAlignmentCenter;
        _statusLabel.font = [UIFont systemFontOfSize:14];
        [self addSubview:_statusLabel];
        
        // 提示文字
        _tipLabel = [[UILabel alloc] initWithFrame:CGRectMake(0, 110, 150, 20)];
        _tipLabel.text = @"松开发送，上滑取消";
        _tipLabel.textColor = [UIColor lightGrayColor];
        _tipLabel.textAlignment = NSTextAlignmentCenter;
        _tipLabel.font = [UIFont systemFontOfSize:12];
        [self addSubview:_tipLabel];
    }
    return self;
}

- (void)startRecordingAnimation {
    self.hidden = NO;
    
    // 脉冲动画
    CABasicAnimation *pulse = [CABasicAnimation animationWithKeyPath:@"transform.scale"];
    pulse.fromValue = @1;
    pulse.toValue = @1.5;
    pulse.duration = 1.0;
    pulse.autoreverses = YES;
    pulse.repeatCount = HUGE_VALF;
    [self.pulseView.layer addAnimation:pulse forKey:@"pulse"];
    
    // 透明度动画
    CABasicAnimation *fade = [CABasicAnimation animationWithKeyPath:@"opacity"];
    fade.fromValue = @0.3;
    fade.toValue = @0.6;
    fade.duration = 1.0;
    fade.autoreverses = YES;
    fade.repeatCount = HUGE_VALF;
    [self.pulseView.layer addAnimation:fade forKey:@"fade"];
}

- (void)stopRecordingAnimation {
    [self.pulseView.layer removeAllAnimations];
    self.hidden = YES;
}

- (void)setCancelled:(BOOL)cancelled {
    if (cancelled) {
        self.statusLabel.text = @"松开取消";
        self.statusLabel.textColor = [UIColor colorWithRed:255.0/255.0 green:68.0/255.0 blue:68.0/255.0 alpha:1.0];
    } else {
        self.statusLabel.text = @"正在录音...";
        self.statusLabel.textColor = [UIColor whiteColor];
    }
}

@end

#pragma mark - AIChatViewControllerV2 Implementation

@interface AIChatViewControllerV2 () <UITableViewDelegate, UITableViewDataSource, UITextViewDelegate, AIChatServiceDelegate, UIImagePickerControllerDelegate, UINavigationControllerDelegate, UICollectionViewDelegate, UICollectionViewDataSource>
@property (nonatomic, strong) AIChatConfig *config;
@property (nonatomic, strong, readwrite) AIChatService *chatService;
@property (nonatomic, strong) UITableView *tableView;
@property (nonatomic, strong) AIChatInputViewV2 *inputView;
@property (nonatomic, strong) NSMutableArray<AIChatMessage *> *messages;
@property (nonatomic, strong) NSMutableArray<UIImage *> *selectedImages;
@property (nonatomic, strong) NSMutableArray<NSString *> *selectedImageIds;
@property (nonatomic, strong) UICollectionView *imagePreviewCollectionView;
@property (nonatomic, strong) UIView *imagePreviewArea;
@property (nonatomic, strong) AIChatVoiceRecordingView *voiceRecordingView;
@property (nonatomic, strong) AVAudioRecorder *audioRecorder;
@property (nonatomic, strong) NSURL *audioRecordingURL;
@property (nonatomic, assign) BOOL isRecording;
@end

@implementation AIChatViewControllerV2

- (instancetype)initWithConfig:(AIChatConfig *)config accessToken:(NSString *)accessToken {
    self = [super init];
    if (self) {
        _config = config;
        _chatService = [[AIChatService alloc] initWithBaseURL:config.baseURL accessToken:accessToken];
        _chatService.delegate = self;
        _messages = [NSMutableArray array];
        _selectedImages = [NSMutableArray array];
        _selectedImageIds = [NSMutableArray array];
    }
    return self;
}

- (instancetype)initWithAccessToken:(NSString *)accessToken {
    return [self initWithConfig:[AIChatConfig defaultConfig] accessToken:accessToken];
}

- (void)viewDidLoad {
    [super viewDidLoad];
    
    self.view.backgroundColor = kBackgroundColor;
    
    // 设置导航栏
    self.title = self.config.title;
    self.navigationController.navigationBar.barTintColor = [UIColor whiteColor];
    
    // 返回按钮
    UIBarButtonItem *backItem = [[UIBarButtonItem alloc] initWithTitle:@"返回"
                                                                  style:UIBarButtonItemStylePlain
                                                                 target:self
                                                                 action:@selector(backTapped)];
    self.navigationItem.leftBarButtonItem = backItem;
    
    // 创建消息列表
    [self setupTableView];
    
    // 创建图片预览区域
    [self setupImagePreviewArea];
    
    // 创建输入框
    [self setupInputView];
    
    // 创建录音状态视图
    [self setupVoiceRecordingView];
    
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

- (void)setupImagePreviewArea {
    // 图片预览区域 (在输入区域上方)
    self.imagePreviewArea = [[UIView alloc] initWithFrame:CGRectMake(0, self.view.bounds.size.height - 110, self.view.bounds.size.width, 0)];
    self.imagePreviewArea.backgroundColor = [UIColor whiteColor];
    self.imagePreviewArea.clipsToBounds = YES;
    [self.view addSubview:self.imagePreviewArea];
    
    // Collection view layout
    UICollectionViewFlowLayout *layout = [[UICollectionViewFlowLayout alloc] init];
    layout.scrollDirection = UICollectionViewScrollDirectionHorizontal;
    layout.itemSize = CGSizeMake(60, 60);
    layout.minimumInteritemSpacing = 8;
    layout.sectionInset = UIEdgeInsetsMake(8, 10, 8, 10);
    
    self.imagePreviewCollectionView = [[UICollectionView alloc] initWithFrame:self.imagePreviewArea.bounds collectionViewLayout:layout];
    self.imagePreviewCollectionView.backgroundColor = [UIColor whiteColor];
    self.imagePreviewCollectionView.delegate = self;
    self.imagePreviewCollectionView.dataSource = self;
    [self.imagePreviewCollectionView registerClass:[AIChatImagePreviewCell class] forCellWithReuseIdentifier:@"ImageCell"];
    [self.imagePreviewArea addSubview:self.imagePreviewCollectionView];
}

- (void)setupInputView {
    CGFloat bottomSafeArea = 0;
    if (@available(iOS 11.0, *)) {
        bottomSafeArea = self.view.safeAreaInsets.bottom;
    }
    
    self.inputView = [[AIChatInputViewV2 alloc] initWithFrame:CGRectMake(0, self.view.bounds.size.height - 60 - bottomSafeArea, self.view.bounds.size.width, 60)];
    
    __weak typeof(self) weakSelf = self;
    self.inputView.onSendTap = ^(NSString *text) {
        [weakSelf sendTextMessage:text];
    };
    
    self.inputView.onVoiceLongPress = ^(UILongPressGestureRecognizer *gesture) {
        [weakSelf handleVoiceLongPress:gesture];
    };
    
    self.inputView.onGalleryTap = ^{
        [weakSelf selectImage];
    };
    
    [self.view addSubview:self.inputView];
}

- (void)setupVoiceRecordingView {
    self.voiceRecordingView = [[AIChatVoiceRecordingView alloc] initWithFrame:CGRectMake(0, 0, 150, 150)];
    self.voiceRecordingView.center = self.view.center;
    [self.view addSubview:self.voiceRecordingView];
}

- (void)updateImagePreviewArea {
    CGFloat bottomSafeArea = 0;
    if (@available(iOS 11.0, *)) {
        bottomSafeArea = self.view.safeAreaInsets.bottom;
    }
    
    if (self.selectedImages.count == 0) {
        // 隐藏预览区域
        self.imagePreviewArea.frame = CGRectMake(0, self.view.bounds.size.height - 60 - bottomSafeArea, self.view.bounds.size.width, 0);
        self.inputView.frame = CGRectMake(0, self.view.bounds.size.height - 60 - bottomSafeArea, self.view.bounds.size.width, 60);
        self.tableView.frame = CGRectMake(0, 0, self.view.bounds.size.width, self.view.bounds.size.height - 60 - bottomSafeArea);
    } else {
        // 显示预览区域
        CGFloat previewHeight = 76;
        self.imagePreviewArea.frame = CGRectMake(0, self.view.bounds.size.height - 60 - previewHeight - bottomSafeArea, self.view.bounds.size.width, previewHeight);
        self.imagePreviewCollectionView.frame = self.imagePreviewArea.bounds;
        self.inputView.frame = CGRectMake(0, self.view.bounds.size.height - 60 - bottomSafeArea, self.view.bounds.size.width, 60);
        self.tableView.frame = CGRectMake(0, 0, self.view.bounds.size.width, self.view.bounds.size.height - 60 - previewHeight - bottomSafeArea);
    }
    
    [self.imagePreviewCollectionView reloadData];
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
    if (text.length == 0 && self.selectedImages.count == 0) return;
    
    // 添加用户消息
    AIChatMessage *userMessage = [[AIChatMessage alloc] initWithRole:AIChatMessageRoleUser type:AIChatMessageTypeText content:text];
    userMessage.imageURLs = [self.selectedImageIds copy];
    [self.messages addObject:userMessage];
    [self.tableView reloadData];
    [self scrollToBottom];
    
    // 清空输入和图片
    self.inputView.textView.text = @"";
    [self.selectedImages removeAllObjects];
    [self.selectedImageIds removeAllObjects];
    [self updateImagePreviewArea];
    
    // 收起键盘
    [self.inputView.textView resignFirstResponder];
    
    // 发送到服务器
    NSMutableArray *imageURLs = [NSMutableArray array];
    for (NSString *imageId in userMessage.imageURLs) {
        [imageURLs addObject:[NSString stringWithFormat:@"https://gj.wojiacloud.com/api/file/%@", imageId]];
    }
    
    [self.chatService sendMessage:text imageURLs:imageURLs completion:^(BOOL success, AIChatMessage * _Nullable message, NSError * _Nullable error) {
        if (success && message) {
            [self.messages addObject:message];
            [self.tableView reloadData];
            [self scrollToBottom];
        }
    }];
}

- (void)handleVoiceLongPress:(UILongPressGestureRecognizer *)gesture {
    CGPoint location = [gesture locationInView:self.view];
    BOOL isCancelled = location.y < self.view.center.y - 50;
    
    switch (gesture.state) {
        case UIGestureRecognizerStateBegan:
            [self startRecording];
            break;
        case UIGestureRecognizerStateChanged:
            [self.voiceRecordingView setCancelled:isCancelled];
            break;
        case UIGestureRecognizerStateEnded:
        case UIGestureRecognizerStateCancelled:
            [self stopRecording:isCancelled];
            break;
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
    
    [self.voiceRecordingView startRecordingAnimation];
}

- (void)stopRecording:(BOOL)cancelled {
    if (!self.isRecording) return;
    
    [self.audioRecorder stop];
    self.isRecording = NO;
    [self.voiceRecordingView stopRecordingAnimation];
    
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
    picker.allowsEditing = NO;
    [self presentViewController:picker animated:YES completion:nil];
}

#pragma mark - UIImagePickerControllerDelegate

- (void)imagePickerController:(UIImagePickerController *)picker didFinishPickingMediaWithInfo:(NSDictionary<UIImagePickerControllerInfoKey,id> *)info {
    [picker dismissViewControllerAnimated:YES completion:nil];
    
    UIImage *image = info[UIImagePickerControllerOriginalImage];
    if (image) {
        [self.selectedImages addObject:image];
        
        // 上传图片
        [self.chatService uploadImage:image completion:^(BOOL success, NSString * _Nullable imageId, NSError * _Nullable error) {
            if (success && imageId) {
                [self.selectedImageIds addObject:imageId];
                [self updateImagePreviewArea];
            } else {
                [self.selectedImages removeLastObject];
                NSLog(@"图片上传失败: %@", error.localizedDescription);
            }
        }];
        
        [self updateImagePreviewArea];
    }
}

#pragma mark - UICollectionViewDataSource

- (NSInteger)collectionView:(UICollectionView *)collectionView numberOfItemsInSection:(NSInteger)section {
    return self.selectedImages.count;
}

- (UICollectionViewCell *)collectionView:(UICollectionView *)collectionView cellForItemAtIndexPath:(NSIndexPath *)indexPath {
    AIChatImagePreviewCell *cell = [collectionView dequeueReusableCellWithReuseIdentifier:@"ImageCell" forIndexPath:indexPath];
    cell.imageView.image = self.selectedImages[indexPath.item];
    
    __weak typeof(self) weakSelf = self;
    cell.onRemove = ^{
        [weakSelf removeImageAtIndex:indexPath.item];
    };
    
    return cell;
}

- (void)removeImageAtIndex:(NSInteger)index {
    if (index < self.selectedImages.count) {
        [self.selectedImages removeObjectAtIndex:index];
        [self.selectedImageIds removeObjectAtIndex:index];
        [self updateImagePreviewArea];
    }
}

#pragma mark - UITableViewDataSource

- (NSInteger)tableView:(UITableView *)tableView numberOfRowsInSection:(NSInteger)section {
    return self.messages.count;
}

- (UITableViewCell *)tableView:(UITableView *)tableView cellForRowAtIndexPath:(NSIndexPath *)indexPath {
    static NSString *cellId = @"MessageCellV2";
    AIChatMessageCellV2 *cell = [tableView dequeueReusableCellWithIdentifier:cellId];
    if (!cell) {
        cell = [[AIChatMessageCellV2 alloc] initWithStyle:UITableViewCellStyleDefault reuseIdentifier:cellId];
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
    CGFloat bottomSafeArea = 0;
    if (@available(iOS 11.0, *)) {
        bottomSafeArea = self.view.safeAreaInsets.bottom;
    }
    
    CGFloat previewHeight = self.selectedImages.count > 0 ? 76 : 0;
    
    [UIView animateWithDuration:0.3 animations:^{
        self.inputView.frame = CGRectMake(0, self.view.bounds.size.height - 60 - keyboardHeight, self.view.bounds.size.width, 60);
        self.imagePreviewArea.frame = CGRectMake(0, self.view.bounds.size.height - 60 - previewHeight - keyboardHeight, self.view.bounds.size.width, previewHeight);
        self.tableView.frame = CGRectMake(0, 0, self.view.bounds.size.width, self.view.bounds.size.height - 60 - previewHeight - keyboardHeight);
    }];
    
    [self scrollToBottom];
}

- (void)keyboardWillHide:(NSNotification *)notification {
    CGFloat bottomSafeArea = 0;
    if (@available(iOS 11.0, *)) {
        bottomSafeArea = self.view.safeAreaInsets.bottom;
    }
    
    CGFloat previewHeight = self.selectedImages.count > 0 ? 76 : 0;
    
    [UIView animateWithDuration:0.3 animations:^{
        self.inputView.frame = CGRectMake(0, self.view.bounds.size.height - 60 - bottomSafeArea, self.view.bounds.size.width, 60);
        self.imagePreviewArea.frame = CGRectMake(0, self.view.bounds.size.height - 60 - previewHeight - bottomSafeArea, self.view.bounds.size.width, previewHeight);
        self.tableView.frame = CGRectMake(0, 0, self.view.bounds.size.width, self.view.bounds.size.height - 60 - previewHeight - bottomSafeArea);
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
    [self.selectedImages removeAllObjects];
    [self.selectedImageIds removeAllObjects];
    [self.tableView reloadData];
    [self updateImagePreviewArea];
    [self addWelcomeMessage];
}

- (void)dealloc {
    [[NSNotificationCenter defaultCenter] removeObserver:self];
}

@end
