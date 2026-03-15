#!/usr/bin/env python3
"""
Cookie Browser Loader
使用配置文件中的Cookie打开浏览器并加载指定网页
"""
import json
import os
import sys
import argparse

# Cookie配置文件路径
COOKIE_CONFIG = os.path.join(os.path.dirname(__file__), 'cookies.json')
COOKIE_CONFIG_example = os.path.join(os.path.dirname(__file__), 'cookies.example.json')

def load_cookies(config_file):
    """加载Cookie配置"""
    if not os.path.exists(config_file):
        print(f"错误: 配置文件 {config_file} 不存在!")
        print(f"请复制 {COOKIE_CONFIG_example} 为 {COOKIE_CONFIG} 并填入您的Cookie")
        sys.exit(1)
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config

def get_chrome_driver():
    """获取Chrome驱动"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        # chrome_options.add_argument('--headless')  # 无头模式
        
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Chrome驱动初始化失败: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Cookie浏览器加载器')
    parser.add_argument('url', help='要加载的网页URL')
    parser.add_argument('--config', '-c', default=COOKIE_CONFIG, help='Cookie配置文件路径')
    parser.add_argument('--example', '-e', action='store_true', help='生成示例配置文件')
    
    args = parser.parse_args()
    
    # 生成示例配置
    if args.example:
        example_config = {
            "url": "https://example.com",
            "cookies": [
                {"name": "session_id", "value": "abc123", "domain": ".example.com", "path": "/"},
                {"name": "user_token", "value": "xyz789", "domain": ".example.com", "path": "/"}
            ]
        }
        with open(COOKIE_CONFIG_example, 'w', encoding='utf-8') as f:
            json.dump(example_config, f, indent=2, ensure_ascii=False)
        print(f"示例配置已生成: {COOKIE_CONFIG_example}")
        return
    
    # 加载配置
    config = load_cookies(args.config)
    
    print(f"正在打开浏览器...")
    driver = get_chrome_driver()
    
    if not driver:
        print("无法启动浏览器，请安装Chrome和selenium")
        sys.exit(1)
    
    try:
        # 先访问域名设置Cookie
        base_url = config.get('url', '')
        if base_url:
            print(f"先访问: {base_url}")
            driver.get(base_url)
        
        # 添加Cookie
        print(f"正在添加 {len(config.get('cookies', []))} 个Cookie...")
        for cookie in config.get('cookies', []):
            # 移除 Selenium 不支持的字段
            cookie_copy = {k: v for k, v in cookie.items() if k in ['name', 'value', 'domain', 'path', 'secure', 'httpOnly', 'expiry']}
            try:
                driver.add_cookie(cookie_copy)
                print(f"  ✓ 添加Cookie: {cookie.get('name')}")
            except Exception as e:
                print(f"  ✗ 添加Cookie失败: {cookie.get('name')} - {e}")
        
        # 访问目标URL
        print(f"正在加载: {args.url}")
        driver.get(args.url)
        
        print("加载完成! 浏览器将保持打开状态...")
        input("按回车键关闭浏览器...")
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"错误: {e}")
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
