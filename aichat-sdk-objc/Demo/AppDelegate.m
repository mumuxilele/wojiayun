//
//  AppDelegate.m
//  AIChatSDKDemo
//
//  Created by wojiacloud on 2026/04/08.
//

#import "AppDelegate.h"
#import "HomeViewController.h"

@interface AppDelegate ()

@end

@implementation AppDelegate

- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {
    
    // 创建主视图控制器
    HomeViewController *homeVC = [[HomeViewController alloc] init];
    
    // 创建导航控制器
    UINavigationController *navController = [[UINavigationController alloc] initWithRootViewController:homeVC];
    
    // 设置导航栏外观
    if (@available(iOS 13.0, *)) {
        UINavigationBarAppearance *appearance = [[UINavigationBarAppearance alloc] init];
        [appearance configureWithOpaqueBackground];
        appearance.backgroundColor = [UIColor systemBlueColor];
        appearance.titleTextAttributes = @{NSForegroundColorAttributeName: [UIColor whiteColor]};
        
        navController.navigationBar.standardAppearance = appearance;
        navController.navigationBar.scrollEdgeAppearance = appearance;
        navController.navigationBar.tintColor = [UIColor whiteColor];
    } else {
        navController.navigationBar.barTintColor = [UIColor systemBlueColor];
        navController.navigationBar.tintColor = [UIColor whiteColor];
        navController.navigationBar.titleTextAttributes = @{NSForegroundColorAttributeName: [UIColor whiteColor]};
    }
    
    // 设置为根视图
    self.window = [[UIWindow alloc] initWithFrame:[UIScreen mainScreen].bounds];
    self.window.rootViewController = navController;
    [self.window makeKeyAndVisible];
    
    return YES;
}

@end