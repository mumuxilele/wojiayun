# AI Chat SDK

一个基于 React 的 AI 聊天 SDK，支持语音输入和流式响应。

## 特性

- 🎯 **开箱即用** - 简单的配置即可集成
- 🎤 **语音输入** - 支持长按语音按钮进行语音识别
- 📡 **流式响应** - 支持 SSE 流式消息展示
- 🎨 **主题定制** - 支持亮色/暗色主题
- 📱 **响应式设计** - 适配移动端和桌面端
- 🔧 **TypeScript** - 完整的类型定义

## 安装

```bash
npm install @wojiayun/aichat-sdk
# 或
yarn add @wojiayun/aichat-sdk
```

## 快速开始

### 基础用法

```tsx
import React from 'react';
import { ChatContainer, ChatConfig } from '@wojiayun/aichat-sdk';
import '@wojiayun/aichat-sdk/dist/styles.css';

const config: ChatConfig = {
  accessToken: 'your-access-token',
  apiUrl: '/api', // API 基础路径
  enableVoice: true, // 启用语音输入
  placeholder: '输入消息...',
  welcomeMessage: '你好！有什么可以帮助你的吗？',
  theme: 'light', // 'light' 或 'dark'
};

function App() {
  return (
    <div style={{ height: '600px' }}>
      <ChatContainer config={config} />
    </div>
  );
}

export default App;
```

### 自定义配置

```tsx
const config: ChatConfig = {
  accessToken: 'your-access-token',
  apiUrl: '/api',
  
  // 自定义变量（传递给后端）
  customVariables: {
    empName: '张三',
    empId: '12345',
  },
  
  // 回调函数
  onMessage: (message) => {
    console.log('New message:', message);
  },
  
  onError: (error) => {
    console.error('Error:', error);
  },
  
  // UI 配置
  enableVoice: true,
  placeholder: '输入消息或长按语音按钮...',
  welcomeMessage: '👋 你好！我是 AI 助手',
  theme: 'light',
};
```

## 组件

### ChatContainer

主容器组件，包含完整的聊天功能。

```tsx
import { ChatContainer } from '@wojiayun/aichat-sdk';

<ChatContainer config={config} className="my-chat" />
```

### MessageList

消息列表组件，用于展示聊天记录。

```tsx
import { MessageList } from '@wojiayun/aichat-sdk';

<MessageList messages={messages} className="my-message-list" />
```

### InputArea

输入区域组件，包含文本输入和语音按钮。

```tsx
import { InputArea } from '@wojiayun/aichat-sdk';

<InputArea
  onSend={(message) => console.log(message)}
  disabled={false}
  placeholder="输入消息..."
  enableVoice={true}
/>
```

### VoiceButton

语音按钮组件，支持长按录音。

```tsx
import { VoiceButton } from '@wojiayun/aichat-sdk';

<VoiceButton
  onResult={(text) => console.log('识别结果:', text)}
  disabled={false}
/>
```

## Hooks

### useChat

聊天状态管理 Hook。

```tsx
import { useChat } from '@wojiayun/aichat-sdk';

function MyChat() {
  const {
    messages,      // 消息列表
    isStreaming,   // 是否正在流式响应
    error,         // 错误信息
    visitorId,     // 访客 ID
    sendMessage,   // 发送消息函数
    clearMessages, // 清空消息函数
  } = useChat(config);

  return (
    // ...
  );
}
```

## API

### ChatConfig

| 属性 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| accessToken | string | ✅ | - | 访问令牌 |
| apiUrl | string | ❌ | '/api' | API 基础路径 |
| customVariables | Record<string, string> | ❌ | - | 自定义变量 |
| enableVoice | boolean | ❌ | true | 是否启用语音输入 |
| placeholder | string | ❌ | '输入消息...' | 输入框占位符 |
| welcomeMessage | string | ❌ | - | 欢迎消息 |
| theme | 'light' \| 'dark' | ❌ | 'light' | 主题 |
| onMessage | (message: Message) => void | ❌ | - | 消息回调 |
| onError | (error: Error) => void | ❌ | - | 错误回调 |

### Message

| 属性 | 类型 | 说明 |
|------|------|------|
| id | string | 消息 ID |
| role | 'user' \| 'assistant' \| 'system' | 消息角色 |
| content | string | 消息内容 |
| timestamp | string | 时间戳 |
| references | Reference[] | 参考资料 |
| optionCards | string[] | 选项卡片 |
| isStreaming | boolean | 是否正在流式响应 |

## 开发

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

### 构建

```bash
npm run build
```

### 类型检查

```bash
npm run type-check
```

## 浏览器支持

- Chrome >= 60
- Firefox >= 55
- Safari >= 11
- Edge >= 79

语音识别功能依赖浏览器的 Web Speech API 支持。

## License

MIT
