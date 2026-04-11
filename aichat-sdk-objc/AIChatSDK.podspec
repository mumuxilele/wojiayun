Pod::Spec.new do |s|
  s.name         = "AIChatSDK"
  s.version      = "1.0.0"
  s.summary      = "AI Chat SDK for iOS - Objective-C"
  s.description  = "A powerful AI Chat SDK with voice input support for iOS applications"
  s.homepage     = "https://github.com/wojiayun/aichat-sdk"
  s.license      = "MIT"
  s.author       = { "wojiayun" => "dev@wojiayun.com" }
  s.platform     = :ios, "11.0"
  s.source       = { :git => "https://github.com/wojiayun/aichat-sdk.git", :tag => "#{s.version}" }
  
  s.source_files = "AIChatSDK/**/*.{h,m}"
  s.resources    = "AIChatSDK/**/*.{html,css,js,json}"
  
  s.frameworks = "UIKit", "WebKit", "Speech", "AVFoundation"
  
  s.dependency "AFNetworking", "~> 4.0"
end
