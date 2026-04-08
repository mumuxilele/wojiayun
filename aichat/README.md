# AI Chat 页面说明

本项目提供两种架构的 AI 聊天页面，功能完全一致。

## 📄 页面版本

### 1. HTML 版本（原生实现）
- **文件**: `aichat/index.html`
- **技术栈**: 原生 HTML + JavaScript + CSS
- **访问地址**: `http://47.98.238.209:22314/?access_token=xxx`

### 2. React 版本（组件化实现）
- **文件**: `aichat/react-index.html`
- **技术栈**: React 18 + TypeScript
- **访问地址**: `http://47.98.238.209:22314/react-index.html?access_token=xxx`

## ✨ 功能特性

两个版本都支持以下功能：

- ✅ **长按语音输入** - 使用 Web Speech API
- ✅ **SSE 流式响应** - 实时展示 AI 回复
- ✅ **Markdown 渲染** - 支持 GFM 语法
- ✅ **代码高亮** - 使用 highlight.js
- ✅ **custom_variables** - 传递用户信息到后端
- ✅ **用户信息获取** - 自动获取并传递用户信息

## 🚀 使用方式

### HTML 版本
```
http://47.98.238.209:22314/?access_token=YOUR_TOKEN
```

### React 版本
```
http://47.98.238.209:22314/react-index.html?access_token=YOUR_TOKEN
```

## 📦 React SDK

除了独立页面，还提供了可集成的 React SDK：

```bash
npm install @wojiayun/aichat-sdk
```

```tsx
import { ChatContainer } from '@wojiayun/aichat-sdk';
import '@wojiayun/aichat-sdk/dist/styles.css';

const config = {
  accessToken: 'your-token',
  apiUrl: '/api',
  enableVoice: true,
  customVariables: { empName: '张三' }
};

<ChatContainer config={config} />
```

## 🔧 技术对比

| 特性 | HTML 版本 | React 版本 | React SDK |
|------|-----------|-----------|-----------|
| 文件 | index.html | react-index.html | aichat-sdk/ |
| 技术栈 | 原生 JS | React 18 | React + TS |
| 使用方式 | 直接访问 | 直接访问 | NPM 包 |
| 组件化 | ❌ | ✅ | ✅ |
| TypeScript | ❌ | ❌ | ✅ |
| 可复用性 | 低 | 中 | 高 |
| 适合场景 | 快速集成 | 独立应用 | 项目集成 |

## 📝 开发说明

### 本地开发
```bash
cd aichat
node server.js
```

访问：
- HTML 版本：http://localhost:22314/?access_token=xxx
- React 版本：http://localhost:22314/react-index.html?access_token=xxx

### 构建 SDK
```bash
cd aichat-sdk
npm install
npm run build
```

## 🎯 选择建议

- **快速集成** → 使用 HTML 版本
- **独立应用** → 使用 React 版本
- **项目集成** → 使用 React SDK
