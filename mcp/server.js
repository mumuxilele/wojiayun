#!/usr/bin/env node

/**
 * Wojiayun MCP Server - HTTP/SSE 模式
 * 
 * 支持通过 HTTP 网络访问的 MCP 服务
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import express from "express";
import cors from "cors";
import { z } from "zod";

const app = express();
const PORT = process.env.MCP_PORT || 3001;

// 启用 CORS
app.use(cors());

// 启用 JSON 解析
app.use(express.json());

// 创建 MCP 服务器实例
const server = new McpServer({
  name: "wojiayun-mcp",
  version: "1.0.0",
  capabilities: {
    tools: {},
    resources: {},
    prompts: {},
  },
});

// ==================== Tools ====================

// 示例工具：获取服务器状态
server.tool(
  "get_server_status",
  "获取服务器运行状态",
  {},
  async () => {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            status: "running",
            uptime: process.uptime(),
            memory: process.memoryUsage(),
            timestamp: new Date().toISOString(),
          }, null, 2),
        },
      ],
    };
  }
);

// 示例工具：执行数学计算
server.tool(
  "calculate",
  "执行数学计算",
  {
    expression: z.string().describe("数学表达式，如 2 + 2"),
  },
  async ({ expression }) => {
    try {
      const result = Function(`"use strict"; return (${expression})`)();
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              expression,
              result,
            }, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              error: "计算失败",
              message: error.message,
            }, null, 2),
          },
        ],
        isError: true,
      };
    }
  }
);

// 示例工具：文本处理
server.tool(
  "process_text",
  "处理文本（转换大小写、统计字数等）",
  {
    text: z.string().describe("要处理的文本"),
    operation: z.enum(["uppercase", "lowercase", "count", "reverse"]).describe("操作类型"),
  },
  async ({ text, operation }) => {
    let result;
    switch (operation) {
      case "uppercase":
        result = text.toUpperCase();
        break;
      case "lowercase":
        result = text.toLowerCase();
        break;
      case "count":
        result = {
          characters: text.length,
          words: text.split(/\s+/).filter(Boolean).length,
          lines: text.split("\n").length,
        };
        break;
      case "reverse":
        result = text.split("").reverse().join("");
        break;
      default:
        throw new Error(`未知操作: ${operation}`);
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            operation,
            input: text,
            result,
          }, null, 2),
        },
      ],
    };
  }
);

// ==================== Resources ====================

server.resource(
  "config://server",
  "服务器配置信息",
  async () => ({
    contents: [
      {
        uri: "config://server",
        text: JSON.stringify({
          name: "wojiayun-mcp",
          version: "1.0.0",
          environment: process.env.NODE_ENV || "development",
          platform: process.platform,
          nodeVersion: process.version,
        }, null, 2),
        mimeType: "application/json",
      },
    ],
  })
);

server.resource(
  "info://system",
  "系统运行信息",
  async () => ({
    contents: [
      {
        uri: "info://system",
        text: JSON.stringify({
          hostname: process.env.HOSTNAME || "unknown",
          pid: process.pid,
          arch: process.arch,
          memoryUsage: process.memoryUsage(),
        }, null, 2),
        mimeType: "application/json",
      },
    ],
  })
);

// ==================== Prompts ====================

server.prompt(
  "code_review",
  "代码审查提示词",
  {
    code: z.string().describe("要审查的代码"),
    language: z.string().optional().describe("编程语言"),
  },
  ({ code, language }) => ({
    messages: [
      {
        role: "user",
        content: {
          type: "text",
          text: `请审查以下${language ? language + " " : ""}代码，指出潜在问题和改进建议：\n\n\`\`\`${language || ""}\n${code}\n\`\`\``,
        },
      },
    ],
  })
);

server.prompt(
  "generate_docs",
  "生成文档提示词",
  {
    topic: z.string().describe("文档主题"),
    style: z.enum(["technical", "user-friendly", "api"]).optional().describe("文档风格"),
  },
  ({ topic, style }) => ({
    messages: [
      {
        role: "user",
        content: {
          type: "text",
          text: `请为以下主题生成${style || "technical"}风格的文档：\n\n主题：${topic}`,
        },
      },
    ],
  })
);

// ==================== HTTP/SSE 路由 ====================

// 存储活跃的 SSE 连接
const transports = new Map();

// SSE 连接端点
app.get("/mcp", async (req, res) => {
  console.log("新的 SSE 连接请求");
  
  const transport = new SSEServerTransport("/messages", res);
  transports.set(transport.sessionId, transport);
  
  res.on("close", () => {
    console.log(`SSE 连接关闭: ${transport.sessionId}`);
    transports.delete(transport.sessionId);
  });
  
  await server.connect(transport);
  console.log(`SSE 连接建立: ${transport.sessionId}`);
});

// 消息接收端点
app.post("/messages", async (req, res) => {
  const sessionId = req.query.sessionId;
  
  if (!sessionId) {
    return res.status(400).json({ error: "缺少 sessionId 参数" });
  }
  
  const transport = transports.get(sessionId);
  
  if (!transport) {
    return res.status(404).json({ error: "未找到对应的 SSE 连接" });
  }
  
  await transport.handlePostMessage(req, res);
});

// 健康检查
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "wojiayun-mcp",
    version: "1.0.0",
    timestamp: new Date().toISOString(),
    activeConnections: transports.size,
  });
});

// 根路径
app.get("/", (req, res) => {
  res.json({
    name: "Wojiayun MCP Server",
    version: "1.0.0",
    description: "MCP 服务 - HTTP/SSE 模式",
    endpoints: {
      sse: "/mcp",
      messages: "/messages",
      health: "/health",
    },
    usage: {
      step1: "GET /mcp - 建立 SSE 连接",
      step2: "POST /messages?sessionId=<id> - 发送 MCP 请求",
    },
  });
});

// ==================== 启动服务器 ====================

app.listen(PORT, () => {
  console.log(`Wojiayun MCP Server 已启动`);
  console.log(`HTTP 模式监听端口: ${PORT}`);
  console.log(`SSE 端点: http://0.0.0.0:${PORT}/mcp`);
  console.log(`健康检查: http://0.0.0.0:${PORT}/health`);
});
