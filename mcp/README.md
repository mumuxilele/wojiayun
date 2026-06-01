# Wojiayun MCP Server

一个标准的 MCP (Model Context Protocol) 服务实现。

## 功能特性

### Tools (工具)

| 工具名称 | 描述 |
|---------|------|
| `get_server_status` | 获取服务器运行状态 |
| `calculate` | 执行数学计算 |
| `process_text` | 文本处理（大小写转换、字数统计、反转） |

### Resources (资源)

| 资源 URI | 描述 |
|----------|------|
| `config://server` | 服务器配置信息 |
| `info://system` | 系统运行信息 |

### Prompts (提示词)

| 提示词名称 | 描述 |
|-----------|------|
| `code_review` | 代码审查提示词 |
| `generate_docs` | 文档生成提示词 |

## 安装

```bash
cd mcp
npm install
```

## 使用方式

### 1. 作为 stdio 服务运行

```bash
npm start
```

### 2. 在 Claude Desktop 中配置

编辑 Claude Desktop 配置文件：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "wojiayun": {
      "command": "node",
      "args": ["/path/to/wojiayun/mcp/index.js"]
    }
  }
}
```

### 3. 在 WorkBuddy 中配置

在 `~/.workbuddy/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "wojiayun": {
      "command": "node",
      "args": ["/path/to/wojiayun/mcp/index.js"]
    }
  }
}
```

## API 示例

### 调用工具

```javascript
// 获取服务器状态
const status = await mcp.callTool("get_server_status", {});

// 执行计算
const result = await mcp.callTool("calculate", {
  expression: "2 + 2 * 3"
});

// 处理文本
const textResult = await mcp.callTool("process_text", {
  text: "Hello World",
  operation: "uppercase"
});
```

### 读取资源

```javascript
// 获取服务器配置
const config = await mcp.readResource("config://server");

// 获取系统信息
const sysInfo = await mcp.readResource("info://system");
```

### 使用提示词

```javascript
// 代码审查
const review = await mcp.getPrompt("code_review", {
  code: "function add(a, b) { return a + b; }",
  language: "javascript"
});

// 生成文档
const docs = await mcp.getPrompt("generate_docs", {
  topic: "用户认证系统",
  style: "technical"
});
```

## 扩展开发

### 添加新工具

```javascript
server.tool(
  "tool_name",
  "工具描述",
  {
    param1: z.string().describe("参数描述"),
    param2: z.number().optional().describe("可选参数"),
  },
  async ({ param1, param2 }) => {
    // 实现逻辑
    return {
      content: [
        {
          type: "text",
          text: "结果",
        },
      ],
    };
  }
);
```

### 添加新资源

```javascript
server.resource(
  "resource://uri",
  "资源描述",
  async () => ({
    contents: [
      {
        uri: "resource://uri",
        text: "资源内容",
        mimeType: "text/plain",
      },
    ],
  })
);
```

### 添加新提示词

```javascript
server.prompt(
  "prompt_name",
  "提示词描述",
  {
    param: z.string().describe("参数描述"),
  },
  ({ param }) => ({
    messages: [
      {
        role: "user",
        content: {
          type: "text",
          text: `提示词内容 ${param}`,
        },
      },
    ],
  })
);
```

## 许可证

MIT
